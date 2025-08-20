"""
Query Router Node
LLM reasoning을 사용하여 쿼리를 분류하고 적절한 처리 경로를 결정하는 노드
"""

import os
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class QueryClassification(BaseModel):
    """LLM이 추론한 쿼리 분류 결과"""
    type: Literal[
        "simple",              # RAG 불필요, LLM 직접 답변 가능
        "rag_required",        # 자동차 제조 문서 검색 필요
        "history_required"     # 이전 대화 참조 필요
    ]
    reasoning: str = Field(description="LLM의 추론 과정")
    confidence: float = Field(ge=0.0, le=1.0, description="분류 신뢰도")


class QueryRouterNode:
    """LLM reasoning으로 쿼리를 분류하고 라우팅하는 노드"""
    
    def __init__(self):
        """초기화"""
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent query classifier using reasoning, not pattern matching.

Analyze the query and recent conversation to determine the type:

1. **simple**: Query that can be answered with general knowledge without searching documents
   - Greetings, casual chat, general knowledge questions
   - Questions unrelated to automobile manufacturing
   
2. **rag_required**: Query that needs to search automobile manufacturing documents
   - Technical specifications, manufacturing processes
   - Quality standards, safety procedures
   - Any domain-specific information
   
3. **history_required**: Query that references previous conversation
   - Contains references like "이전에", "아까", "위에서", "that", "it", etc.
   - Needs context from earlier messages to be fully understood
   - After resolving references, might still need RAG

Use reasoning to decide, not keyword matching. Consider:
- Does this require domain-specific knowledge from documents?
- Are there unresolved references to previous conversation?
- Can I answer this with general knowledge alone?

Provide your reasoning process in the 'reasoning' field."""),
            ("human", """Query: {query}

Recent messages (for context):
{recent_messages}

Classify this query.""")
        ])
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[QUERY_ROUTER] Node started")
        
        try:
            query = state.get("query", "")
            messages = state.get("messages", [])
            
            # 진행 상황 메시지
            progress_messages = [
                AIMessage(content="🔍 쿼리를 분석하고 있습니다...")
            ]
            
            # 최근 메시지 컨텍스트 준비 (최대 5개)
            recent_messages = []
            for msg in messages[-10:] if messages else []:
                if isinstance(msg, (HumanMessage, AIMessage)):
                    msg_preview = str(msg.content)[:100] if hasattr(msg, 'content') else str(msg)[:100]
                    recent_messages.append(f"{msg.__class__.__name__}: {msg_preview}")
            recent_context = "\n".join(recent_messages) if recent_messages else "No previous messages"
            
            # LLM으로 분류
            structured_llm = self.llm.with_structured_output(QueryClassification)
            classification = await structured_llm.ainvoke(
                self.classification_prompt.format_messages(
                    query=query,
                    recent_messages=recent_context
                )
            )
            
            logger.info(f"[QUERY_ROUTER] Classification: {classification.type} (confidence: {classification.confidence:.2f})")
            logger.debug(f"[QUERY_ROUTER] Reasoning: {classification.reasoning}")
            
            # 완료 메시지
            type_emoji = {
                "simple": "💬",
                "rag_required": "🏭",
                "history_required": "🔄"
            }
            
            progress_messages.append(
                AIMessage(content=f"{type_emoji.get(classification.type, '❓')} 쿼리 타입: {classification.type}")
            )
            
            # State 업데이트
            result = {
                "messages": progress_messages,
                "query_type": classification.type,
                "current_node": "query_router",
                "metadata": {
                    **state.get("metadata", {}),
                    "query_classification": {
                        "type": classification.type,
                        "confidence": classification.confidence,
                        "reasoning": classification.reasoning
                    }
                }
            }
            
            logger.info(f"[QUERY_ROUTER] Node completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"[QUERY_ROUTER] Failed: {str(e)}")
            return {
                "messages": [
                    AIMessage(content=f"❌ 쿼리 분류 실패: {str(e)}")
                ],
                "error": str(e),
                "query_type": "rag_required",  # 기본값으로 RAG 처리
                "current_node": "query_router"
            }
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        logger.debug(f"[QUERY_ROUTER] Invoke called (sync wrapper)")
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            # 이미 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
            logger.debug(f"[QUERY_ROUTER] Event loop detected, using ThreadPoolExecutor")
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성하여 실행
            logger.debug(f"[QUERY_ROUTER] No event loop, creating new one")
            return asyncio.run(self.__call__(state))
        else:
            # 이미 이벤트 루프가 실행 중이면 별도 스레드에서 실행
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.__call__(state))
                return future.result()