"""
Direct Response Node
단순 쿼리에 대해 LLM이 직접 응답하는 노드
"""

import os
import logging
from typing import Dict, Any
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class DirectResponseNode:
    """단순 쿼리에 대해 LLM이 직접 응답하는 노드"""
    
    def __init__(self):
        """초기화"""
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,  # 자연스러운 대화를 위해 약간 높임
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.response_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant. 
Answer the user's query directly and naturally.
If asked about automobile manufacturing, mention that you can help with technical questions if they search the documentation.
Keep responses concise and friendly.
Respond in the same language as the user's query."""),
            ("human", "{query}")
        ])
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        노드 실행 - 단순 LLM 호출
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[DIRECT_RESPONSE] Node started")
        
        try:
            query = state.get("query", "")
            
            messages = [
                AIMessage(content="💬 응답을 생성하고 있습니다...")
            ]
            
            # LLM 호출하여 응답 생성
            response = await self.llm.ainvoke(
                self.response_prompt.format_messages(query=query)
            )
            
            messages.append(
                AIMessage(content=response.content)
            )
            
            logger.info(f"[DIRECT_RESPONSE] Generated response")
            
            return {
                "messages": messages,
                "final_answer": response.content,
                "workflow_status": "completed",
                "current_node": "direct_response",
                "metadata": {
                    **state.get("metadata", {}),
                    "direct_response": {
                        "query_type": "simple",
                        "model": self.llm.model_name
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"[DIRECT_RESPONSE] Failed: {str(e)}")
            return {
                "messages": [
                    AIMessage(content=f"❌ 응답 생성 실패: {str(e)}")
                ],
                "error": str(e),
                "workflow_status": "failed",
                "current_node": "direct_response"
            }
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        logger.debug(f"[DIRECT_RESPONSE] Invoke called (sync wrapper)")
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            # 이미 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
            logger.debug(f"[DIRECT_RESPONSE] Event loop detected, using ThreadPoolExecutor")
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성하여 실행
            logger.debug(f"[DIRECT_RESPONSE] No event loop, creating new one")
            return asyncio.run(self.__call__(state))
        else:
            # 이미 이벤트 루프가 실행 중이면 별도 스레드에서 실행
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.__call__(state))
                return future.result()