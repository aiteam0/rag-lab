#!/usr/bin/env python3
"""
Comprehensive Workflow Integration Test
전체 워크플로우가 노드 간 상태 전이를 올바르게 수행하는지 테스트
"""

import sys
import asyncio
from pathlib import Path
import uuid
from typing import Dict, Any

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from workflow.nodes.planning_agent import PlanningAgentNode
from workflow.nodes.subtask_executor import SubtaskExecutorNode
from workflow.nodes.retrieval import RetrievalNode
from workflow.nodes.synthesis import SynthesisNode
from workflow.nodes.hallucination import HallucinationCheckNode
from workflow.nodes.answer_grader import AnswerGraderNode
from workflow.state import MVPWorkflowState


class WorkflowIntegrationTest:
    """워크플로우 통합 테스트 클래스"""
    
    def __init__(self):
        self.nodes = {
            "planning": PlanningAgentNode(),
            "executor": SubtaskExecutorNode(), 
            "retrieval": RetrievalNode(),
            "synthesis": SynthesisNode(),
            "hallucination": HallucinationCheckNode(),
            "grader": AnswerGraderNode()
        }
        self.test_results = {}
    
    async def run_complete_workflow(self, test_query: str, scenario_name: str):
        """완전한 워크플로우 실행"""
        print(f"\n{'='*80}")
        print(f"🚀 WORKFLOW INTEGRATION TEST: {scenario_name}")
        print(f"Query: {test_query}")
        print(f"{'='*80}")
        
        # 초기 상태
        state = {
            "query": test_query,
            "subtasks": [],
            "current_subtask_idx": 0,
            "documents": [],
            "query_variations": [],
            "search_filter": None,
            "final_answer": None,
            "intermediate_answer": None,
            "confidence_score": 0.0,
            "search_language": None,
            "hallucination_check": None,
            "answer_grade": None,
            "metadata": {},
            "execution_time": {},
            "workflow_status": "running",
            "retry_count": 0,
            "max_retries": 2
        }
        
        workflow_steps = []
        
        try:
            # Step 1: Planning Agent
            print(f"\n🎯 STEP 1: Planning Agent")
            print(f"{'='*50}")
            state = await self.execute_node_with_logging("planning", state, workflow_steps)
            
            if not state.get("subtasks"):
                raise ValueError("Planning failed: No subtasks generated")
            
            print(f"✅ Generated {len(state['subtasks'])} subtasks")
            
            # Step 2-4: Process each subtask (Executor → Retrieval → Synthesis)
            subtask_count = len(state["subtasks"])
            for i in range(subtask_count):
                state["current_subtask_idx"] = i
                current_subtask = state["subtasks"][i]
                
                print(f"\n📋 SUBTASK {i+1}/{subtask_count}: {current_subtask['query']}")
                print(f"{'='*60}")
                
                # Skip if already retrieved
                if current_subtask.get("status") == "retrieved":
                    print(f"  ⏭️  Already processed, skipping...")
                    continue
                
                # Subtask Executor
                print(f"  🔧 Step 2.{i+1}: Subtask Executor")
                state = await self.execute_node_with_logging("executor", state, workflow_steps)
                
                # Retrieval
                print(f"  🔍 Step 3.{i+1}: Retrieval")
                state = await self.execute_node_with_logging("retrieval", state, workflow_steps)
                
                retrieved_docs = len(state.get("documents", []))
                print(f"    Retrieved {retrieved_docs} documents")
                
                # Synthesis (intermediate answer for subtask)
                print(f"  📝 Step 4.{i+1}: Synthesis")
                state = await self.execute_node_with_logging("synthesis", state, workflow_steps)
                
                # Check if we got an answer
                answer = state.get("intermediate_answer") or state.get("final_answer")
                if answer:
                    print(f"    Generated answer ({len(answer)} chars)")
                
            # Step 5: Final Synthesis (if needed)
            if not state.get("final_answer") and state.get("workflow_status") == "running":
                print(f"\n📄 STEP 5: Final Synthesis")
                print(f"{'='*50}")
                # Reset to process all subtasks for final answer
                state["current_subtask_idx"] = 0
                state = await self.execute_node_with_logging("synthesis", state, workflow_steps)
            
            # Step 6: Hallucination Check
            if state.get("final_answer"):
                print(f"\n🔍 STEP 6: Hallucination Check")
                print(f"{'='*50}")
                state = await self.execute_node_with_logging("hallucination", state, workflow_steps)
                
                hall_result = state.get("hallucination_check", {})
                is_valid = hall_result.get("is_valid", False)
                score = hall_result.get("score", 0.0)
                print(f"    Hallucination check: {'PASS' if is_valid else 'FAIL'} (score: {score:.3f})")
                
                # Step 7: Answer Grader (only if hallucination check passed)
                if is_valid:
                    print(f"\n📊 STEP 7: Answer Grader")
                    print(f"{'='*50}")
                    state = await self.execute_node_with_logging("grader", state, workflow_steps)
                    
                    grade_result = state.get("answer_grade", {})
                    grade_valid = grade_result.get("is_valid", False)
                    grade_score = grade_result.get("score", 0.0)
                    print(f"    Answer grade: {'PASS' if grade_valid else 'FAIL'} (score: {grade_score:.3f})")
                else:
                    print(f"    ⚠️  Skipping answer grader due to hallucination")
            
            # Final Results
            self.print_workflow_summary(state, workflow_steps, scenario_name)
            return state, workflow_steps
            
        except Exception as e:
            print(f"\n❌ WORKFLOW FAILED: {e}")
            import traceback
            traceback.print_exc()
            return state, workflow_steps
    
    async def execute_node_with_logging(self, node_name: str, state: Dict[str, Any], workflow_steps: list) -> Dict[str, Any]:
        """노드 실행 및 로깅"""
        import time
        start_time = time.time()
        
        try:
            # 실행 전 상태 스냅샷
            pre_state = {
                "subtasks": len(state.get("subtasks", [])),
                "documents": len(state.get("documents", [])),
                "has_answer": bool(state.get("final_answer") or state.get("intermediate_answer")),
                "workflow_status": state.get("workflow_status"),
                "current_idx": state.get("current_subtask_idx", 0)
            }
            
            # 노드 실행
            result = await self.nodes[node_name](state)
            
            # 실행 시간 기록
            execution_time = time.time() - start_time
            
            # 실행 후 상태 스냅샷
            post_state = {
                "subtasks": len(result.get("subtasks", [])),
                "documents": len(result.get("documents", [])),
                "has_answer": bool(result.get("final_answer") or result.get("intermediate_answer")),
                "workflow_status": result.get("workflow_status"),
                "current_idx": result.get("current_subtask_idx", 0)
            }
            
            # 워크플로우 단계 기록
            workflow_steps.append({
                "node": node_name,
                "execution_time": execution_time,
                "pre_state": pre_state,
                "post_state": post_state,
                "success": True,
                "error": None
            })
            
            print(f"    ✅ {node_name.title()} completed ({execution_time:.3f}s)")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            workflow_steps.append({
                "node": node_name,
                "execution_time": execution_time,
                "pre_state": pre_state if 'pre_state' in locals() else {},
                "post_state": {},
                "success": False,
                "error": str(e)
            })
            print(f"    ❌ {node_name.title()} failed: {e}")
            raise
    
    def print_workflow_summary(self, final_state: Dict[str, Any], workflow_steps: list, scenario_name: str):
        """워크플로우 요약 출력"""
        print(f"\n{'='*80}")
        print(f"📊 WORKFLOW SUMMARY: {scenario_name}")
        print(f"{'='*80}")
        
        # 실행 통계
        total_time = sum(step["execution_time"] for step in workflow_steps)
        successful_steps = sum(1 for step in workflow_steps if step["success"])
        
        print(f"\n📈 Execution Statistics:")
        print(f"  - Total execution time: {total_time:.3f}s")
        print(f"  - Successful steps: {successful_steps}/{len(workflow_steps)}")
        print(f"  - Final workflow status: {final_state.get('workflow_status', 'unknown')}")
        
        # 상태 요약
        print(f"\n📋 Final State Summary:")
        print(f"  - Subtasks generated: {len(final_state.get('subtasks', []))}")
        print(f"  - Documents retrieved: {len(final_state.get('documents', []))}")
        print(f"  - Final answer length: {len(final_state.get('final_answer', ''))}")
        print(f"  - Confidence score: {final_state.get('confidence_score', 0.0):.3f}")
        
        # 품질 체크 결과
        hall_check = final_state.get("hallucination_check", {})
        answer_grade = final_state.get("answer_grade", {})
        
        print(f"\n🔍 Quality Assessment:")
        print(f"  - Hallucination check: {'PASS' if hall_check.get('is_valid') else 'FAIL'}")
        print(f"  - Hallucination score: {hall_check.get('score', 0.0):.3f}")
        print(f"  - Answer grade: {'PASS' if answer_grade.get('is_valid') else 'FAIL'}")
        print(f"  - Grade score: {answer_grade.get('score', 0.0):.3f}")
        
        # 단계별 실행 시간
        print(f"\n⏱️  Step Execution Times:")
        for step in workflow_steps:
            status = "✅" if step["success"] else "❌"
            print(f"  {status} {step['node'].title()}: {step['execution_time']:.3f}s")
        
        # 최종 답변 미리보기
        final_answer = final_state.get("final_answer", "")
        if final_answer:
            print(f"\n📝 Final Answer Preview:")
            print(f"{'='*60}")
            preview = final_answer[:500] + "..." if len(final_answer) > 500 else final_answer
            print(preview)
            print(f"{'='*60}")


async def run_integration_tests():
    """통합 테스트 실행"""
    test_runner = WorkflowIntegrationTest()
    
    print("🧪 Starting Comprehensive Workflow Integration Tests")
    print("="*80)
    
    # 테스트 시나리오들
    test_scenarios = [
        {
            "name": "Normal Success Path",
            "query": "엔진 오일 교체 방법을 자세히 설명해주세요",
            "description": "일반적인 성공 시나리오"
        },
        {
            "name": "Technical Query", 
            "query": "차량 정비 매뉴얼에서 브레이크 패드 교체 절차",
            "description": "기술적 쿼리 처리"
        },
        {
            "name": "Bilingual Query",
            "query": "How to check tire pressure in Korean manual",
            "description": "이중 언어 쿼리 처리"
        }
    ]
    
    results = {}
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🎯 RUNNING TEST SCENARIO {i}/{len(test_scenarios)}")
        try:
            final_state, workflow_steps = await test_runner.run_complete_workflow(
                scenario["query"],
                scenario["name"]
            )
            results[scenario["name"]] = {
                "success": final_state.get("workflow_status") == "completed",
                "final_state": final_state,
                "workflow_steps": workflow_steps
            }
        except Exception as e:
            print(f"❌ Scenario '{scenario['name']}' failed: {e}")
            results[scenario["name"]] = {
                "success": False,
                "error": str(e)
            }
    
    # 전체 테스트 결과 요약
    print(f"\n{'='*80}")
    print("🏆 INTEGRATION TEST RESULTS SUMMARY")
    print(f"{'='*80}")
    
    successful_scenarios = sum(1 for r in results.values() if r.get("success"))
    total_scenarios = len(results)
    
    print(f"\n📊 Overall Results:")
    print(f"  - Successful scenarios: {successful_scenarios}/{total_scenarios}")
    print(f"  - Success rate: {(successful_scenarios/total_scenarios)*100:.1f}%")
    
    for scenario_name, result in results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"  {status} {scenario_name}")
        if not result.get("success") and result.get("error"):
            print(f"        Error: {result['error']}")
    
    print(f"\n{'='*80}")
    print("🎯 Integration Tests Completed")
    print(f"{'='*80}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_integration_tests())