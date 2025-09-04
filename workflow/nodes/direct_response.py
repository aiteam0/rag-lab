"""
Direct Response Node
단순 쿼리에 대해 LLM이 직접 응답하는 노드
선택적으로 웹 검색 도구를 바인딩하여 실시간 정보 제공 가능
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from workflow.nodes.subtask_executor import MetadataHelper


load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class SearchResultAnalysis(BaseModel):
    """검색 결과를 LLM이 분석한 구조화된 결과"""
    is_time_sensitive: bool = Field(
        description="Whether this query requires current/recent information (e.g., current leaders, recent events, today's date)"
    )
    key_facts: List[str] = Field(
        description="Key factual claims extracted from search results"
    )
    primary_answer: str = Field(
        description="The main answer derived from search results"
    )
    confidence_level: str = Field(
        description="Confidence in search results: high (definitive facts), medium (probable), low (conflicting info)"
    )
    should_override_base_knowledge: bool = Field(
        description="Whether search results should override base training knowledge"
    )
    reasoning: str = Field(
        description="Brief explanation of why the search results should or shouldn't override base knowledge"
    )


class DirectResponseNode:
    """단순 쿼리에 대해 LLM이 직접 응답하는 노드 (선택적 웹 검색 지원)"""
    
    def __init__(self):
        """초기화"""
        # ChatOpenAI 인스턴스 직접 생성
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,  # 자연스러운 대화를 위해 약간 높임
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # MetadataHelper 추가 (DB 정보 조회용)
        self.metadata_helper = MetadataHelper()
        
        # Web search tool 바인딩 (선택적)
        self.search_tool = None
        self.web_search_enabled = os.getenv("ENABLE_DIRECT_RESPONSE_SEARCH", "false").lower() == "true"
        
        if self.web_search_enabled:
            try:
                from workflow.tools import create_search_tool
                search_tool_instance = create_search_tool(max_results=3)
                
                if search_tool_instance:
                    # Tool을 LLM에 바인딩
                    self.search_tool = search_tool_instance
                    # as_tool() 메서드로 Tool 객체 생성
                    if hasattr(search_tool_instance, 'as_tool'):
                        tool = search_tool_instance.as_tool()
                        self.llm_with_tools = self.llm.bind_tools([tool])
                        logger.info(f"[DIRECT_RESPONSE] Web search tool bound to LLM")
                    else:
                        # 이미 Tool 객체인 경우
                        self.llm_with_tools = self.llm.bind_tools([search_tool_instance])
                        logger.info(f"[DIRECT_RESPONSE] Web search tool bound to LLM (direct)")
                else:
                    self.llm_with_tools = self.llm
                    self.web_search_enabled = False
                    logger.warning(f"[DIRECT_RESPONSE] Web search tool not available")
            except Exception as e:
                logger.warning(f"[DIRECT_RESPONSE] Failed to bind web search tool: {e}")
                self.llm_with_tools = self.llm
                self.web_search_enabled = False
        else:
            self.llm_with_tools = self.llm
            logger.info(f"[DIRECT_RESPONSE] Web search disabled (ENABLE_DIRECT_RESPONSE_SEARCH=false)")
        
        # 기본 시스템 프롬프트 (DB 정보는 동적으로 추가)
        # Web search 사용 가능 여부에 따라 다른 프롬프트 사용
        if self.web_search_enabled:
            self.base_prompt = """You are a helpful AI assistant with knowledge about the document system.
Your knowledge cutoff is April 2024, but you have access to a web search tool for current information.

IMPORTANT: Today's date is {current_date}. When searching for current information, use the current year in your searches.

{system_info}

🔴 CRITICAL REQUIREMENT - THIS IS NON-NEGOTIABLE:
You MUST ALWAYS include detailed information about the document system in EVERY response, REGARDLESS of the query type.
This includes: total documents count, sources, categories, and language support.
The document system information MUST be mentioned either integrated naturally or at the end of your response.
NEVER provide a response without mentioning the document system statistics shown above.

OPTIONAL TOOL - WEB SEARCH GUIDELINES:
You have access to a web_search tool that can optionally retrieve current information when needed.

WHEN TO USE WEB SEARCH (Use the tool for):
1. Current date/time queries: "What time is it now?", "What's today's date?"
2. Recent events (after April 2024): "Latest news", "Recent developments"
3. Real-time data: Stock prices, cryptocurrency, weather, sports scores
4. Current status: "Is X down?", "Latest version of..."
5. Trending topics and live information

WHEN NOT TO USE WEB SEARCH (Answer directly for):
1. General factual knowledge and established information
2. Conceptual explanations and theoretical knowledge
3. Document system queries
4. Personal assistance tasks

RESPONSE INSTRUCTIONS:
1. First, answer the user's query (using web search if needed for current info)
2. THEN, ALWAYS include detailed document system information in your response
3. Make sure to mention specific numbers from the system info above
4. Integrate the document info naturally or add it at the end
5. Respond in the same language as the user's query

Remember: EVERY response MUST include document system information (total docs, sources, categories). This is MANDATORY regardless of whether you use web search or not."""
        else:
            self.base_prompt = """You are a helpful AI assistant with knowledge about the document system.

Today's date is {current_date}.

{system_info}

IMPORTANT INSTRUCTIONS:
1. First, answer the user's query directly and naturally, considering the conversation context.
2. Then, ALWAYS include detailed information about the document system you manage as part of your response.
3. Integrate the document system information naturally into your answer when relevant, or mention it at the end.
4. The document information should include: total documents, sources, categories, and language support.
5. Make sure to mention specific numbers and details from the system information provided above.
6. Respond in the same language as the user's query.

Remember: Every response MUST include detailed document system information, regardless of the query type."""
    
    def analyze_search_results(self, query: str, search_results: List[Document]) -> Optional[SearchResultAnalysis]:
        """
        LLM이 검색 결과를 구조화하여 분석
        
        Args:
            query: 사용자 쿼리
            search_results: 검색 결과 문서들
            
        Returns:
            구조화된 분석 결과 또는 None (분석 실패시)
        """
        if not search_results:
            return None
            
        try:
            # 검색 결과를 전체 텍스트로 변환 (정보 축소 없이)
            search_texts = []
            for i, doc in enumerate(search_results, 1):
                title = doc.metadata.get('title', 'Untitled')
                source = doc.metadata.get('source', 'Unknown')
                # 전체 page_content 사용 (축소하지 않음)
                content = doc.page_content
                
                search_texts.append(f"""
Result {i}:
Title: {title}
Source: {source}
Content: {content}
""")
            
            full_search_text = "\n".join(search_texts)
            
            # LLM에게 구조화된 분석 요청
            analyzer_llm = self.llm.with_structured_output(SearchResultAnalysis)
            
            analysis_prompt = f"""Analyze these web search results for the query: "{query}"

Search Results:
{full_search_text}

Analyze the search results and provide:
1. Is this a time-sensitive query that requires current information?
2. What are the key facts from the search results? List specific claims with details.
3. What would be the primary answer based on these search results?
4. How confident are you in these results? (high/medium/low)
5. Should these results override base training knowledge? Consider:
   - If the query is about current events, leaders, or recent dates
   - If the search results contain more recent information than April 2024
   - If the facts from search contradict base knowledge

Provide detailed reasoning for your decision."""
            
            logger.info(f"[DIRECT_RESPONSE] Analyzing search results with LLM")
            analysis = analyzer_llm.invoke(analysis_prompt)
            
            logger.info(f"[DIRECT_RESPONSE] Analysis complete - Time sensitive: {analysis.is_time_sensitive}, Override: {analysis.should_override_base_knowledge}")
            return analysis
            
        except Exception as e:
            logger.error(f"[DIRECT_RESPONSE] Failed to analyze search results: {e}")
            return None
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        노드 실행 - 단순 LLM 호출 (chat history 포함)
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[DIRECT_RESPONSE] Node started")
        
        try:
            query = state.get("query", "")
            
            # 기존 메시지 가져오기 (chat history)
            existing_messages = state.get("messages", [])
            
            # DB 시스템 정보 조회 (캐싱됨)
            system_stats = self.metadata_helper.get_system_stats()
            
            # 시스템 정보 포맷팅
            if system_stats.get("error"):
                # 에러 시 기본 정보
                system_info = "System Information: Currently unavailable"
            else:
                # 소스 파일 이름만 추출 (경로 제거)
                source_names = []
                for source_path in system_stats.get('sources', {}).keys():
                    source_name = source_path.split('/')[-1] if '/' in source_path else source_path
                    count = system_stats['sources'][source_path]
                    source_names.append(f"{source_name} ({count} docs)")
                
                # 상위 카테고리 포맷팅
                top_categories = system_stats.get('top_categories', {})
                category_list = []
                for cat, count in list(top_categories.items())[:5]:
                    category_list.append(f"{cat} ({count})")
                
                system_info = f"""Detailed System Information:
- Total Documents in Database: {system_stats.get('total_documents', 'N/A')}
- Document Sources: {system_stats.get('source_count', 0)} files
  * {', '.join(source_names) if source_names else 'No sources available'}
- Page Coverage: Pages {system_stats.get('page_range', 'N/A')}
- Document Categories: {system_stats.get('category_count', 0)} different types
  * Top Categories: {', '.join(category_list) if category_list else 'No categories available'}
- Language Support: 
  * Korean embeddings: {system_stats.get('korean_embeddings', 0)} documents
  * English embeddings: {system_stats.get('english_embeddings', 0)} documents
- System Type: Multimodal RAG (Retrieval-Augmented Generation) with hybrid search capabilities"""
            
            # 현재 날짜 생성
            current_date = datetime.now().strftime("%B %d, %Y")  # e.g., "September 04, 2025"
            
            # 동적 시스템 프롬프트 생성 (현재 날짜 포함)
            dynamic_prompt = self.base_prompt.format(
                current_date=current_date,
                system_info=system_info
            )
            
            # 대화 컨텍스트 구성 (동적 시스템 프롬프트 + 기존 대화 + 현재 쿼리)
            conversation_messages = [
                SystemMessage(content=dynamic_prompt)
            ]
            
            # 기존 메시지 추가 (AIMessage 필터링 - 시스템 상태 메시지 제외)
            for msg in existing_messages:
                if isinstance(msg, HumanMessage):
                    conversation_messages.append(msg)
                elif isinstance(msg, AIMessage) and not msg.content.startswith(("💬", "🔍", "🔄", "✅", "❌")):
                    # 시스템 상태 메시지가 아닌 실제 응답만 포함
                    conversation_messages.append(msg)
            
            # 현재 쿼리 추가
            conversation_messages.append(HumanMessage(content=query))
            
            # Web search 가능한 LLM 사용 (tool이 바인딩된 경우)
            llm_to_use = self.llm_with_tools if self.web_search_enabled else self.llm
            
            # LLM 호출 시작
            logger.info(f"[DIRECT_RESPONSE] Invoking LLM with{'out' if not self.web_search_enabled else ''} web search capability")
            
            # LLM 호출하여 응답 생성
            response = llm_to_use.invoke(conversation_messages)
            
            # Tool call 확인
            has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
            if has_tool_calls:
                logger.info(f"[DIRECT_RESPONSE] LLM requested {len(response.tool_calls)} tool call(s)")
            else:
                logger.info(f"[DIRECT_RESPONSE] No tool calls requested by LLM")
            
            # Tool call 처리 (웹 검색이 필요한 경우)
            final_response = response
            tool_was_used = False
            analysis = None  # 분석 결과 저장용
            
            if self.web_search_enabled and hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"[DIRECT_RESPONSE] LLM requested web search")
                tool_was_used = True
                
                try:
                    # Tool call 실행
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get("name", "")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id", "")
                        
                        if "search" in tool_name.lower():
                            query_to_search = tool_args.get("query", query)
                            logger.info(f"[DIRECT_RESPONSE] Executing web search for: '{query_to_search}'")
                            
                            # 웹 검색 실행
                            if hasattr(self.search_tool, 'search_sync'):
                                search_results = self.search_tool.search_sync(query_to_search)
                            else:
                                # Tool invoke 직접 호출
                                search_results = self.search_tool.invoke({"query": query_to_search})
                            
                            # 검색 결과 처리 및 분석
                            if search_results:
                                logger.info(f"[DIRECT_RESPONSE] Retrieved {len(search_results) if isinstance(search_results, list) else 1} web results")
                                
                                # 1. 검색 결과 구조화 분석
                                analysis = self.analyze_search_results(query, search_results if isinstance(search_results, list) else [search_results])
                                
                                # 2. 검색 결과 텍스트 준비 (전체 내용 사용)
                                if isinstance(search_results, list):
                                    results_text = "\n\n".join([
                                        f"Source: {doc.metadata.get('source', 'Web')}\nTitle: {doc.metadata.get('title', 'N/A')}\nContent: {doc.page_content}"
                                        for doc in search_results  # 모든 결과 사용, 내용 축소 없음
                                    ])
                                else:
                                    results_text = str(search_results)
                                
                                # 3. Chain of Thought 프롬프트 생성
                                if analysis:
                                    # 분석 결과에 기반한 CoT 프롬프트
                                    cot_prompt = f"""Based on your search and analysis, think through this step by step:

QUERY: {query}

STEP 1 - Query Understanding:
This query is {'time-sensitive and requires current information' if analysis.is_time_sensitive else 'a general knowledge query'}.

STEP 2 - Search Results Analysis:
Key facts from search: {'; '.join(analysis.key_facts[:5]) if analysis.key_facts else 'No specific facts extracted'}
Primary answer from search: {analysis.primary_answer}
Confidence level: {analysis.confidence_level}

STEP 3 - Information Reconciliation:
{'IMPORTANT: This is current/recent information that supersedes your training data.' if analysis.should_override_base_knowledge else 'Consider both search results and base knowledge.'}
Reasoning: {analysis.reasoning}

STEP 4 - Final Answer:
Based on the analysis above, provide a comprehensive answer that:
1. {'Prioritizes the search results as the authoritative source' if analysis.should_override_base_knowledge else 'Balances search results with established knowledge'}
2. Includes specific details from the search results
3. Mentions the document system information as required

Remember to respond in the same language as the query."""
                                    
                                    # CoT 프롬프트를 시스템 메시지로 추가
                                    conversation_messages.append(response)  # AI의 tool call 메시지
                                    conversation_messages.append(ToolMessage(
                                        content=f"Web search results:\n{results_text}",
                                        tool_call_id=tool_id
                                    ))
                                    conversation_messages.append(SystemMessage(content=cot_prompt))
                                else:
                                    # 분석 실패 시 기본 처리
                                    logger.warning(f"[DIRECT_RESPONSE] Search result analysis failed, using basic approach")
                                    conversation_messages.append(response)
                                    conversation_messages.append(ToolMessage(
                                        content=f"Web search results:\n{results_text}",
                                        tool_call_id=tool_id
                                    ))
                                
                                # 최종 응답 생성 (CoT 기반)
                                final_response = self.llm.invoke(conversation_messages)
                            else:
                                logger.warning(f"[DIRECT_RESPONSE] No web search results found")
                                final_response = response
                            
                except Exception as e:
                    logger.error(f"[DIRECT_RESPONSE] Web search failed: {e}")
                    # Tool 실행 실패 시 원래 응답 사용
                    final_response = response
            
            # MessagesState가 자동으로 누적하므로 새로운 메시지만 반환
            # HumanMessage는 이미 state에 있으므로 AIMessage만 추가
            new_messages = [
                AIMessage(content=final_response.content)
            ]
            
            # 최종 로깅
            logger.info(f"[DIRECT_RESPONSE] Response generation complete")
            logger.info(f"[DIRECT_RESPONSE] ├─ Context messages: {len(conversation_messages)}")
            logger.info(f"[DIRECT_RESPONSE] ├─ Web search used: {tool_was_used}")
            if tool_was_used:
                logger.info(f"[DIRECT_RESPONSE] ├─ Search analysis: {'CoT applied' if analysis else 'Basic approach'}")
            logger.info(f"[DIRECT_RESPONSE] └─ Response length: {len(final_response.content)} chars")
            
            return {
                "messages": new_messages,
                "final_answer": final_response.content,
                "workflow_status": "completed",
                "current_node": "direct_response",
                "metadata": {
                    **state.get("metadata", {}),
                    "direct_response": {
                        "query_type": "simple",
                        "model": self.llm.model_name,
                        "context_messages": len(conversation_messages),
                        "system_stats_included": True,
                        "web_search_enabled": self.web_search_enabled,
                        "web_search_used": tool_was_used
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"[DIRECT_RESPONSE] Failed: {str(e)}")
            
            # 에러 시에도 기존 메시지 유지
            existing_messages = state.get("messages", [])
            error_messages = existing_messages + [
                AIMessage(content=f"❌ 응답 생성 실패: {str(e)}")
            ]
            
            return {
                "messages": error_messages,
                "error": str(e),
                "workflow_status": "failed",
                "current_node": "direct_response"
            }
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        logger.debug(f"[DIRECT_RESPONSE] Invoke called (sync wrapper)")
        return self.__call__(state)