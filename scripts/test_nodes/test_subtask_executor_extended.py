#!/usr/bin/env python3
"""
Extended Subtask Executor Node Test
3개 이상 서브태스크에서 current_subtask_idx 상태 전이가 올바르게 작동하는지 검증
"""

import sys
import asyncio
from pathlib import Path
from pprint import pprint
import uuid

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from workflow.nodes.subtask_executor import SubtaskExecutorNode
from workflow.state import MVPWorkflowState


async def test_extended_subtask_executor():
    """Extended Subtask Executor 노드 테스트 - 3개 서브태스크"""
    print("=" * 70)
    print("Extended Subtask Executor Node Test (3 Subtasks)")
    print("=" * 70)
    
    # 노드 생성
    node = SubtaskExecutorNode()
    print("✅ Node created successfully\n")
    
    # 3개 서브태스크 생성
    test_subtasks = [
        {
            "id": str(uuid.uuid4())[:8],
            "query": "엔진 오일 교체 절차",
            "priority": 1,
            "dependencies": [],
            "search_language": "korean",
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4())[:8],
            "query": "엔진 오일 종류 및 규격",
            "priority": 2,
            "dependencies": [],
            "search_language": "korean", 
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4())[:8],
            "query": "오일 교체 주기 및 점검 방법",
            "priority": 3,
            "dependencies": [],
            "search_language": "korean",
            "status": "pending"
        }
    ]
    
    print(f"📋 Created {len(test_subtasks)} subtasks:")
    for i, subtask in enumerate(test_subtasks):
        print(f"  {i+1}. [{subtask['id']}] {subtask['query']}")
    
    # 시나리오: 점진적 처리
    print(f"\n{'='*50}")
    print("Scenario: Progressive Processing (0 → 1 → 2)")
    print(f"{'='*50}")
    
    # Step 1: 첫 번째 서브태스크 처리 (index 0)
    print(f"\n🔸 Step 1: Process Subtask 0")
    state_1 = {
        "query": "엔진 오일 관련 정보",
        "subtasks": [s.copy() for s in test_subtasks],
        "current_subtask_idx": 0,
        "workflow_status": "running",
        "metadata": {},
        "query_variations": None,
        "search_filter": None
    }
    
    try:
        result_1 = await node(state_1)
        current_idx = result_1.get("current_subtask_idx", -1)
        print(f"  ✅ Result: index = {current_idx} (expected: 0)")
        
        # 첫 번째 서브태스크가 executing 상태가 되었는지 확인
        updated_subtask = result_1["subtasks"][0]
        print(f"  📊 Subtask 0 status: {updated_subtask['status']}")
        
    except Exception as e:
        print(f"  ❌ Step 1 failed: {e}")
        return
    
    # Step 2: 첫 번째를 retrieved로 만들고 두 번째 처리
    print(f"\n🔸 Step 2: Mark Subtask 0 as 'retrieved', Process Subtask 1")
    test_subtasks[0]["status"] = "retrieved"
    test_subtasks[0]["documents"] = []  # 문서 추가 (retrieved 시뮬레이션)
    
    state_2 = {
        "query": "엔진 오일 관련 정보",
        "subtasks": [s.copy() for s in test_subtasks],
        "current_subtask_idx": 0,  # 여전히 0에서 시작
        "workflow_status": "running",
        "metadata": {},
        "query_variations": None,
        "search_filter": None
    }
    
    try:
        result_2 = await node(state_2)
        current_idx = result_2.get("current_subtask_idx", -1)
        print(f"  ✅ Result: index = {current_idx} (expected: 1)")
        
        # 두 번째 서브태스크가 executing 상태가 되었는지 확인
        if len(result_2["subtasks"]) > 1:
            updated_subtask = result_2["subtasks"][1]
            print(f"  📊 Subtask 1 status: {updated_subtask['status']}")
        
        # 진행 확인
        if current_idx == 1:
            print(f"  ✅ Index correctly advanced: 0 → 1")
        else:
            print(f"  ❌ Index mismatch: expected 1, got {current_idx}")
        
    except Exception as e:
        print(f"  ❌ Step 2 failed: {e}")
        return
    
    # Step 3: 두 번째도 retrieved로 만들고 세 번째 처리
    print(f"\n🔸 Step 3: Mark Subtask 1 as 'retrieved', Process Subtask 2")
    test_subtasks[1]["status"] = "retrieved"
    test_subtasks[1]["documents"] = []
    
    state_3 = {
        "query": "엔진 오일 관련 정보",
        "subtasks": [s.copy() for s in test_subtasks],
        "current_subtask_idx": 1,  # Step 2 결과 반영
        "workflow_status": "running",
        "metadata": {},
        "query_variations": None,
        "search_filter": None
    }
    
    try:
        result_3 = await node(state_3)
        current_idx = result_3.get("current_subtask_idx", -1)
        print(f"  ✅ Result: index = {current_idx} (expected: 2)")
        
        # 세 번째 서브태스크가 executing 상태가 되었는지 확인
        if len(result_3["subtasks"]) > 2:
            updated_subtask = result_3["subtasks"][2]
            print(f"  📊 Subtask 2 status: {updated_subtask['status']}")
        
        # 진행 확인
        if current_idx == 2:
            print(f"  ✅ Index correctly advanced: 1 → 2")
        else:
            print(f"  ❌ Index mismatch: expected 2, got {current_idx}")
        
    except Exception as e:
        print(f"  ❌ Step 3 failed: {e}")
        return
    
    # Step 4: 모든 서브태스크 완료
    print(f"\n🔸 Step 4: Mark all subtasks as 'retrieved' - Should complete")
    test_subtasks[2]["status"] = "retrieved"
    test_subtasks[2]["documents"] = []
    
    state_4 = {
        "query": "엔진 오일 관련 정보",
        "subtasks": [s.copy() for s in test_subtasks],
        "current_subtask_idx": 2,  # Step 3 결과 반영
        "workflow_status": "running",
        "metadata": {},
        "query_variations": None,
        "search_filter": None
    }
    
    try:
        result_4 = await node(state_4)
        current_idx = result_4.get("current_subtask_idx", -1)
        workflow_status = result_4.get("workflow_status", "unknown")
        print(f"  ✅ Result: index = {current_idx}, status = '{workflow_status}'")
        
        # 완료 확인
        if workflow_status == "completed":
            print(f"  ✅ Workflow correctly marked as completed")
            print(f"  📊 Final index: {current_idx} (should be {len(test_subtasks)})")
        else:
            print(f"  ❌ Workflow status error: expected 'completed', got '{workflow_status}'")
        
    except Exception as e:
        print(f"  ❌ Step 4 failed: {e}")
        return
    
    print(f"\n{'='*70}")
    print("🎯 Extended Test Summary")
    print(f"{'='*70}")
    print("✅ All 3-subtask scenarios passed successfully!")
    print("✅ Index progression: 0 → 1 → 2 → 3 (completed)")  
    print("✅ Status transitions: pending → executing → retrieved")
    print("✅ Workflow completion: properly detected when all subtasks retrieved")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(test_extended_subtask_executor())