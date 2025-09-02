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
import psycopg
import json


load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class QueryClassification(BaseModel):
    """LLM이 추론한 쿼리 분류 결과"""
    type: Literal[
        "simple",              # RAG 불필요, LLM 직접 답변 가능
        "rag_required"         # 자동차 제조 문서 검색 필요
    ]
    reasoning: str = Field(description="LLM의 추론 과정")
    confidence: float = Field(ge=0.0, le=1.0, description="분류 신뢰도")


class QueryRouterNode:
    """LLM reasoning으로 쿼리를 분류하고 라우팅하는 노드"""
    
    def __init__(self):
        """초기화"""
        # ChatOpenAI 인스턴스 직접 생성
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # DB 연결 설정
        self.connection_string = (
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )
        self.table_name = os.getenv("DB_TABLE_NAME", "mvp_ddu_documents")
        
        # 동적 예시는 초기화 시 빈 값으로 설정
        self.rag_examples = []
        self.document_topics = []
        
        # 초기화 시 동적 예시 로드 시도
        try:
            # 동기 방식으로 동적 예시 로드
            logger.debug("Loading dynamic examples from database")
            self._load_dynamic_examples()
        except Exception as e:
            logger.warning(f"Failed to load dynamic examples: {e}")
            # 폴백: 기본 예시 사용
            self.rag_examples = ["엔진 오일 교체 주기는?", "차량 사양 정보", "브레이크 점검 방법"]
            self.document_topics = ["차량 관련 정보"]
        
        self.classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent query classifier using reasoning, not pattern matching.

Analyze the query and recent conversation to determine the type:

1. **simple**: Query that can be answered with general knowledge OR from conversation history OR about the system itself
   - Greetings, casual chat, general knowledge questions
   - Questions about the RAG system itself (문서 개수, 시스템 정보, 다루는 파일, 소스, 카테고리)
   - Questions unrelated to automobile manufacturing
   - Personal information from conversation (names, preferences, previously mentioned topics)
   - Follow-up questions about previous conversations (including automobile topics discussed)
   - Examples: 
     * "내 이름이 뭐야?", "안녕하세요", "날씨 어때?", "What's my name?", "How are you?"
     * "너가 다루고 있는 문서는 뭐야?", "몇 개의 문서 청크를 관리해?"
     * "어떤 소스 파일들이 있어?", "시스템에 대해 알려줘"
     * "What documents do you have?", "How many chunks are there?"
   
2. **rag_required**: Query that needs to search automobile manufacturing documents  
   - Technical specifications, manufacturing processes
   - Quality standards, safety procedures
   - Any NEW domain-specific information about vehicles that requires document lookup
   - Examples: {rag_examples}

Use reasoning to decide, not keyword matching. Consider:
- Is this about general conversation or previously discussed topics → simple
- Does this require NEW automobile document search → rag_required  
- Can I answer this from conversation history alone → simple

Provide your reasoning process in the 'reasoning' field.

"""),
            ("human", """Query: {query}

Recent messages (for context):
{recent_messages}

Available document topics: {document_topics}

Classify this query.""")
        ])
    
    def _load_dynamic_examples(self):
        """DB에서 실제 문서 정보를 로드하여 동적 예시 생성"""
        conn = None
        try:
            # DB 연결
            conn = psycopg.connect(self.connection_string)
            
            # 1. 주요 heading1 가져오기 (문서의 주요 섹션)
            query_headings = f"""
                SELECT DISTINCT page_content 
                FROM {self.table_name}
                WHERE category = 'heading1'
                LIMIT 10
            """
            with conn.cursor() as cur:
                cur.execute(query_headings)
                headings = cur.fetchall()
            
            # 2. 자주 나타나는 키워드 추출 (paragraph에서)
            query_keywords = f"""
                SELECT page_content 
                FROM {self.table_name}
                WHERE category = 'paragraph'
                LIMIT 20
            """
            with conn.cursor() as cur:
                cur.execute(query_keywords)
                paragraphs = cur.fetchall()
            
            # 3. Entity가 있는 문서에서 토픽 추출
            query_entities = f"""
                SELECT entity
                FROM {self.table_name}
                WHERE entity IS NOT NULL
                  AND entity != '{{}}'::jsonb
                LIMIT 10
            """
            with conn.cursor() as cur:
                cur.execute(query_entities)
                entities = cur.fetchall()
            
            # 동적 예시 생성
            self.rag_examples = []
            self.document_topics = []
            
            # Heading에서 예시 생성
            for row in headings[:3]:
                if row[0]:  # page_content is the first column
                    content = row[0].strip()
                    if len(content) > 5:
                        # 예시 질문 생성
                        self.rag_examples.append(f"{content}에 대해 알려줘")
                        self.document_topics.append(content)
            
            # Entity에서 토픽 추출
            for row in entities:
                if row[0]:  # entity is the first column
                    try:
                        entity_data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                        if 'title' in entity_data:
                            self.document_topics.append(entity_data['title'])
                        if 'keywords' in entity_data:
                            self.document_topics.extend(entity_data['keywords'][:2])
                    except:
                        pass
            
            # 키워드 기반 예시 추가
            common_terms = ['점검', '교체', '주기', '사양', '절차', '방법']
            for term in common_terms[:2]:
                for row in paragraphs:
                    if row[0] and term in row[0]:  # page_content is the first column
                        self.rag_examples.append(f"{term} 관련 정보")
                        break
            
            # 예시가 없으면 기본값 사용
            if not self.rag_examples:
                self.rag_examples = ["차량 정보", "사용 방법", "점검 절차"]
            
            if not self.document_topics:
                self.document_topics = ["차량 매뉴얼 관련 정보"]
            
            # 최대 5개로 제한
            self.rag_examples = self.rag_examples[:5]
            self.document_topics = self.document_topics[:10]
            
            logger.info(f"Loaded {len(self.rag_examples)} dynamic examples from DB")
            logger.debug(f"Examples: {self.rag_examples}")
            logger.debug(f"Topics: {self.document_topics}")
            
        except Exception as e:
            logger.error(f"Failed to load dynamic examples: {e}")
            # 폴백 예시
            self.rag_examples = ["차량 정보", "사용 방법", "점검 절차"]
            self.document_topics = ["차량 관련 정보"]
        finally:
            if conn:
                conn.close()
    
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[QUERY_ROUTER] Node started")
        
        try:
            # ALWAYS extract latest query from messages FIRST
            query = ""
            messages = state.get("messages", [])
            
            logger.debug(f"[QUERY_ROUTER] Extracting query from messages (count: {len(messages)})")
            
            # Always look for the most recent HumanMessage
            for msg in reversed(messages):
                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                    query = msg.content
                    # Handle structured content format (list of content blocks)
                    if isinstance(query, list) and len(query) > 0:
                        # Extract text from first text block
                        if isinstance(query[0], dict) and query[0].get('type') == 'text':
                            query = query[0].get('text', '')
                            logger.debug(f"[QUERY_ROUTER] Extracted text from structured content: '{query}'")
                        else:
                            # Fallback: convert to string if unexpected format
                            logger.warning(f"[QUERY_ROUTER] Unexpected structured content format: {query}")
                            query = str(query)
                    logger.info(f"[QUERY_ROUTER] Extracted query from HumanMessage: '{query}'")
                    break
                elif isinstance(msg, dict) and msg.get('type') == 'human':
                    query = msg.get('content', '')
                    # Handle structured content format for dict messages too
                    if isinstance(query, list) and len(query) > 0:
                        if isinstance(query[0], dict) and query[0].get('type') == 'text':
                            query = query[0].get('text', '')
                            logger.debug(f"[QUERY_ROUTER] Extracted text from structured dict content: '{query}'")
                        else:
                            logger.warning(f"[QUERY_ROUTER] Unexpected structured dict content format: {query}")
                            query = str(query)
                    logger.info(f"[QUERY_ROUTER] Extracted query from message dict: '{query}'")
                    break
            
            # Only use state.query as fallback if no HumanMessage found
            if not query or (isinstance(query, str) and query.strip() == ""):
                query = state.get("query", "")
                # Handle structured content in state.query too (edge case)
                if isinstance(query, list) and len(query) > 0:
                    if isinstance(query[0], dict) and query[0].get('type') == 'text':
                        query = query[0].get('text', '')
                        logger.debug(f"[QUERY_ROUTER] Extracted text from structured state.query: '{query}'")
                    else:
                        logger.warning(f"[QUERY_ROUTER] Unexpected structured state.query format: {query}")
                        query = str(query)
                if query:
                    logger.warning(f"[QUERY_ROUTER] No HumanMessage found, using state.query as fallback: '{query}'")
                else:
                    logger.debug(f"[QUERY_ROUTER] No query in state.query either")
            
            # Raise error if still no query
            if not query or (isinstance(query, str) and query.strip() == ""):
                logger.error(f"[QUERY_ROUTER] CRITICAL: No query found in state or messages")
                logger.error(f"[QUERY_ROUTER] State keys: {list(state.keys())}")
                logger.error(f"[QUERY_ROUTER] Messages count: {len(messages)}")
                if messages:
                    logger.error(f"[QUERY_ROUTER] Last message type: {type(messages[-1])}")
                    logger.error(f"[QUERY_ROUTER] Last message: {messages[-1]}")
                raise ValueError("No query found in state or messages. The query field must be provided or a HumanMessage must exist in messages.")
            
            # 최근 메시지 컨텍스트 준비 (최대 5개)
            recent_messages = []
            for msg in messages[-10:] if messages else []:
                if isinstance(msg, (HumanMessage, AIMessage)):
                    msg_preview = str(msg.content)[:100] if hasattr(msg, 'content') else str(msg)[:100]
                    recent_messages.append(f"{msg.__class__.__name__}: {msg_preview}")
            recent_context = "\n".join(recent_messages) if recent_messages else "No previous messages"
            
            # LLM으로 분류 (structured output 사용)
            try:
                structured_llm = self.llm.with_structured_output(
                    QueryClassification
                )
                classification = structured_llm.invoke(
                    self.classification_prompt.format_messages(
                        query=query,
                        recent_messages=recent_context,
                        rag_examples=", ".join(self.rag_examples) if self.rag_examples else "차량 관련 정보",
                        document_topics=", ".join(self.document_topics[:5]) if self.document_topics else "차량 매뉴얼 정보"
                    )
                )
            except Exception as e:
                logger.error(f"[QUERY_ROUTER] Failed to classify query: {e}")
                raise ValueError(f"Query classification failed: {e}")
            
            logger.info(f"[QUERY_ROUTER] Classification: {classification.type} (confidence: {classification.confidence:.2f})")
            logger.debug(f"[QUERY_ROUTER] Reasoning: {classification.reasoning}")
            
            # State 업데이트 (진행 메시지 없이)
            result = {
                "query": query,  # 원본 쿼리 보존
                "messages": [],  # 진행 메시지를 추가하지 않음
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
                "query": state.get("query", ""),  # 에러 시에도 쿼리 보존
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
        return self.__call__(state)