#!/usr/bin/env python3
"""
Subtask Executor Node Test
서브태스크 실행 노드가 쿼리 변형과 필터를 올바르게 생성하는지 테스트
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


async def test_subtask_executor():
    """Subtask Executor 노드 테스트"""
    print("=" * 60)
    print("Subtask Executor Node Test")
    print("=" * 60)
    
    # 노드 생성
    node = SubtaskExecutorNode()
    print("✅ Node created successfully\n")
    
    # 테스트용 서브태스크 생성
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
        }
    ]
    
    # 테스트 케이스 1: 첫 번째 서브태스크 처리
    print("\n" + "="*40)
    print("Test Case 1: Process First Subtask")
    print("="*40)
    
    state_1 = {
        "query": "엔진 오일 교체 방법",
        "subtasks": test_subtasks.copy(),
        "current_subtask_idx": 0,
        "workflow_status": "running",
        "metadata": {},
        "query_variations": None,
        "search_filter": None
    }
    
    try:
        result_1 = await node(state_1)
        
        # 결과 검증
        assert "query_variations" in result_1, "query_variations field missing"
        assert "subtasks" in result_1, "subtasks field missing"
        
        variations = result_1.get("query_variations", [])
        print(f"\n✅ Generated {len(variations)} query variations:")
        for i, var in enumerate(variations, 1):
            print(f"  {i}. {var}")
        
        # 서브태스크 상태 확인
        updated_subtask = result_1["subtasks"][0]
        print(f"\n📊 Subtask Status Update:")
        print(f"  - ID: {updated_subtask['id']}")
        print(f"  - Status: {updated_subtask['status']}")
        print(f"  - Has variations: {updated_subtask.get('query_variations') is not None}")
        
        # 필터 확인
        if result_1.get("search_filter"):
            print(f"\n🔍 Search Filter Generated:")
            pprint(result_1["search_filter"])
        else:
            print(f"\n🔍 No search filter (empty filter for broad search)")
        
    except Exception as e:
        print(f"❌ Test Case 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 2: 이미 처리된 서브태스크 (다음으로 진행)
    print("\n" + "="*40)
    print("Test Case 2: Skip Retrieved Subtask")
    print("="*40)
    
    # 첫 번째 서브태스크를 retrieved로 표시
    test_subtasks[0]["status"] = "retrieved"
    test_subtasks[0]["documents"] = []  # 문서 추가
    
    state_2 = {
        "query": "엔진 오일 교체 방법",
        "subtasks": test_subtasks.copy(),
        "current_subtask_idx": 0,  # 여전히 0
        "workflow_status": "running",
        "metadata": {},
        "query_variations": None,
        "search_filter": None
    }
    
    try:
        result_2 = await node(state_2)
        
        # current_subtask_idx가 증가했는지 확인
        new_idx = result_2.get("current_subtask_idx", 0)
        print(f"\n✅ Index advanced: 0 → {new_idx}")
        
        if new_idx == 1:
            print(f"  Next subtask: {test_subtasks[1]['query']}")
            
            # 두 번째 서브태스크의 query_variations 확인
            if result_2.get("query_variations"):
                print(f"\n✅ Generated variations for subtask 2:")
                for i, var in enumerate(result_2["query_variations"][:3], 1):
                    print(f"  {i}. {var}")
        
    except Exception as e:
        print(f"❌ Test Case 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 3: 모든 서브태스크 완료
    print("\n" + "="*40)
    print("Test Case 3: All Subtasks Completed")
    print("="*40)
    
    # 모든 서브태스크를 retrieved로 표시
    for subtask in test_subtasks:
        subtask["status"] = "retrieved"
        subtask["documents"] = []
    
    state_3 = {
        "query": "엔진 오일 교체 방법",
        "subtasks": test_subtasks.copy(),
        "current_subtask_idx": 1,  # 마지막 서브태스크
        "workflow_status": "running",
        "metadata": {},
        "query_variations": None,
        "search_filter": None
    }
    
    try:
        result_3 = await node(state_3)
        
        # workflow_status 확인
        status = result_3.get("workflow_status", "unknown")
        print(f"\n✅ Workflow Status: {status}")
        
        if status == "completed":
            print("  All subtasks have been processed!")
            print(f"  Final index: {result_3.get('current_subtask_idx', -1)}")
        
    except Exception as e:
        print(f"❌ Test Case 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Subtask Executor Test Completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_subtask_executor())