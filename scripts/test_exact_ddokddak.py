#!/usr/bin/env python3
"""
Test with exact query from filter_prompt example
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph

def test_exact_query():
    """Test with exact query from prompt example"""
    print("\n" + "="*60)
    print("Testing with EXACT query from filter_prompt")
    print("="*60)
    
    # 정확히 filter_prompt에 있는 예시 사용
    query = "똑딱이 타입 문서 목록 보여줘"
    print(f"\nQuery: '{query}'")
    
    workflow = MVPWorkflowGraph()
    result = workflow.run(query)
    
    # 결과 확인
    print(f"\nWorkflow status: {result.get('workflow_status')}")
    
    # 메타데이터에서 필터 확인
    metadata = result.get('metadata', {})
    for key in metadata:
        if key.startswith('subtask_'):
            subtask_meta = metadata[key]
            filter_applied = subtask_meta.get('filter_applied')
            if filter_applied:
                print(f"\n{key} filter: {filter_applied}")
                if 'entity' in filter_applied and filter_applied['entity'].get('type') == '똑딱이':
                    print("✅ SUCCESS: '똑딱이' filter generated!")
                    return True
    
    print("\n❌ No '똑딱이' filter found")
    return False

if __name__ == "__main__":
    success = test_exact_query()
    sys.exit(0 if success else 1)