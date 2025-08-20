#\!/usr/bin/env python3
"""
Debug test for workflow - minimal test
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph


async def test_workflow_async():
    """비동기 워크플로우 테스트"""
    print("=" * 60)
    print("Workflow Debug Test")
    print("=" * 60)
    
    try:
        # 워크플로우 생성
        print("\n1. Creating workflow...")
        workflow = MVPWorkflowGraph()
        print("   ✅ Workflow created")
        
        # 초기 상태 생성
        initial_state = {
            "query": "엔진 오일 교체",
            "workflow_status": "started",
            "metadata": {},
            "retry_count": 0,
            "documents": [],
            "execution_time": {},
            "current_subtask_idx": 0,
            "subtasks": []
        }
        
        print("\n2. Running workflow...")
        print(f"   Query: '{initial_state['query']}'")
        
        # 각 노드를 개별적으로 실행
        nodes_executed = []
        
        async for event in workflow.app.astream(initial_state):
            node_name = list(event.keys())[0] if event else "unknown"
            nodes_executed.append(node_name)
            print(f"   Node executed: {node_name}")
            
            # 상태 확인
            if node_name in event:
                node_state = event[node_name]
                
                # 에러 체크
                if node_state.get("error"):
                    print(f"   ❌ ERROR in {node_name}: {node_state['error']}")
                    return False
                
                # 주요 필드 체크
                if node_state.get("query_variations"):
                    print(f"      - query_variations: {len(node_state['query_variations'])} items")
                
                if node_state.get("documents") is not None:
                    print(f"      - documents: {len(node_state['documents'])} items")
                
                if node_state.get("subtasks"):
                    print(f"      - subtasks: {len(node_state['subtasks'])} items")
                    for idx, subtask in enumerate(node_state['subtasks']):
                        status = subtask.get('status', 'unknown')
                        print(f"        - subtask[{idx}]: status={status}")
                
                if node_state.get("current_subtask_idx") is not None:
                    print(f"      - current_subtask_idx: {node_state['current_subtask_idx']}")
                
                if node_state.get("workflow_status"):
                    print(f"      - workflow_status: {node_state['workflow_status']}")
            
            # 최대 10개 노드만 실행 (무한 루프 방지)
            if len(nodes_executed) > 10:
                print(f"\n⚠️  Too many nodes executed ({len(nodes_executed)}), stopping...")
                break
        
        print(f"\n3. Workflow completed")
        print(f"   Nodes executed: {nodes_executed}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    success = asyncio.run(test_workflow_async())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
