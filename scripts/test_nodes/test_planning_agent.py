#!/usr/bin/env python3
"""
Planning Agent Node Test
계획 노드가 쿼리를 서브태스크로 올바르게 분해하는지 테스트
"""

import sys
import asyncio
from pathlib import Path
from pprint import pprint

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from workflow.nodes.planning_agent import PlanningAgentNode
from workflow.state import MVPWorkflowState


async def test_planning_agent():
    """Planning Agent 노드 테스트"""
    print("=" * 60)
    print("Planning Agent Node Test")
    print("=" * 60)
    
    # 노드 생성
    node = PlanningAgentNode()
    print("✅ Node created successfully\n")
    
    # 테스트 케이스 정의
    test_cases = [
        {
            "name": "Problem Query - Oil Change",
            "query": "오일 교체에 대해 알려줘",
            "expected_subtasks": 1,  # 1개가 적절함 (단순한 오일 교체 정보)
            "description": "문제가 되는 쿼리 - 차량 안전 기능으로 잘못 해석되는 케이스"
        },
        {
            "name": "Simple Query",
            "query": "엔진 오일 교체 방법",
            "expected_subtasks": 1  # 최소 1개 이상
        },
        {
            "name": "Complex Query",
            "query": "차량 안전 기능과 연비 정보, 그리고 정기 점검 항목을 알려줘",
            "expected_subtasks": 2  # 최소 2개 이상
        },
        {
            "name": "English Query",
            "query": "How to change brake pads and check tire pressure",
            "expected_subtasks": 2  # 최소 2개 이상
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*40}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print("="*40)
        
        # 초기 state 생성
        state = {
            "query": test_case["query"],
            "workflow_status": "started",
            "metadata": {},
            "subtasks": [],
            "current_subtask_idx": 0
        }
        
        try:
            # 노드 실행
            result = await node(state)
            
            # 결과 검증
            assert "subtasks" in result, "subtasks field missing"
            assert "current_subtask_idx" in result, "current_subtask_idx field missing"
            assert "workflow_status" in result, "workflow_status field missing"
            
            subtasks = result["subtasks"]
            print(f"\n✅ Generated {len(subtasks)} subtasks:")
            
            for j, subtask in enumerate(subtasks, 1):
                print(f"\n  Subtask {j}:")
                print(f"    - Query: {subtask.get('query', 'N/A')}")
                print(f"    - Priority: {subtask.get('priority', 'N/A')}")
                print(f"    - Language: {subtask.get('search_language', 'N/A')}")
                print(f"    - Status: {subtask.get('status', 'N/A')}")
                print(f"    - ID: {subtask.get('id', 'N/A')[:8]}")
            
            # 최소 서브태스크 수 검증
            if len(subtasks) >= test_case["expected_subtasks"]:
                print(f"\n✅ Test passed: {len(subtasks)} >= {test_case['expected_subtasks']} subtasks")
            else:
                print(f"\n⚠️  Less subtasks than expected: {len(subtasks)} < {test_case['expected_subtasks']}")
            
            # 메타데이터 확인
            if "metadata" in result and "planning" in result["metadata"]:
                planning_meta = result["metadata"]["planning"]
                print(f"\n📊 Planning Metadata:")
                print(f"    - Strategy: {planning_meta.get('strategy', 'N/A')}")
                print(f"    - Complexity: {planning_meta.get('expected_complexity', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Planning Agent Test Completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_planning_agent())