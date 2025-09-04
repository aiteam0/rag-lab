#!/usr/bin/env python3
"""
Test filter flow from generation to SQL
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from retrieval.search_filter import MVPSearchFilter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_filter_flow():
    """Test the complete filter flow"""
    
    # 1. Create filter as done by FILTER_OVERRIDE
    print("\n1. Creating filter with entity={'type': '똑딱이'}...")
    filter_obj = MVPSearchFilter(
        categories=None,
        pages=None,
        sources=None,
        caption=None,
        entity={'type': '똑딱이'}
    )
    
    # 2. Convert to dict (as done in subtask_executor)
    print("\n2. Converting filter to dict...")
    filter_dict = filter_obj.to_dict()
    print(f"   filter_dict: {filter_dict}")
    
    # 3. Simulate what happens in _dual_search_strategy
    print("\n3. Simulating _dual_search_strategy...")
    
    # Extract entity filter
    entity_filter = filter_dict.get("entity", None) if filter_dict else None
    general_filter_dict = {k: v for k, v in filter_dict.items() if k != "entity"} if filter_dict else {}
    
    print(f"   entity_filter: {entity_filter}")
    print(f"   general_filter_dict: {general_filter_dict}")
    
    # First search (general filter without entity)
    print("\n4. First search (general filter)...")
    general_filter = MVPSearchFilter(**general_filter_dict) if general_filter_dict else MVPSearchFilter()
    where_clause1, params1 = general_filter.to_sql_where()
    print(f"   WHERE clause: {where_clause1}")
    print(f"   Parameters: {params1}")
    
    # Second search (with entity filter)
    if entity_filter:
        print("\n5. Second search (with entity filter)...")
        entity_filter_dict = general_filter_dict.copy()
        entity_filter_dict["entity"] = entity_filter
        entity_filter_dict["categories"] = ["figure", "table", "paragraph", "heading1", "heading2", "heading3"]
        
        print(f"   entity_filter_dict: {entity_filter_dict}")
        
        entity_search_filter = MVPSearchFilter(**entity_filter_dict)
        where_clause2, params2 = entity_search_filter.to_sql_where()
        print(f"   WHERE clause: {where_clause2}")
        print(f"   Parameters: {params2}")
    else:
        print("\n5. No entity filter found - second search skipped")
    
    # 6. Test SQL query construction
    print("\n6. Example SQL query with entity filter:")
    if entity_filter:
        print(f"""
        SELECT * FROM mvp_ddu_documents
        WHERE {where_clause2}
        """)
        print(f"   With parameters: {params2}")

if __name__ == "__main__":
    test_filter_flow()