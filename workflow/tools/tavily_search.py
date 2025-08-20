"""
Tavily Search Tool
웹 검색 도구 - 문서에서 찾을 수 없는 정보를 검색
"""

import os
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.tools import Tool
from tavily import TavilyClient
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

load_dotenv()


class TavilySearchResult(BaseModel):
    """Tavily 검색 결과"""
    query: str = Field(description="검색 쿼리")
    results: List[Dict[str, Any]] = Field(description="검색 결과 리스트")
    total_results: int = Field(description="전체 결과 수")


class TavilySearchTool:
    """Tavily 웹 검색 도구"""
    
    def __init__(self, max_results: int = 5):
        """
        초기화
        
        Args:
            max_results: 최대 검색 결과 수 (기본값: 5)
        """
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables")
        
        self.client = TavilyClient(api_key=api_key)
        self.max_results = max_results
        self.executor = ThreadPoolExecutor(max_workers=1)
    
    def _search_sync(self, query: str, search_depth: str = "basic") -> Dict[str, Any]:
        """
        동기 검색 실행
        
        Args:
            query: 검색 쿼리
            search_depth: 검색 깊이 ("basic" 또는 "advanced")
            
        Returns:
            검색 결과
        """
        try:
            response = self.client.search(
                query=query,
                search_depth=search_depth,
                max_results=self.max_results
            )
            return response
        except Exception as e:
            return {
                "results": [],
                "error": str(e)
            }
    
    async def search(
        self, 
        query: str, 
        search_depth: str = "basic"
    ) -> List[Document]:
        """
        비동기 웹 검색 실행
        
        Args:
            query: 검색 쿼리
            search_depth: 검색 깊이 ("basic" 또는 "advanced")
            
        Returns:
            Document 리스트
        """
        loop = asyncio.get_event_loop()
        
        # 동기 함수를 비동기로 실행
        response = await loop.run_in_executor(
            self.executor,
            self._search_sync,
            query,
            search_depth
        )
        
        # 결과를 Document로 변환
        documents = []
        
        if "error" in response:
            # 에러 발생 시 빈 리스트 반환
            print(f"Tavily search error: {response['error']}")
            return documents
        
        results = response.get("results", [])
        
        # 웹 검색 결과 상세 로깅 (상위 3개만)
        print(f"[WEB_SEARCH] Found {len(results)} web results for: \"{query[:50]}{'...' if len(query) > 50 else ''}\"")
        for i, result in enumerate(results[:3]):
            title = result.get('title', 'No title')[:40] + ('...' if len(result.get('title', '')) > 40 else '')
            url = result.get('url', 'No URL')[:60] + ('...' if len(result.get('url', '')) > 60 else '')
            print(f"[WEB_SEARCH] Result {i+1}: \"{title}\" - {url}")
        
        for idx, result in enumerate(results):
            # 각 결과를 Document로 변환
            content = result.get("content", "")
            
            # 제목과 내용 결합
            title = result.get("title", "")
            if title:
                content = f"**{title}**\n\n{content}"
            
            # 메타데이터 구성
            metadata = {
                "source": result.get("url", ""),
                "title": title,
                "score": result.get("score", 0.0),
                "published_date": result.get("published_date", ""),
                "search_query": query,
                "search_rank": idx + 1,
                "search_tool": "tavily"
            }
            
            # Document 생성
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(doc)
        
        return documents
    
    def search_sync(self, query: str, search_depth: str = "basic") -> List[Document]:
        """
        동기 웹 검색 (LangGraph 호환)
        
        Args:
            query: 검색 쿼리
            search_depth: 검색 깊이
            
        Returns:
            Document 리스트
        """
        response = self._search_sync(query, search_depth)
        
        documents = []
        
        if "error" in response:
            print(f"Tavily search error: {response['error']}")
            return documents
        
        results = response.get("results", [])
        
        for idx, result in enumerate(results):
            content = result.get("content", "")
            title = result.get("title", "")
            
            if title:
                content = f"**{title}**\n\n{content}"
            
            metadata = {
                "source": result.get("url", ""),
                "title": title,
                "score": result.get("score", 0.0),
                "published_date": result.get("published_date", ""),
                "search_query": query,
                "search_rank": idx + 1,
                "search_tool": "tavily"
            }
            
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(doc)
        
        return documents
    
    def as_tool(self) -> Tool:
        """
        LangChain Tool로 변환
        
        Returns:
            LangChain Tool 인스턴스
        """
        return Tool(
            name="tavily_web_search",
            description=(
                "Search the web for current information using Tavily. "
                "Use this when you need recent information not available in the documents. "
                "Input should be a search query string."
            ),
            func=lambda query: self.search_sync(query, "basic"),
            coroutine=lambda query: self.search(query, "basic")
        )
    
    async def advanced_search(
        self, 
        query: str,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> List[Document]:
        """
        고급 검색 옵션
        
        Args:
            query: 검색 쿼리
            include_domains: 포함할 도메인 리스트
            exclude_domains: 제외할 도메인 리스트
            
        Returns:
            Document 리스트
        """
        # 도메인 필터 적용
        search_query = query
        
        if include_domains:
            domain_filter = " OR ".join([f"site:{domain}" for domain in include_domains])
            search_query = f"{query} ({domain_filter})"
        
        if exclude_domains:
            for domain in exclude_domains:
                search_query = f"{search_query} -site:{domain}"
        
        # Advanced depth로 검색
        return await self.search(search_query, search_depth="advanced")
    
    def check_availability(self) -> bool:
        """
        Tavily API 가용성 확인
        
        Returns:
            API 사용 가능 여부
        """
        try:
            # 간단한 테스트 쿼리
            response = self._search_sync("test", "basic")
            return "error" not in response
        except Exception:
            return False


# 유틸리티 함수
def create_tavily_tool(max_results: int = 5) -> Tool:
    """
    Tavily 검색 도구 생성 헬퍼 함수
    
    Args:
        max_results: 최대 검색 결과 수
        
    Returns:
        LangChain Tool 인스턴스
    """
    try:
        tavily = TavilySearchTool(max_results=max_results)
        return tavily.as_tool()
    except ValueError as e:
        print(f"Warning: {e}")
        # Fallback tool that returns empty results
        return Tool(
            name="tavily_web_search",
            description="Web search (unavailable - API key missing)",
            func=lambda query: [],
            coroutine=lambda query: []
        )