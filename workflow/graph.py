"""
Main Workflow Graph
LangGraph 기반 P-E-O 패턴 워크플로우
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from dotenv import load_dotenv

load_dotenv()

# 환경변수 읽기 (단 2개만!)
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_file_path = os.getenv('LOG_FILE_PATH', '')  # 비어있으면 파일 로깅 비활성화

# 핸들러 리스트
handlers = []

# 1. 콘솔 핸들러 (항상 활성화)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
))
handlers.append(console_handler)

# 2. 파일 핸들러 (LOG_FILE_PATH가 설정된 경우만)
if log_file_path:
    # 로그 디렉토리 생성
    log_dir = Path(log_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 타임스탬프 추가 (테스트 실행마다 구분)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = Path(log_file_path).stem
    file_ext = Path(log_file_path).suffix
    actual_path = log_dir / f"{file_name}_{timestamp}{file_ext}"
    
    file_handler = logging.FileHandler(actual_path, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(name)-40s %(filename)s:%(lineno)d - %(message)s'
    ))
    handlers.append(file_handler)

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, log_level),
    handlers=handlers,
    force=True  # 기존 설정 덮어쓰기
)

# 서드파티 라이브러리 로그 억제 (자동 결정)
third_party_level = 'DEBUG' if log_level == 'DEBUG' else 'WARNING'
for lib in ['httpcore', 'openai', 'httpx', 'asyncio']:
    logging.getLogger(lib).setLevel(getattr(logging, third_party_level))

logger = logging.getLogger(__name__)

# 파일 로깅 활성화 시 안내 메시지
if log_file_path:
    logger.info(f"File logging enabled: {actual_path}")

# 노드들 import
from workflow.state import MVPWorkflowState
from workflow.nodes.planning_agent import PlanningAgentNode
from workflow.nodes.subtask_executor import SubtaskExecutorNode
from workflow.nodes.retrieval import RetrievalNode
from workflow.nodes.synthesis import SynthesisNode
from workflow.nodes.hallucination import HallucinationCheckNode
from workflow.nodes.answer_grader import AnswerGraderNode
from workflow.tools.tavily_search import TavilySearchTool

# 새로운 노드들 import (Query Routing 활성화시)
try:
    from workflow.nodes.query_router import QueryRouterNode
    from workflow.nodes.direct_response import DirectResponseNode
    # ContextEnhancementNode removed - using MessagesState for chat history
    ROUTING_AVAILABLE = True
except ImportError:
    logger.warning("Query routing nodes not found. Running in legacy mode.")
    ROUTING_AVAILABLE = False


class MVPWorkflowGraph:
    """MVP RAG 워크플로우 그래프"""
    
    def __init__(self, checkpointer_path: Optional[str] = None):
        """
        초기화
        
        Args:
            checkpointer_path: 체크포인트 저장 경로 (선택)
        """
        # Query Routing 활성화 확인
        self.enable_routing = os.getenv("ENABLE_QUERY_ROUTING", "true").lower() == "true" and ROUTING_AVAILABLE
        
        if self.enable_routing:
            logger.info("Query routing enabled")
            # 새로운 노드들 초기화
            self.query_router = QueryRouterNode()
            self.direct_response = DirectResponseNode()
            # ContextEnhancement removed - chat history flows through MessagesState
        else:
            logger.info("Query routing disabled, using legacy mode")
        
        # 기존 노드 초기화
        self.planning_node = PlanningAgentNode()
        self.subtask_executor = SubtaskExecutorNode()
        self.retrieval_node = RetrievalNode()
        self.synthesis_node = SynthesisNode()
        self.hallucination_check = HallucinationCheckNode()
        self.answer_grader = AnswerGraderNode()
        
        # Tavily 도구 초기화 (선택적)
        try:
            self.tavily_tool = TavilySearchTool(max_results=3)
            self.use_tavily = True
        except ValueError:
            print("Warning: Tavily API key not found. Web search disabled.")
            self.tavily_tool = None
            self.use_tavily = False
        
        # 체크포인터 설정 (선택적)
        self.checkpointer = None
        if checkpointer_path:
            self.checkpointer = SqliteSaver.from_conn_string(checkpointer_path)
        
        # 워크플로우 그래프 구성
        self.graph = self._build_graph()
        
        # 컴파일된 그래프 with recursion limit
        compiled_graph = self.graph.compile(checkpointer=self.checkpointer)
        
        # Recursion limit 계산 및 적용
        # 서브태스크 수 * 3 (executor, retrieval, search) + CRAG 재시도 * 4 + 기본 노드 + 버퍼
        max_subtasks = int(os.getenv("LANGGRAPH_PLANNING_MAX_SUBTASKS", "5"))
        max_retries = int(os.getenv("CRAG_MAX_RETRIES", "3"))
        recursion_limit = (max_subtasks * 3) + (max_retries * 4) + 10 + 20
        
        # with_config를 사용하여 recursion limit 적용
        self.app = compiled_graph.with_config(recursion_limit=recursion_limit)
    
    def _build_graph(self) -> StateGraph:
        """워크플로우 그래프 구성"""
        
        # StateGraph 생성
        workflow = StateGraph(MVPWorkflowState)
        
        # === Query Routing이 활성화된 경우 ===
        if self.enable_routing:
            # 새로운 노드들 추가
            workflow.add_node("query_router", self.query_router.invoke)
            workflow.add_node("direct_response", self.direct_response.invoke)
            # context_enhancement node removed
            
            # 엔트리포인트를 query_router로 설정
            workflow.set_entry_point("query_router")
            
            # Query Router에서의 조건부 라우팅 (simplified)
            def route_query(state: MVPWorkflowState) -> str:
                """쿼리 타입에 따른 라우팅 (simple or rag_required only)"""
                query_type = state.get("query_type", "rag_required")
                
                if query_type == "simple":
                    logger.info(f"[ROUTING] Simple query → DirectResponse")
                    return "direct_response"
                else:  # rag_required
                    logger.info(f"[ROUTING] RAG required → Planning")
                    return "planning"
            
            workflow.add_conditional_edges(
                "query_router",
                route_query,
                {
                    "direct_response": "direct_response",
                    "planning": "planning"
                }
            )
            
            # Direct Response는 바로 종료
            workflow.add_edge("direct_response", END)
            
            # Context Enhancement removed - using MessagesState
        else:
            # === Query Routing이 비활성화된 경우 (기존 동작) ===
            workflow.set_entry_point("planning")
        
        # === 기존 노드들 추가 (공통) ===
        workflow.add_node("planning", self.planning_node.invoke)
        workflow.add_node("subtask_executor", self.subtask_executor.invoke)
        workflow.add_node("retrieval", self.retrieval_node.invoke)
        workflow.add_node("synthesis", self.synthesis_node.invoke)
        workflow.add_node("hallucination_check", self.hallucination_check.invoke)
        workflow.add_node("answer_grader", self.answer_grader.invoke)
        
        # Tavily 검색 노드 (선택적)
        if self.use_tavily:
            workflow.add_node("web_search", self._web_search_node_sync)
        
        # === 엣지 정의 (기존 플로우는 동일) ===
        
        # Planning → Subtask Executor
        workflow.add_edge("planning", "subtask_executor")
        
        # Subtask Executor → Retrieval 또는 완료
        workflow.add_conditional_edges(
            "subtask_executor",
            self._should_continue_subtasks,
            {
                "continue": "retrieval",
                "complete": "synthesis",
                "failed": END
            }
        )
        
        # Retrieval → Web Search (필요시) 또는 다음 단계
        if self.use_tavily:
            workflow.add_conditional_edges(
                "retrieval",
                self._should_web_search,
                {
                    "search": "web_search",
                    "continue": "subtask_executor"
                }
            )
            # Web Search → Subtask Executor
            workflow.add_edge("web_search", "subtask_executor")
        else:
            # Tavily 없으면 바로 다음 서브태스크로
            workflow.add_edge("retrieval", "subtask_executor")
        
        # Synthesis → Hallucination Check
        workflow.add_edge("synthesis", "hallucination_check")
        
        # Hallucination Check → Answer Grader 또는 재시도
        workflow.add_conditional_edges(
            "hallucination_check",
            self._check_hallucination,
            {
                "valid": "answer_grader",
                "retry": "synthesis",
                "failed": END
            }
        )
        
        # Answer Grader → 완료 또는 재시도
        workflow.add_conditional_edges(
            "answer_grader",
            self._check_answer_quality,
            {
                "accept": END,
                "retry": "synthesis",
                "failed": END
            }
        )
        
        return workflow
    
    def _should_continue_subtasks(self, state: MVPWorkflowState) -> str:
        """서브태스크 계속 실행 여부 결정"""
        logger.debug(f"[CONDITIONAL] _should_continue_subtasks() called")
        
        # 에러 체크
        if state.get("error"):
            logger.warning(f"[CONDITIONAL] Found error in state: {state.get('error')}")
            return "failed"
        
        # 워크플로우 상태 체크
        workflow_status = state.get("workflow_status")
        logger.debug(f"[CONDITIONAL] Workflow status: {workflow_status}")
        if workflow_status == "completed":
            logger.info(f"[CONDITIONAL] Workflow marked as completed")
            return "complete"
        
        # 서브태스크 진행 상황 체크
        subtasks = state.get("subtasks", [])
        current_idx = state.get("current_subtask_idx", 0)
        logger.debug(f"[CONDITIONAL] Subtasks count: {len(subtasks)}, current_idx: {current_idx}")
        
        # 현재 처리할 서브태스크가 있는지 확인
        if current_idx >= len(subtasks):
            # 모든 서브태스크 완료
            logger.info(f"[CONDITIONAL] All subtasks completed ({current_idx}/{len(subtasks)})")
            return "complete"
        
        # 현재 서브태스크 상태 확인
        if subtasks:
            current_subtask = subtasks[current_idx]
            current_status = current_subtask.get("status", "pending")
            logger.debug(f"[CONDITIONAL] Current subtask[{current_idx}] status: {current_status}")
            
            # retrieved 상태면 다음 단계로 (subtask_executor가 인덱스 증가 처리)
            if current_status == "retrieved":
                logger.info(f"[CONDITIONAL] Subtask[{current_idx}] retrieved, continuing to next")
                return "continue"
        
        logger.info(f"[CONDITIONAL] Continuing with subtask {current_idx}")
        return "continue"
    
    def _should_web_search(self, state: MVPWorkflowState) -> str:
        """웹 검색 필요 여부 결정"""
        logger.debug(f"[CONDITIONAL] _should_web_search() called")
        
        if not self.use_tavily:
            logger.debug(f"[CONDITIONAL] Tavily not available, skipping web search")
            return "continue"
        
        # 검색 결과가 충분하지 않은 경우
        documents = state.get("documents", [])
        doc_count = len(documents)
        logger.debug(f"[CONDITIONAL] Current document count: {doc_count}")
        
        if doc_count < 3:
            # 문서가 3개 미만이면 웹 검색 수행
            logger.info(f"[CONDITIONAL] Insufficient documents ({doc_count} < 3), triggering web search")
            return "search"
        
        # 메타데이터에서 웹 검색 요청 확인
        metadata = state.get("metadata", {})
        require_web_search = metadata.get("require_web_search", False)
        logger.debug(f"[CONDITIONAL] Web search explicitly required: {require_web_search}")
        
        if require_web_search:
            logger.info(f"[CONDITIONAL] Web search explicitly required")
            return "search"
        
        logger.debug(f"[CONDITIONAL] Sufficient documents found, skipping web search")
        return "continue"
    
    def _check_hallucination(self, state: MVPWorkflowState) -> str:
        """환각 체크 결과 확인"""
        logger.debug(f"[CONDITIONAL] _check_hallucination() called")
        
        # 에러 체크
        if state.get("error"):
            logger.warning(f"[CONDITIONAL] Found error in state: {state.get('error')}")
            return "failed"
        
        hallucination_check = state.get("hallucination_check", {})
        is_valid = hallucination_check.get("is_valid", False)
        needs_retry = hallucination_check.get("needs_retry", False)
        logger.debug(f"[CONDITIONAL] Hallucination check - valid: {is_valid}, needs_retry: {needs_retry}")
        
        # 환각 검사 통과
        if is_valid:
            logger.info(f"[CONDITIONAL] Hallucination check passed")
            return "valid"
        
        # 재시도 필요
        if needs_retry:
            # 재시도 횟수 체크 (증가는 SynthesisNode에서 처리)
            retry_count = state.get("retry_count", 0)
            max_retries = int(os.getenv("CRAG_MAX_RETRIES", "3"))
            logger.debug(f"[CONDITIONAL] Current retry count: {retry_count}/{max_retries}")
            
            if retry_count < max_retries:
                logger.info(f"[CONDITIONAL] Hallucination check failed, will retry (current: {retry_count})")
                return "retry"
            else:
                logger.warning(f"[CONDITIONAL] Max retries reached for hallucination check")
        
        logger.error(f"[CONDITIONAL] Hallucination check failed permanently")
        return "failed"
    
    def _check_answer_quality(self, state: MVPWorkflowState) -> str:
        """답변 품질 체크 결과 확인"""
        logger.debug(f"[CONDITIONAL] _check_answer_quality() called")
        
        # 에러 체크
        if state.get("error"):
            logger.warning(f"[CONDITIONAL] Found error in state: {state.get('error')}")
            return "failed"
        
        answer_grade = state.get("answer_grade", {})
        is_valid = answer_grade.get("is_valid", False)
        needs_retry = answer_grade.get("needs_retry", False)
        logger.debug(f"[CONDITIONAL] Answer grade - valid: {is_valid}, needs_retry: {needs_retry}")
        
        # 품질 기준 통과
        if is_valid:
            logger.info(f"[CONDITIONAL] Answer quality check passed")
            return "accept"
        
        # 재시도 필요
        if needs_retry:
            # 재시도 횟수 체크 (증가는 SynthesisNode에서 처리)
            retry_count = state.get("retry_count", 0)
            max_retries = int(os.getenv("CRAG_MAX_RETRIES", "3"))
            logger.debug(f"[CONDITIONAL] Current retry count: {retry_count}/{max_retries}")
            
            if retry_count < max_retries:
                logger.info(f"[CONDITIONAL] Answer quality check failed, will retry (current: {retry_count})")
                return "retry"
            else:
                logger.warning(f"[CONDITIONAL] Max retries reached for answer quality check")
        
        logger.error(f"[CONDITIONAL] Answer quality check failed permanently")
        return "failed"
    
    async def _web_search_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """웹 검색 노드"""
        logger.info(f"[WEB_SEARCH] Node started")
        
        if not self.tavily_tool:
            logger.warning(f"[WEB_SEARCH] Tavily tool not available")
            return {"warnings": ["Web search unavailable"]}
        
        try:
            # 현재 쿼리 가져오기
            query = state.get("query", "")
            logger.debug(f"[WEB_SEARCH] Original query: '{query}'")
            
            # 서브태스크가 있으면 현재 서브태스크 쿼리 사용
            subtasks = state.get("subtasks", [])
            current_idx = state.get("current_subtask_idx", 0)
            logger.debug(f"[WEB_SEARCH] Subtasks: {len(subtasks)}, current_idx: {current_idx}")
            
            if subtasks and current_idx < len(subtasks):
                subtask_query = subtasks[current_idx].get("query", query)
                logger.info(f"[WEB_SEARCH] Using subtask query: '{subtask_query}'")
                query = subtask_query
            
            # 웹 검색 실행
            logger.info(f"[WEB_SEARCH] Executing search for: '{query}'")
            web_documents = await self.tavily_tool.search(query)
            logger.info(f"[WEB_SEARCH] Retrieved {len(web_documents)} web documents")
            
            # 기존 문서와 병합
            existing_docs = state.get("documents", [])
            all_documents = existing_docs + web_documents
            logger.debug(f"[WEB_SEARCH] Total documents: {len(existing_docs)} + {len(web_documents)} = {len(all_documents)}")
            
            # 메타데이터 업데이트
            metadata = state.get("metadata", {})
            metadata["web_search_performed"] = True
            metadata["web_search_results"] = len(web_documents)
            logger.debug(f"[WEB_SEARCH] Updated metadata")
            
            # 메시지 생성 - 웹 검색 과정 상세 정보
            messages = []
            
            # 1. 웹 검색 시작
            messages.append(
                AIMessage(content=f"🌐 웹 검색 시작: '{query[:100]}...'")
            )
            
            # 2. 검색 진행
            messages.append(
                AIMessage(content="🔍 Tavily API로 최신 정보 검색 중...")
            )
            
            # 3. 검색 결과
            if len(web_documents) > 0:
                messages.append(
                    AIMessage(content=f"📄 {len(web_documents)}개 웹 문서 발견")
                )
                messages.append(
                    AIMessage(content=f"✅ 총 {len(all_documents)}개 문서로 보강 완료 (기존 {len(existing_docs)}개 + 웹 {len(web_documents)}개)")
                )
            else:
                messages.append(
                    AIMessage(content="⚠️ 웹 검색 결과가 없습니다")
                )
            
            result = {
                "messages": messages,  # 메시지 추가
                "documents": all_documents,
                "metadata": metadata
            }
            
            # Clear error state if we found documents
            if len(web_documents) > 0:
                result["error"] = None  # Clear any previous errors
                result["workflow_status"] = "continuing"
                # 추가: state에서도 error 제거 (완전한 error 클리어)
                if "error" in state:
                    logger.info(f"[WEB_SEARCH] Removing error from state after successful web search")
                    # state에서 error를 제거하는 것은 result를 통해 처리
                    # LangGraph는 state를 직접 수정하지 않고 return value로 업데이트
                result["errors"] = []  # errors 리스트도 초기화
                result["warnings"] = []  # warnings도 초기화 (필요시)
                logger.info(f"[WEB_SEARCH] Cleared all error states after finding {len(web_documents)} documents")
            
            logger.info(f"[WEB_SEARCH] Node completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"[WEB_SEARCH] Search failed: {str(e)}")
            return {
                "warnings": [f"Web search failed: {str(e)}"]
            }
    
    def _web_search_node_sync(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """웹 검색 노드 (동기)"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            # 이미 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성하여 실행
            return asyncio.run(self._web_search_node(state))
        else:
            # 이미 이벤트 루프가 실행 중이면 별도 스레드에서 실행
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self._web_search_node(state))
                return future.result()
    
    async def arun(
        self, 
        query: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        비동기 실행
        
        Args:
            query: 사용자 쿼리
            config: 실행 설정
            
        Returns:
            최종 상태
        """
        initial_state = {
            "query": query,
            "workflow_status": "started",
            "metadata": {},
            "retry_count": 0,
            "documents": [],
            "execution_time": {},
            "current_subtask_idx": 0,
            "subtasks": []
        }
        
        # 그래프 실행 with error handling
        try:
            async for event in self.app.astream(initial_state, config=config):
                pass  # 스트리밍 처리 (필요시)
            
            # 최종 상태 반환
            return event
        except GraphRecursionError as e:
            print(f"⚠️  워크플로우가 recursion limit에 도달했습니다: {str(e)}")
            # 부분 결과 반환
            return {
                "error": "Recursion limit exceeded", 
                "query": query,
                "workflow_status": "failed",
                "partial_results": initial_state.get("subtask_results", [])
            }
    
    def run(
        self, 
        query: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        동기 실행
        
        Args:
            query: 사용자 쿼리
            config: 실행 설정
            
        Returns:
            최종 상태
        """
        initial_state = {
            "query": query,
            "workflow_status": "started",
            "metadata": {},
            "retry_count": 0,
            "documents": [],
            "execution_time": {},
            "current_subtask_idx": 0,
            "subtasks": []
        }
        
        # 그래프 실행 with error handling
        try:
            final_state = self.app.invoke(initial_state, config=config)
            return final_state
        except GraphRecursionError as e:
            print(f"⚠️  워크플로우가 recursion limit에 도달했습니다: {str(e)}")
            # 부분 결과 반환
            return {
                "error": "Recursion limit exceeded",
                "query": query,
                "workflow_status": "failed",
                "partial_results": initial_state.get("subtask_results", [])
            }
    
    def stream(
        self,
        query: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        스트리밍 실행
        
        Args:
            query: 사용자 쿼리
            config: 실행 설정
            
        Yields:
            중간 상태들
        """
        initial_state = {
            "query": query,
            "workflow_status": "started",
            "metadata": {},
            "retry_count": 0,
            "documents": [],
            "execution_time": {},
            "current_subtask_idx": 0,
            "subtasks": []
        }
        
        # 스트리밍으로 그래프 실행
        for event in self.app.stream(initial_state, config=config):
            yield event
    
    def get_graph_image(self, output_path: str = "workflow_graph.png"):
        """
        워크플로우 그래프 시각화
        
        Args:
            output_path: 이미지 저장 경로
        """
        try:
            from IPython.display import Image, display
            img = self.app.get_graph().draw_mermaid_png()
            
            # 파일로 저장
            with open(output_path, "wb") as f:
                f.write(img)
            
            print(f"Graph image saved to {output_path}")
            
            # Jupyter 환경이면 표시
            try:
                display(Image(img))
            except:
                pass
                
        except ImportError:
            print("Graph visualization requires IPython")
        except Exception as e:
            print(f"Failed to generate graph image: {e}")


# 헬퍼 함수
def create_workflow(checkpointer_path: Optional[str] = None) -> MVPWorkflowGraph:
    """
    워크플로우 생성 헬퍼 함수
    
    Args:
        checkpointer_path: 체크포인트 저장 경로
        
    Returns:
        MVPWorkflowGraph 인스턴스
    """
    return MVPWorkflowGraph(checkpointer_path)