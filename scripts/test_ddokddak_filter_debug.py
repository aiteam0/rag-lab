#!/usr/bin/env python3
"""
Debug filter generation for '똑딱이' entity type
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.subtask_executor import SubtaskExecutorNode
from workflow.state import MVPWorkflowState
import os
from dotenv import load_dotenv
import logging

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def test_ddokddak_filter():
    """Test filter generation directly"""
    print("\n" + "="*60)
    print("Testing Filter Generation for '똑딱이'")
    print("="*60)
    
    try:
        # SubtaskExecutorNode 초기화
        executor = SubtaskExecutorNode()
        
        # 간단한 state 생성
        state = MVPWorkflowState(
            query="똑딱이 문서 목록",
            subtasks=[{
                "id": "test",
                "query": "똑딱이 문서 목록",
                "description": "List of 똑딱이 documents",
                "priority": 1,
                "expected_language": "korean",
                "status": "pending"
            }],
            current_subtask_idx=0
        )
        
        # 노드 실행
        print("\nExecuting SubtaskExecutorNode...")
        result = executor(state)
        
        print("\n" + "-"*40)
        print("Result:")
        
        # metadata 확인
        metadata = result.get("metadata", {})
        if "subtask_1" in metadata:
            subtask_meta = metadata["subtask_1"]
            print(f"  Query variations: {subtask_meta.get('query_variations', [])}")
            print(f"  Entity type: {subtask_meta.get('entity_type')}")
            print(f"  Filter applied: {subtask_meta.get('filter_applied')}")
            
            filter_applied = subtask_meta.get('filter_applied')
            if filter_applied and 'entity' in filter_applied:
                entity = filter_applied['entity']
                if entity.get('type') == '똑딱이':
                    print("\n✅ SUCCESS: '똑딱이' entity filter was generated!")
                else:
                    print(f"\n❌ FAILURE: Wrong entity type: {entity.get('type')}")
            else:
                print("\n❌ FAILURE: No entity filter generated!")
        else:
            print("  No subtask metadata found")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ddokddak_filter()
    sys.exit(0 if success else 1)