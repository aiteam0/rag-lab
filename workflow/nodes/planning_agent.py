"""
Planning Agent Node
쿼리를 분석하여 서브태스크로 분해하는 계획 노드
"""

import os
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from workflow.state import MVPWorkflowState, SubtaskState
import uuid


load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class Subtask(BaseModel):
    """서브태스크 스키마"""
    query: str = Field(description="서브태스크를 위한 구체적인 쿼리")
    priority: int = Field(description="우선순위 (1-5, 1이 가장 높음)", ge=1, le=5)
    dependencies: List[str] = Field(default_factory=list, description="의존하는 다른 서브태스크 인덱스")
    search_language: str = Field(default="korean", description="검색 언어 (korean/english)")


class ExecutionPlan(BaseModel):
    """실행 계획 스키마"""
    subtasks: List[Subtask] = Field(description="서브태스크 목록")
    strategy: str = Field(description="실행 전략 설명")
    expected_complexity: str = Field(description="예상 복잡도 (simple/moderate/complex)")


class PlanningAgentNode:
    """쿼리를 서브태스크로 분해하는 계획 노드"""
    
    def __init__(self):
        """초기화"""
        # ChatOpenAI 인스턴스 직접 생성
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 최대 서브태스크 수를 환경변수에서 읽기
        self.max_subtasks = int(os.getenv("LANGGRAPH_PLANNING_MAX_SUBTASKS", "5"))
        
        self.planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query planning expert for a RAG system about automobile manufacturing.
Your task is to break down complex user queries into manageable subtasks.

Rules:
1. Create between 1 and {max_subtasks} subtasks maximum
2. Each subtask should be specific and answerable
3. Order subtasks by logical dependencies
4. Keep subtasks focused and atomic
5. Identify whether Korean or English search would be more effective for each subtask
6. For vehicle-specific queries, prefer Korean language
7. For technical specifications, consider using English

⚠️ CRITICAL: DO NOT ADD FORMAT SPECIFICATIONS
Create subtasks ONLY for what the user explicitly requested.
DO NOT add format specifications (tables, lists, charts, images) unless explicitly mentioned by the user.

STRICT RULES:
1. If user says "오일 사양을 알려주세요" → Create subtask: "오일 사양"
2. If user says "표로 정리된 오일 사양" → Create subtask: "표로 정리된 오일 사양"  
3. NEVER transform "오일 사양" into "표로 정리된 오일 사양"
4. Focus on CONTENT retrieval, not PRESENTATION format

Filter Hint Keywords to PRESERVE ONLY IF PRESENT in original query:
- Table/Chart: IF user mentions "표로", "테이블", "표 형태", "차트" → Keep these exact words
- Image/Figure: IF user mentions "그림으로", "이미지", "도식" → Keep these exact words
- Page Reference: IF user mentions "N페이지" → Keep exact page reference
- Entity Types: IF user mentions "구조도", "회로도" → Keep these exact words

EXAMPLES:
✅ GOOD: "엔진 오일 사양" → "엔진 오일 사양" (no format added)
✅ GOOD: "표로 정리된 오일 사양" → "표로 정리된 오일 사양" (preserved user's format)
❌ BAD: "엔진 오일 사양" → "표로 정리된 오일 사양" (added format not requested)

Consider the following when creating subtasks:
- Is this a simple lookup or complex analysis?
- Does it require multiple pieces of information?
- Are there dependencies between different parts?
- Which language would yield better search results?
- MOST IMPORTANT: Are filter hints (table, image, page) preserved in each subtask?

Examples:
- "A와 B에 대해 알려줘" → 2 subtasks focusing on what user asked (A information, B information)
- "오일 교체 방법" → 1 subtask (오일 교체 절차)
- "브레이크 점검과 정비" → 2 subtasks (브레이크 점검, 브레이크 정비)
- "표로 정리된 엔진 사양" → "표에 나온 엔진 사양" (PRESERVE "표")"""),
            ("human", """Query: {query}

Break this down into subtasks. Consider:
1. What specific information is being requested?
2. Are there multiple distinct questions?
3. What order makes logical sense?
4. Which language (korean/english) would be best for each part?

Create an execution plan with subtasks.""")
        ])
    
    
    def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[PLANNING] Node started")
        
        try:
            query = state["query"]
            logger.debug(f"[PLANNING] Processing query: '{query}'")
            
            # Multi-turn 대화에서 새로운 RAG 쿼리 시작 시 이전 문서 초기화
            # Custom clearable_add reducer가 빈 리스트를 초기화 신호로 인식
            logger.info(f"[PLANNING] Clearing previous documents for new RAG query")
            
            # LLM을 사용하여 쿼리 분석 및 서브태스크 생성 (structured output 사용)
            logger.debug(f"[PLANNING] Creating structured LLM with max_subtasks={self.max_subtasks}")
            try:
                structured_llm = self.llm.with_structured_output(
                    ExecutionPlan
                )
                
                logger.info(f"[PLANNING] Generating execution plan...")
                formatted_messages = self.planning_prompt.format_messages(
                    query=query,
                    max_subtasks=self.max_subtasks
                )
                
                # 디버깅: 프롬프트 내용 로깅
                logger.debug(f"[PLANNING] Input query: '{query}'")
                logger.debug(f"[PLANNING] Formatted prompt (last 500 chars): ...{str(formatted_messages)[-500:]}")
                
                plan = structured_llm.invoke(formatted_messages)
            except Exception as e:
                logger.error(f"[PLANNING] Failed to generate execution plan: {e}")
                raise ValueError(f"Planning failed: {e}")
            
            # 디버깅: ExecutionPlan 상세 정보 로깅
            logger.info(f"[PLANNING] Generated {len(plan.subtasks)} subtasks, strategy: {plan.strategy}")
            logger.info(f"[PLANNING] Original query: '{query}'")
            logger.info(f"[PLANNING] Generated strategy: '{plan.strategy}'")
            logger.info(f"[PLANNING] Expected complexity: '{plan.expected_complexity}'")
            
            # 각 서브태스크 상세 정보 로깅
            for i, subtask in enumerate(plan.subtasks):
                logger.info(f"[PLANNING] Subtask {i+1}: '{subtask.query}' (priority: {subtask.priority}, lang: {subtask.search_language})")
                if subtask.dependencies:
                    logger.info(f"[PLANNING]   Dependencies: {subtask.dependencies}")
            
            # 원본 쿼리와 생성된 서브태스크 간의 관련성 확인
            original_keywords = query.lower().split()
            for i, subtask in enumerate(plan.subtasks):
                subtask_keywords = subtask.query.lower().split()
                common_keywords = set(original_keywords) & set(subtask_keywords)
                logger.info(f"[PLANNING] Subtask {i+1} keyword overlap with original: {len(common_keywords)}/{len(original_keywords)} - {list(common_keywords)}")
            
            # 서브태스크를 상태 형식으로 변환
            subtasks = []
            for i, task in enumerate(plan.subtasks):
                subtask_state: SubtaskState = {
                    "id": str(uuid.uuid4()),
                    "query": task.query,
                    "priority": task.priority,
                    "dependencies": task.dependencies,
                    "status": "pending",
                    "result": None,
                    "error": None,
                    "documents": [],
                    "answer": None
                }
                subtasks.append(subtask_state)
                logger.debug(f"[PLANNING] Subtask {i}: '{task.query}' (priority: {task.priority})")
            
            # 우선순위와 의존성에 따라 정렬
            original_order = [st["query"][:30] + "..." for st in subtasks]
            subtasks.sort(key=lambda x: (x["priority"], len(x["dependencies"])))
            sorted_order = [st["query"][:30] + "..." for st in subtasks]
            logger.debug(f"[PLANNING] Subtasks sorted by priority - before: {original_order}, after: {sorted_order}")
            
            # 메타데이터 업데이트
            metadata = state.get("metadata", {})
            metadata["planning"] = {
                "total_subtasks": len(subtasks),
                "strategy": plan.strategy,
                "complexity": plan.expected_complexity
            }
            logger.info(f"[PLANNING] Planning completed - {len(subtasks)} subtasks, complexity: {plan.expected_complexity}")
            
            # 서브태스크 상세 정보 로깅
            for i, subtask_state in enumerate(subtasks):
                priority = subtask_state['priority'] 
                query_preview = subtask_state['query'][:60] + ('...' if len(subtask_state['query']) > 60 else '')
                logger.info(f"[PLANNING] Subtask {i+1}: [P:{priority}] \"{query_preview}\"")
            
            # 메시지 생성 (스트리밍 지원)
            # 서브태스크 목록 생성
            subtask_list = "\n".join([f"  {i+1}. {task['query']}" for i, task in enumerate(subtasks)])
            
            messages = [
                AIMessage(content=f"📋 다음 {len(subtasks)}개 작업으로 나누어 검색합니다:\n{subtask_list}")
            ]
            
            result = {
                "messages": messages,
                "subtasks": subtasks,
                "current_subtask_idx": 0,
                "metadata": metadata,
                "workflow_status": "running",
                "current_node": "planning",
                "documents": [],  # Custom reducer가 빈 리스트를 초기화 신호로 인식
                "retry_count": 0  # Reset retry count for new RAG query
            }
            logger.info(f"[PLANNING] Node completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"[PLANNING] Planning failed: {str(e)}")
            return {
                "error": f"Planning failed: {str(e)}",
                "workflow_status": "failed"
            }
    
    def invoke(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        logger.debug(f"[PLANNING] Invoke called (sync wrapper)")
        return self.__call__(state)