"""
Context Enhancement Node
LLM이 대화 히스토리를 보고 참조를 해결하는 노드
"""

import os
import logging
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class ContextEnhancementNode:
    """LLM이 대화 히스토리를 보고 참조를 해결하는 노드"""
    
    def __init__(self):
        """초기화"""
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.enhancement_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are analyzing a follow-up query that references previous conversation.

Your task: Create a self-contained query by resolving references using conversation history.

Process:
1. Identify what the user is referring to (이전에, 아까, that, it, etc.)
2. Find the relevant context from previous messages
3. Create a complete query that doesn't need context to understand
4. Preserve the original intent and question

Important:
- Only add necessary context, don't over-elaborate
- Keep technical terms accurate
- The enhanced query should be searchable in documents
- If the query is already self-contained, return it as is

Example:
- History: "GV80 엔진의 조립 공정을 알려줘"
- Follow-up: "거기에 필요한 도구는?"
- Enhanced: "GV80 엔진 조립 공정에 필요한 도구"

Another example:
- History: "배터리 생산 라인의 효율성 보고서"
- Follow-up: "아까 말한 것의 작년 대비 개선율"
- Enhanced: "배터리 생산 라인 효율성의 작년 대비 개선율"
"""),
            ("human", """Original query: {query}

Recent conversation:
{conversation_history}

Create a self-contained enhanced query:""")
        ])
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[CONTEXT_ENHANCEMENT] Node started")
        
        try:
            query = state.get("query", "")
            messages = state.get("messages", [])
            
            progress_messages = [
                AIMessage(content="🔄 이전 대화 컨텍스트를 분석하고 있습니다...")
            ]
            
            # 대화 히스토리 준비
            conversation_history = []
            for msg in messages[-10:] if messages else []:  # 최근 10개 메시지
                if isinstance(msg, HumanMessage):
                    conversation_history.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage) and not str(msg.content).startswith("🔄"):
                    # 진행 상황 메시지 제외
                    content_preview = str(msg.content)[:200] if hasattr(msg, 'content') else str(msg)[:200]
                    conversation_history.append(f"Assistant: {content_preview}")
            
            history_text = "\n".join(conversation_history) if conversation_history else "No previous conversation"
            
            # 쿼리 개선
            response = await self.llm.ainvoke(
                self.enhancement_prompt.format_messages(
                    query=query,
                    conversation_history=history_text
                )
            )
            
            enhanced_query = response.content.strip()
            logger.info(f"[CONTEXT_ENHANCEMENT] Enhanced: '{query}' → '{enhanced_query}'")
            
            progress_messages.append(
                AIMessage(content=f"✅ 컨텍스트 적용 완료: {enhanced_query}")
            )
            
            return {
                "messages": progress_messages,
                "enhanced_query": enhanced_query,  # 개선된 쿼리 저장
                "query": enhanced_query,  # Planning 노드를 위해 query도 업데이트
                "current_node": "context_enhancement",
                "metadata": {
                    **state.get("metadata", {}),
                    "context_enhancement": {
                        "original_query": query,
                        "enhanced_query": enhanced_query,
                        "history_used": len(conversation_history)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"[CONTEXT_ENHANCEMENT] Failed: {str(e)}")
            # 실패시 원본 쿼리 사용
            return {
                "messages": [
                    AIMessage(content=f"⚠️ 컨텍스트 개선 실패, 원본 쿼리 사용: {state.get('query', '')}")
                ],
                "current_node": "context_enhancement",
                "enhanced_query": state.get("query", ""),  # 원본 쿼리 유지
                "error": None  # 에러를 전파하지 않고 계속 진행
            }
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        logger.debug(f"[CONTEXT_ENHANCEMENT] Invoke called (sync wrapper)")
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            # 이미 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
            logger.debug(f"[CONTEXT_ENHANCEMENT] Event loop detected, using ThreadPoolExecutor")
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성하여 실행
            logger.debug(f"[CONTEXT_ENHANCEMENT] No event loop, creating new one")
            return asyncio.run(self.__call__(state))
        else:
            # 이미 이벤트 루프가 실행 중이면 별도 스레드에서 실행
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.__call__(state))
                return future.result()