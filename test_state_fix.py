#!/usr/bin/env python
"""
간단한 상태 전파 테스트
state field name mismatch 수정 확인
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from workflow.state import MVPWorkflowState
from workflow.nodes.planning_agent import PlanningAgentNode
from workflow.nodes.subtask_executor import SubtaskExecutorNode
from workflow.nodes.retrieval import RetrievalNode

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

async def test_state_propagation():
    """상태 전파 테스트"""
    try:
        # 초기 상태 생성
        state = MVPWorkflowState(
            query="엔진 오일 교체 방법",
            subtasks=[],
            current_subtask_idx=0,
            subtask_results=[],
            query_variations=[],  # state.py에 정의된 필드명
            documents=[],
            search_filter=None,
            search_language="korean",
            intermediate_answer=None,
            final_answer=None,
            hallucination_check=None,
            answer_grade=None,
            iteration_count=0,
            max_iterations=3,
            should_use_web=False,
            should_retry=False,
            confidence_score=0.0,
            error=None,
            warnings=[],
            metadata={},
            execution_time={},
            next_node=None,
            workflow_status="running"
        )
        
        # 1. Planning Agent 실행
        logger.info("=" * 60)
        logger.info("TEST 1: Planning Agent 실행")
        planning_agent = PlanningAgentNode()
        planning_result = await planning_agent(state)
        
        # 상태 업데이트
        for key, value in planning_result.items():
            if value is not None:
                state[key] = value
        
        logger.info(f"✓ Planning 완료: {len(state.get('subtasks', []))} 서브태스크 생성")
        
        # 2. SubtaskExecutor 실행
        logger.info("=" * 60)
        logger.info("TEST 2: SubtaskExecutor 실행")
        executor = SubtaskExecutorNode()
        executor_result = await executor(state)
        
        # 중요: query_variations 필드 확인
        if "query_variations" in executor_result:
            logger.info(f"✓ SubtaskExecutor가 'query_variations' 반환: {len(executor_result['query_variations'])} 개")
        else:
            logger.error(f"✗ SubtaskExecutor가 'query_variations' 반환하지 않음!")
            logger.error(f"  반환된 키: {list(executor_result.keys())}")
            return False
        
        # 상태 업데이트
        for key, value in executor_result.items():
            if value is not None:
                state[key] = value
        
        # 3. Retrieval Node 실행 (상태 전파 확인)
        logger.info("=" * 60)
        logger.info("TEST 3: Retrieval Node 실행 (상태 전파 확인)")
        
        # state에 query_variations가 있는지 확인
        if "query_variations" in state and state["query_variations"]:
            logger.info(f"✓ State에 'query_variations' 존재: {len(state['query_variations'])} 개")
        else:
            logger.error(f"✗ State에 'query_variations' 없음!")
            logger.error(f"  State 키: {list(state.keys())}")
            return False
        
        retrieval = RetrievalNode()
        try:
            retrieval_result = await retrieval(state)
            logger.info(f"✓ Retrieval Node 성공적으로 실행됨")
            logger.info(f"  검색된 문서: {len(retrieval_result.get('documents', []))} 개")
            return True
        except ValueError as e:
            if "Query variations not found" in str(e):
                logger.error(f"✗ Retrieval Node 실패: {e}")
                logger.error(f"  State 키: {list(state.keys())}")
                return False
            raise
            
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 리소스 정리
        if 'retrieval' in locals():
            await retrieval.cleanup()

async def main():
    """메인 함수"""
    logger.info("상태 전파 수정 테스트 시작")
    logger.info("=" * 60)
    
    success = await test_state_propagation()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ 테스트 성공: 상태 전파 문제가 해결되었습니다!")
    else:
        logger.error("❌ 테스트 실패: 상태 전파 문제가 여전히 존재합니다.")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)