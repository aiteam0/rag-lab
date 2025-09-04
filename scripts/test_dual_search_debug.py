#!/usr/bin/env python3
"""
Debug dual_search_strategy to see why entity filter is not working
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.retrieval import RetrievalNode
from retrieval.search_filter import MVPSearchFilter
import logging

logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')
logger = logging.getLogger(__name__)

def test_dual_search():
    """Test dual search with entity filter"""
    
    # Initialize retrieval node
    retrieval = RetrievalNode()
    retrieval._initialize()  # Initialize the hybrid_search
    
    # Create filter with entity type '똑딱이'
    filter_dict = {
        'entity': {'type': '똑딱이'}
    }
    
    print("\n=== Testing dual_search_strategy ===")
    print(f"Filter dict: {filter_dict}")
    
    # Test query
    query = "똑딱이 문서의 정의"
    
    # Call dual_search_strategy directly
    results = retrieval._dual_search_strategy(
        query=query,
        filter_dict=filter_dict,
        language='korean',
        top_k=10
    )
    
    print(f"\nTotal results: {len(results)}")
    
    # Check results
    ddokddak_count = 0
    gv80_count = 0
    
    for i, doc in enumerate(results[:5]):
        source = doc.metadata.get('source', 'unknown')
        entity = doc.metadata.get('entity', {})
        entity_type = entity.get('type') if entity else None
        
        if '디지털정부' in source:
            ddokddak_count += 1
        elif 'gv80' in source.lower():
            gv80_count += 1
            
        print(f"\n[{i+1}] Source: {source}")
        print(f"    Page: {doc.metadata.get('page')}")
        print(f"    Category: {doc.metadata.get('category')}")
        print(f"    Entity type: {entity_type}")
        print(f"    Content: {doc.page_content[:100]}...")
    
    print(f"\n=== Summary ===")
    print(f"'똑딱이' documents: {ddokddak_count}")
    print(f"GV80 documents: {gv80_count}")
    
    if ddokddak_count > 0:
        print("\n✅ SUCCESS: Entity filter is working!")
    else:
        print("\n❌ FAILURE: Entity filter is not working properly")

if __name__ == "__main__":
    test_dual_search()