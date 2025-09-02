"""
Workflow State Definition for MVP RAG System
Central state that flows through all nodes in the LangGraph workflow
"""

from typing import List, Dict, Optional, Annotated, Any, TypedDict
from operator import add
from langchain_core.documents import Document
from langgraph.graph import MessagesState


def clearable_add(existing: List[Any], new: List[Any]) -> List[Any]:
    """
    Custom reducer that supports both adding and clearing documents.
    
    - 빈 리스트 [] 받으면: 전체 초기화 (multi-turn 대화에서 새 RAG 쿼리 시작)
    - 일반 리스트 받으면: 기존 리스트에 추가 (retrieval 결과 누적)
    
    Args:
        existing: 현재 state의 문서 리스트
        new: 새로 추가할 문서 리스트
        
    Returns:
        병합된 문서 리스트 (빈 리스트 시 초기화)
    """
    if new is None:
        return existing if existing else []
    
    # 특별한 경우: 빈 리스트는 초기화 신호 (multi-turn 대화 새 RAG 시작)
    if isinstance(new, list) and len(new) == 0:
        return []
    
    # 일반적인 경우: 추가 (retrieval 결과 누적)
    if existing is None:
        return new if isinstance(new, list) else []
    
    return existing + (new if isinstance(new, list) else [])


class MVPWorkflowState(MessagesState):
    """
    MVP 워크플로우 상태
    
    LangGraph의 모든 노드 간에 공유되는 중앙 상태 정의.
    각 노드는 이 상태를 읽고 수정할 수 있으며,
    Annotated[List, add]를 사용하여 리스트 필드는 추가 방식으로 업데이트됨.
    """
    
    # ===== 입력 필드 =====
    query: str                                    # 사용자의 원본 쿼리
    
    # ===== Plan-Execute-Observe 패턴 필드 =====
    subtasks: List[Dict[str, Any]]               # 분해된 서브태스크 목록
    current_subtask_idx: int                      # 현재 실행 중인 서브태스크 인덱스
    subtask_results: Annotated[List[Dict], add]   # 서브태스크 실행 결과 (누적)
    
    # ===== Multi-Query 처리 (서브태스크 레벨) =====
    query_variations: List[str]                   # 현재 서브태스크의 쿼리 변형 목록
    
    # ===== 검색 관련 필드 =====
    documents: Annotated[List[Document], clearable_add]  # 검색된 문서들 (누적, multi-turn 시 초기화 가능)
    search_filter: Optional[Dict[str, Any]]       # 현재 검색 필터 설정
    search_language: str                          # 검색 언어 ('korean' 또는 'english')
    
    # ===== 답변 생성 필드 =====
    intermediate_answer: Optional[str]            # 중간 답변 (서브태스크별)
    final_answer: Optional[str]                   # 최종 통합 답변
    
    # ===== CRAG (Corrective RAG) 품질 체크 =====
    hallucination_check: Optional[Dict[str, Any]] # 환각 체크 결과
    answer_grade: Optional[Dict[str, Any]]        # 답변 품질 평가 결과
    
    # ===== 제어 플래그 =====
    iteration_count: int                          # 현재 반복 횟수
    max_iterations: int                           # 최대 반복 횟수
    retry_count: int                              # CRAG 재시도 횟수 (synthesis 노드 재실행 카운트)
    should_use_web: bool                          # 웹 검색 사용 여부
    should_retry: bool                            # 재시도 필요 여부
    confidence_score: float                       # 현재 답변 신뢰도 (0.0-1.0)
    
    # ===== 에러 및 로깅 =====
    error: Optional[str]                          # 에러 메시지
    warnings: Annotated[List[str], add]           # 경고 메시지들 (누적)
    
    # ===== 메타데이터 =====
    metadata: Dict[str, Any]                      # 추가 메타데이터
    execution_time: Dict[str, float]              # 각 노드별 실행 시간
    
    # ===== 워크플로우 제어 =====
    next_node: Optional[str]                      # 다음 실행할 노드 (조건부 엣지용)
    workflow_status: str                          # 현재 워크플로우 상태 ('running', 'completed', 'failed')
    
    # ===== Query Routing 필드 (새로 추가) =====
    query_type: Optional[str]                     # 쿼리 타입: simple/rag_required/history_required
    enhanced_query: Optional[str]                 # 컨텍스트가 개선된 쿼리 (history_required인 경우)
    current_node: Optional[str]                   # 현재 실행 중인 노드 (디버깅용)


class SubtaskState(TypedDict):
    """서브태스크 개별 상태"""
    id: str                                       # 서브태스크 고유 ID
    query: str                                     # 서브태스크 쿼리
    priority: int                                  # 우선순위 (1-5, 1이 가장 높음)
    dependencies: List[str]                       # 의존하는 다른 서브태스크 ID들
    status: str                                    # 상태 ('pending', 'running', 'completed', 'failed')
    result: Optional[Dict[str, Any]]              # 실행 결과
    error: Optional[str]                          # 에러 메시지 (실패 시)
    documents: List[Document]                     # 이 서브태스크에서 검색된 문서들
    answer: Optional[str]                         # 서브태스크 답변


class QualityCheckResult(TypedDict):
    """품질 체크 결과"""
    is_valid: bool                                # 유효성 여부
    score: float                                  # 점수 (0.0-1.0)
    reason: str                                   # 판단 이유
    suggestions: List[str]                        # 개선 제안사항
    needs_retry: bool                             # 재시도 필요 여부


class SearchResult(TypedDict):
    """검색 결과"""
    documents: List[Document]                     # 검색된 문서들
    total_count: int                              # 전체 결과 수
    search_type: str                              # 검색 타입 ('semantic', 'keyword', 'hybrid')
    execution_time: float                         # 실행 시간 (초)
    confidence: float                             # 검색 신뢰도 (0.0-1.0)