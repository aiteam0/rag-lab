#!/usr/bin/env python3
"""
Quick test for filter generation
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.subtask_executor import SubtaskExecutorNode, QueryExtraction
import os
from dotenv import load_dotenv

load_dotenv()

def test_filter_generation():
    """Test filter generation for '똑딱이' queries"""
    print("\n" + "="*60)
    print("Testing Filter Generation for '똑딱이'")
    print("="*60)
    
    executor = SubtaskExecutorNode()
    metadata = executor._get_metadata_sync()
    
    print(f"\nAvailable entity types: {metadata.get('entity_types', [])}")
    
    # Test queries
    test_cases = [
        ("똑딱이 문서에 대해 알려줘", "Should generate '똑딱이' filter"),
        ("똑딱이 문서의 정의", "Should generate '똑딱이' filter"),
        ("PPT 삽입 문서 목록", "Should generate '똑딱이' filter"),
    ]
    
    for query, description in test_cases:
        print(f"\n📝 Test: {description}")
        print(f"   Query: '{query}'")
        
        # Extract query info
        extraction = executor._extract_query_info(query, metadata)
        print(f"   Entity type extracted: {extraction.entity_type}")
        
        # Generate filter
        filter_obj = executor._generate_filter(query, extraction, metadata)
        
        if filter_obj and filter_obj.entity:
            print(f"   ✅ Entity filter generated: {filter_obj.entity}")
        else:
            print(f"   ❌ No entity filter generated")
            if filter_obj:
                print(f"   Other filters: {filter_obj.to_dict()}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_filter_generation()