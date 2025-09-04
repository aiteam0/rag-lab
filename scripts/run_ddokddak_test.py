#!/usr/bin/env python3
"""
Run ddokddak query and monitor logs
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
import logging

# 로깅 설정 - 파일과 콘솔에 출력
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

print("\n" + "="*60)
print("Running '똑딱이 문서에 대해 알려줘' Query")
print("="*60)

workflow = MVPWorkflowGraph()
query = "똑딱이 문서에 대해 알려줘"

print(f"\nQuery: '{query}'")
print("\nExecuting workflow... (monitor logs for FILTER_OVERRIDE)")
print("-" * 40)

try:
    result = workflow.run(query)
    
    print("\n" + "-" * 40)
    print("Workflow completed!")
    print(f"Status: {result.get('workflow_status')}")
    
    # Check if filter was applied
    metadata = result.get('metadata', {})
    for key in metadata:
        if key.startswith('subtask_'):
            subtask_meta = metadata[key]
            filter_applied = subtask_meta.get('filter_applied')
            if filter_applied and 'entity' in filter_applied:
                print(f"\n✅ Filter applied: {filter_applied['entity']}")
    
    # Check documents
    documents = result.get('documents', [])
    ddokddak_count = 0
    
    for doc in documents:
        entity = doc.metadata.get('entity')
        if entity and entity.get('type') == '똑딱이':
            ddokddak_count += 1
    
    print(f"\n📚 Results:")
    print(f"  Total documents: {len(documents)}")
    print(f"  '똑딱이' documents: {ddokddak_count}")
    
    if ddokddak_count > 0:
        print("\n✅ SUCCESS: '똑딱이' documents were retrieved!")
    else:
        print("\n❌ FAILURE: No '똑딱이' documents found")
        
except Exception as e:
    print(f"\n❌ Error: {e}")