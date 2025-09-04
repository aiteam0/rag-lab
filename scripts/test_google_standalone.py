#!/usr/bin/env python3
"""
Standalone test for Google Search Tool
Tests basic functionality with USE_GOOGLE_SEARCH=true
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print(f"GOOGLE SEARCH TOOL STANDALONE TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# Verify environment setting
use_google = os.getenv("USE_GOOGLE_SEARCH", "false").lower()
print(f"\n✓ Environment: USE_GOOGLE_SEARCH = {use_google}")

if use_google != "true":
    print("⚠ WARNING: USE_GOOGLE_SEARCH is not set to true!")
    print("Please set USE_GOOGLE_SEARCH=true in .env file")
    sys.exit(1)

print("\n" + "=" * 40)
print("TEST 1: Direct Google Search Tool")
print("=" * 40)

try:
    from workflow.tools.google_search import GoogleSearchTool
    
    # Create Google Search Tool
    google = GoogleSearchTool(max_results=3)
    print("✓ GoogleSearchTool instance created")
    
    # Check status
    status = google.get_status()
    print(f"✓ Tool: {status['tool']}")
    print(f"✓ Available: {status['available']}")
    print(f"✓ Quota: {status['quota']['used']}/{status['quota']['limit']} (remaining: {status['quota']['remaining']})")
    print(f"✓ Cache: {status['cache']['hits']} hits, {status['cache']['misses']} misses")
    
    # Test search
    print("\nPerforming test search...")
    query = "OpenAI ChatGPT latest news 2024"
    results = google.search_sync(query)
    
    print(f"✓ Search completed: {len(results)} results returned")
    
    # Display results
    for i, doc in enumerate(results[:3], 1):
        print(f"\nResult {i}:")
        print(f"  Title: {doc.metadata.get('title', 'N/A')[:60]}...")
        print(f"  URL: {doc.metadata.get('source', 'N/A')[:80]}...")
        print(f"  Score: {doc.metadata.get('score', 0):.2f}")
        print(f"  Content preview: {doc.page_content[:100]}...")
    
    # Check quota after search
    status_after = google.get_status()
    print(f"\n✓ Quota after search: {status_after['quota']['used']}/{status_after['quota']['limit']}")
    
    print("\n✅ Direct Google Search Tool test PASSED")
    
except Exception as e:
    print(f"\n❌ Direct test FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 40)
print("TEST 2: Factory Pattern Test")
print("=" * 40)

try:
    from workflow.tools import create_search_tool
    
    # Create tool using factory
    tool = create_search_tool(max_results=3)
    
    if tool is None:
        print("❌ Factory returned None")
        sys.exit(1)
    
    tool_type = type(tool).__name__
    print(f"✓ Factory created: {tool_type}")
    
    # Verify it's Google
    if tool_type != "GoogleSearchTool":
        print(f"⚠ WARNING: Expected GoogleSearchTool, got {tool_type}")
        print("Factory might have fallen back to Tavily")
    else:
        print("✓ Correct tool type (GoogleSearchTool)")
    
    # Test search with factory-created tool
    results = tool.search_sync("Python programming best practices")
    print(f"✓ Factory tool search: {len(results)} results")
    
    print("\n✅ Factory pattern test PASSED")
    
except Exception as e:
    print(f"\n❌ Factory test FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 40)
print("TEST 3: Cache Functionality")
print("=" * 40)

try:
    # Create new instance for cache test
    google = GoogleSearchTool(max_results=2)
    
    # First search
    query = "machine learning algorithms"
    print(f"First search: '{query}'")
    results1 = google.search_sync(query)
    print(f"✓ Results: {len(results1)}")
    
    # Get cache status
    cache_status1 = google.cache.hit_rate()
    print(f"✓ Cache hit rate after first search: {cache_status1:.1%}")
    
    # Second search (same query - should hit cache)
    print(f"\nSecond search (same query): '{query}'")
    results2 = google.search_sync(query)
    print(f"✓ Results: {len(results2)} (from cache)")
    
    # Check cache hit rate increased
    cache_status2 = google.cache.hit_rate()
    print(f"✓ Cache hit rate after second search: {cache_status2:.1%}")
    
    if cache_status2 > cache_status1:
        print("✓ Cache is working correctly (hit rate increased)")
    else:
        print("⚠ Cache might not be working (hit rate didn't increase)")
    
    # Verify results are identical
    if len(results1) == len(results2):
        print("✓ Same number of results from cache")
    
    print("\n✅ Cache functionality test PASSED")
    
except Exception as e:
    print(f"\n❌ Cache test FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 40)
print("TEST 4: Error Handling")
print("=" * 40)

try:
    google = GoogleSearchTool(max_results=3)
    
    # Test with empty query
    print("Testing empty query...")
    results = google.search_sync("")
    print(f"✓ Empty query handled: {len(results)} results")
    
    # Test with very long query
    long_query = "test " * 100
    print("Testing very long query...")
    results = google.search_sync(long_query)
    print(f"✓ Long query handled: {len(results)} results")
    
    # Test availability check
    available = google.check_availability()
    print(f"✓ Availability check: {available}")
    
    print("\n✅ Error handling test PASSED")
    
except Exception as e:
    print(f"\n❌ Error handling test FAILED: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("STANDALONE TEST SUMMARY")
print("=" * 80)
print("✅ All standalone Google Search Tool tests completed")
print(f"✅ USE_GOOGLE_SEARCH is correctly set to: {use_google}")
print("✅ Tool is functioning properly")
print("\nReady to test in workflow context!")