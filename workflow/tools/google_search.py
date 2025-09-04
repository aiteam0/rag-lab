"""
Google Custom Search Tool
Google Custom Search API를 사용한 웹 검색 도구
TavilySearchTool과 100% 호환되는 인터페이스 제공
"""

import os
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor

from langchain_core.documents import Document
from langchain_core.tools import Tool
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Google API Client
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Warning: google-api-python-client not installed. Run: pip install google-api-python-client")

load_dotenv()
logger = logging.getLogger(__name__)


class GoogleSearchResult(BaseModel):
    """Google 검색 결과"""
    query: str = Field(description="검색 쿼리")
    results: List[Dict[str, Any]] = Field(description="검색 결과 리스트")
    total_results: int = Field(description="전체 결과 수")


class QuotaManager:
    """API 쿼터 관리자 - 일일 100회 제한 관리"""
    
    def __init__(self, daily_limit: int = 100):
        """
        초기화
        
        Args:
            daily_limit: 일일 쿼리 제한 (기본 100)
        """
        self.daily_limit = daily_limit
        self.queries_today = 0
        self.last_reset = date.today()
        self.query_log = []
    
    def can_query(self) -> bool:
        """쿼리 가능 여부 확인"""
        self._check_reset()
        return self.queries_today < self.daily_limit
    
    def increment(self, query: str = ""):
        """쿼리 카운트 증가"""
        self._check_reset()
        self.queries_today += 1
        self.query_log.append({
            "time": datetime.now(),
            "query": query[:50] if query else "",
            "count": self.queries_today
        })
        logger.debug(f"[QUOTA] Used {self.queries_today}/{self.daily_limit} queries today")
    
    def remaining(self) -> int:
        """남은 쿼리 수 반환"""
        self._check_reset()
        return max(0, self.daily_limit - self.queries_today)
    
    def _check_reset(self):
        """날짜가 바뀌었으면 카운터 리셋"""
        if date.today() > self.last_reset:
            self.queries_today = 0
            self.query_log = []
            self.last_reset = date.today()
            logger.info(f"[QUOTA] Daily quota reset. {self.daily_limit} queries available.")


class SearchCache:
    """검색 결과 캐시 - API 호출 최소화"""
    
    def __init__(self, ttl: int = 3600):
        """
        초기화
        
        Args:
            ttl: 캐시 유효 시간 (초, 기본 1시간)
        """
        self.cache = {}
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
    
    def get(self, query: str) -> Optional[List[Document]]:
        """캐시에서 결과 가져오기"""
        cache_key = self._make_key(query)
        
        if cache_key in self.cache:
            entry_time, documents = self.cache[cache_key]
            if time.time() - entry_time < self.ttl:
                self.hits += 1
                logger.debug(f"[CACHE] Hit for query: '{query[:30]}...' (hit rate: {self.hit_rate():.1%})")
                return documents
            else:
                # 만료된 캐시 제거
                del self.cache[cache_key]
        
        self.misses += 1
        return None
    
    def set(self, query: str, documents: List[Document]):
        """캐시에 결과 저장"""
        cache_key = self._make_key(query)
        self.cache[cache_key] = (time.time(), documents)
        logger.debug(f"[CACHE] Stored {len(documents)} results for: '{query[:30]}...'")
        
        # 캐시 크기 제한 (최대 100개)
        if len(self.cache) > 100:
            # 가장 오래된 항목 제거
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]
    
    def hit_rate(self) -> float:
        """캐시 히트율 계산"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def _make_key(self, query: str) -> str:
        """캐시 키 생성"""
        return query.lower().strip()


class GoogleSearchInput(BaseModel):
    """Google Search Tool의 입력 스키마"""
    query: str = Field(
        description="The search query string to look up on Google. Should be a clear and specific search term."
    )


class GoogleSearchTool:
    """Google Custom Search 도구 - TavilySearchTool 호환 인터페이스"""
    
    def __init__(self, max_results: int = 5):
        """
        초기화
        
        Args:
            max_results: 최대 검색 결과 수 (기본값: 5)
        """
        # API 자격 증명 확인
        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        
        if not api_key or not cse_id:
            missing = []
            if not api_key:
                missing.append("GOOGLE_API_KEY")
            if not cse_id:
                missing.append("GOOGLE_SEARCH_ENGINE_ID")
            raise ValueError(f"Missing Google Search credentials: {missing}")
        
        if not GOOGLE_API_AVAILABLE:
            raise ImportError("google-api-python-client not installed. Run: pip install google-api-python-client")
        
        self.api_key = api_key
        self.cse_id = cse_id
        self.max_results = max_results
        
        # Google API 서비스 빌드
        try:
            self.service = build("customsearch", "v1", developerKey=api_key)
            logger.info("[GOOGLE] Google Custom Search API initialized successfully")
        except Exception as e:
            raise ValueError(f"Failed to initialize Google Search API: {e}")
        
        # 쿼터 매니저 및 캐시 초기화
        self.quota_manager = QuotaManager(daily_limit=100)
        self.cache = SearchCache(ttl=3600)  # 1시간 캐시
        
        # ThreadPoolExecutor for async operations
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        logger.info(f"[GOOGLE] GoogleSearchTool initialized with max_results={max_results}")
    
    def _search_sync(self, query: str, search_depth: str = "basic") -> Dict[str, Any]:
        """
        동기 검색 실행 (내부용)
        
        Args:
            query: 검색 쿼리
            search_depth: 검색 깊이 ("basic" 또는 "advanced")
            
        Returns:
            검색 결과 딕셔너리
        """
        # search_depth를 결과 수로 매핑
        depth_mapping = {
            "basic": min(5, self.max_results),
            "advanced": min(10, self.max_results)
        }
        num_results = depth_mapping.get(search_depth, self.max_results)
        
        # 쿼터 체크
        if not self.quota_manager.can_query():
            logger.warning(f"[GOOGLE] Daily quota exhausted ({self.quota_manager.daily_limit} queries)")
            return {
                "results": [],
                "error": f"Google Search daily quota exhausted (limit: {self.quota_manager.daily_limit})"
            }
        
        results = []
        total_to_fetch = min(num_results, self.max_results)
        
        try:
            # Google API는 한 번에 최대 10개까지만 반환
            # 10개 이상 필요하면 여러 번 호출 (페이지네이션)
            for start_index in range(1, total_to_fetch + 1, 10):
                num_to_fetch = min(10, total_to_fetch - len(results))
                
                logger.debug(f"[GOOGLE] Searching: '{query[:50]}...' (start={start_index}, num={num_to_fetch})")
                
                # API 호출
                response = self.service.cse().list(
                    q=query,
                    cx=self.cse_id,
                    num=num_to_fetch,
                    start=start_index
                ).execute()
                
                # 쿼터 카운트 증가
                self.quota_manager.increment(query)
                
                # 결과 추출
                items = response.get("items", [])
                results.extend(items)
                
                # 필요한 만큼 가져왔으면 중단
                if len(results) >= total_to_fetch:
                    break
                
                # 더 이상 결과가 없으면 중단
                if len(items) < num_to_fetch:
                    break
            
            logger.info(f"[GOOGLE] Retrieved {len(results)} results (quota remaining: {self.quota_manager.remaining()})")
            
            return {
                "results": results[:total_to_fetch],
                "total": len(results),
                "query": query
            }
            
        except HttpError as e:
            error_msg = str(e)
            if e.resp.status == 429:
                error_msg = "Rate limit exceeded. Please try again later."
                logger.error(f"[GOOGLE] Rate limit error: {e}")
            elif e.resp.status == 403:
                error_msg = "API quota exceeded or permission denied."
                logger.error(f"[GOOGLE] Quota/permission error: {e}")
            else:
                logger.error(f"[GOOGLE] HTTP error {e.resp.status}: {e}")
            
            return {
                "results": [],
                "error": error_msg
            }
            
        except Exception as e:
            logger.error(f"[GOOGLE] Search failed: {e}")
            return {
                "results": [],
                "error": str(e)
            }
    
    def _convert_to_document(self, google_result: Dict, rank: int, query: str) -> Document:
        """
        Google 검색 결과를 LangChain Document로 변환
        
        Args:
            google_result: Google API 결과
            rank: 검색 순위 (1부터 시작)
            query: 원본 검색 쿼리
            
        Returns:
            LangChain Document
        """
        # 필드 추출
        title = google_result.get("title", "")
        snippet = google_result.get("snippet", "")
        link = google_result.get("link", "")
        
        # 콘텐츠 포맷 (TavilySearchTool과 동일)
        content = f"**{title}**\n\n{snippet}" if title else snippet
        
        # 발행일 추출 시도 (pagemap에서)
        published_date = ""
        if "pagemap" in google_result:
            metatags = google_result["pagemap"].get("metatags", [])
            if metatags:
                published_date = metatags[0].get("article:published_time", "")
                if not published_date:
                    published_date = metatags[0].get("og:updated_time", "")
        
        # 메타데이터 구성 (TavilySearchTool과 동일한 구조)
        metadata = {
            "source": link,
            "title": title,
            "score": 1.0 - (rank * 0.1),  # 순위 기반 점수 (1위=0.9, 2위=0.8, ...)
            "published_date": published_date,
            "search_query": query,
            "search_rank": rank,
            "search_tool": "google"  # tavily 대신 google
        }
        
        return Document(
            page_content=content,
            metadata=metadata
        )
    
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
        # 캐시 확인
        cached_docs = self.cache.get(query)
        if cached_docs is not None:
            return cached_docs
        
        # 비동기 실행
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self.executor,
            self._search_sync,
            query,
            search_depth
        )
        
        # 결과를 Document로 변환
        documents = []
        
        if "error" in response:
            logger.warning(f"[GOOGLE] Search error: {response['error']}")
            return documents
        
        results = response.get("results", [])
        
        # 웹 검색 결과 로깅 (TavilySearchTool과 동일한 형식)
        logger.info(f"[WEB_SEARCH] Found {len(results)} web results for: \"{query[:50]}{'...' if len(query) > 50 else ''}\"")
        for i, result in enumerate(results[:3]):
            title = result.get('title', 'No title')[:40] + ('...' if len(result.get('title', '')) > 40 else '')
            url = result.get('link', 'No URL')[:60] + ('...' if len(result.get('link', '')) > 60 else '')
            logger.info(f"[WEB_SEARCH] Result {i+1}: \"{title}\" - {url}")
        
        # Document 변환
        for idx, result in enumerate(results):
            doc = self._convert_to_document(result, idx + 1, query)
            documents.append(doc)
        
        # 캐시 저장
        if documents:
            self.cache.set(query, documents)
        
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
        # 캐시 확인
        cached_docs = self.cache.get(query)
        if cached_docs is not None:
            return cached_docs
        
        # 동기 검색 실행
        response = self._search_sync(query, search_depth)
        
        documents = []
        
        if "error" in response:
            logger.warning(f"[GOOGLE] Search error: {response['error']}")
            return documents
        
        results = response.get("results", [])
        
        # 결과 로깅
        logger.info(f"[WEB_SEARCH] Found {len(results)} web results for: \"{query[:50]}{'...' if len(query) > 50 else ''}\"")
        
        # Document 변환
        for idx, result in enumerate(results):
            doc = self._convert_to_document(result, idx + 1, query)
            documents.append(doc)
        
        # 캐시 저장
        if documents:
            self.cache.set(query, documents)
        
        return documents
    
    def as_tool(self) -> Tool:
        """
        LangChain Tool로 변환
        
        Returns:
            LangChain Tool 인스턴스
        """
        def search_wrapper(query: str) -> List[Document]:
            """동기 검색 래퍼"""
            return self.search_sync(query, "basic")
        
        async def async_search_wrapper(query: str) -> List[Document]:
            """비동기 검색 래퍼"""
            return await self.search(query, "basic")
        
        return Tool(
            name="google_web_search",
            description=(
                "Search the web for current information using Google Custom Search. "
                "Use this when you need recent information not available in the documents. "
                "For example: current time, latest news, recent events, real-time data, etc."
            ),
            func=search_wrapper,
            coroutine=async_search_wrapper,
            args_schema=GoogleSearchInput
        )
    
    async def advanced_search(
        self, 
        query: str,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> List[Document]:
        """
        고급 검색 옵션 (도메인 필터링)
        
        Args:
            query: 검색 쿼리
            include_domains: 포함할 도메인 리스트
            exclude_domains: 제외할 도메인 리스트
            
        Returns:
            Document 리스트
        """
        # 도메인 필터 적용
        search_query = query
        
        # 포함 도메인 (site: 연산자 사용)
        if include_domains:
            site_filter = " OR ".join([f"site:{domain}" for domain in include_domains])
            search_query = f"{query} ({site_filter})"
        
        # 제외 도메인 (-site: 연산자 사용)
        if exclude_domains:
            for domain in exclude_domains:
                search_query = f"{search_query} -site:{domain}"
        
        logger.debug(f"[GOOGLE] Advanced search query: {search_query}")
        
        # Advanced depth로 검색
        return await self.search(search_query, search_depth="advanced")
    
    def check_availability(self) -> bool:
        """
        Google API 가용성 확인
        
        Returns:
            API 사용 가능 여부
        """
        try:
            # 쿼터 확인
            if not self.quota_manager.can_query():
                logger.warning(f"[GOOGLE] Quota exhausted: {self.quota_manager.queries_today}/{self.quota_manager.daily_limit}")
                return False
            
            # API 연결 테스트 (실제 검색은 하지 않음)
            # list API를 호출하되 maxResults=0으로 설정하여 쿼터 소비 최소화
            # 참고: 이것도 쿼터를 소비할 수 있으므로 주의
            # 대신 service 객체가 있는지만 확인
            if self.service is not None:
                logger.debug(f"[GOOGLE] API available. Quota: {self.quota_manager.remaining()}/{self.quota_manager.daily_limit}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[GOOGLE] Availability check failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        도구 상태 정보 반환
        
        Returns:
            상태 정보 딕셔너리
        """
        return {
            "tool": "google_search",
            "available": self.check_availability(),
            "quota": {
                "used": self.quota_manager.queries_today,
                "remaining": self.quota_manager.remaining(),
                "limit": self.quota_manager.daily_limit
            },
            "cache": {
                "size": len(self.cache.cache),
                "hit_rate": f"{self.cache.hit_rate():.1%}",
                "hits": self.cache.hits,
                "misses": self.cache.misses
            },
            "max_results": self.max_results
        }


# 유틸리티 함수 (TavilySearchTool과 동일한 인터페이스)
def create_google_search_tool(max_results: int = 5) -> Tool:
    """
    Google 검색 도구 생성 헬퍼 함수
    
    Args:
        max_results: 최대 검색 결과 수
        
    Returns:
        LangChain Tool 인스턴스
    """
    try:
        google = GoogleSearchTool(max_results=max_results)
        return google.as_tool()
    except (ValueError, ImportError) as e:
        logger.warning(f"Warning: {e}")
        # Fallback tool that returns empty results
        return Tool(
            name="google_web_search",
            description="Web search (unavailable - API key missing or package not installed)",
            func=lambda query: [],
            coroutine=lambda query: [],
            args_schema=GoogleSearchInput
        )