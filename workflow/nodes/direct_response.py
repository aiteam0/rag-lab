"""
Direct Response Node
단순 쿼리에 대해 LLM이 직접 응답하는 노드
"""

import os
import logging
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from workflow.nodes.subtask_executor import MetadataHelper


load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class DirectResponseNode:
    """단순 쿼리에 대해 LLM이 직접 응답하는 노드"""
    
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
        
        # 기본 시스템 프롬프트 (DB 정보는 동적으로 추가)
        self.base_prompt = """You are a helpful AI assistant with knowledge about the document system.

{system_info}

IMPORTANT INSTRUCTIONS:
1. First, answer the user's query directly and naturally, considering the conversation context.
2. Then, ALWAYS include detailed information about the document system you manage as part of your response.
3. Integrate the document system information naturally into your answer when relevant, or mention it at the end.
4. The document information should include: total documents, sources, categories, and language support.
5. Make sure to mention specific numbers and details from the system information provided above.
6. Respond in the same language as the user's query.

Remember: Every response MUST include detailed document system information, regardless of the query type."""
    
    
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
            
            # 동적 시스템 프롬프트 생성
            dynamic_prompt = self.base_prompt.format(system_info=system_info)
            
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
            
            # LLM 호출하여 응답 생성
            response = self.llm.invoke(conversation_messages)
            
            # MessagesState가 자동으로 누적하므로 새로운 메시지만 반환
            # HumanMessage는 이미 state에 있으므로 AIMessage만 추가
            new_messages = [
                AIMessage(content=response.content)
            ]
            
            logger.info(f"[DIRECT_RESPONSE] Generated response with {len(conversation_messages)} messages in context")
            
            return {
                "messages": new_messages,
                "final_answer": response.content,
                "workflow_status": "completed",
                "current_node": "direct_response",
                "metadata": {
                    **state.get("metadata", {}),
                    "direct_response": {
                        "query_type": "simple",
                        "model": self.llm.model_name,
                        "context_messages": len(conversation_messages),
                        "system_stats_included": True
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