#!/usr/bin/env python
"""
Minimal test to identify where the hang occurs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from retrieval.hybrid_search import HybridSearch

def test_minimal():
    """Test HybridSearch directly"""
    print("Creating HybridSearch instance...")
    try:
        searcher = HybridSearch()
        print("HybridSearch created successfully")
        
        print("\nTesting search with query: '엔진 오일'")
        results = searcher.search(
            query="엔진 오일",
            filter_dict=None,
            top_k=5
        )
        
        print(f"Search completed! Found {len(results)} results")
        
        # Check stats
        if hasattr(searcher, 'last_search_stats'):
            stats = searcher.last_search_stats
            print(f"Stats: {stats}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting minimal test...")
    test_minimal()
    print("Test completed!")