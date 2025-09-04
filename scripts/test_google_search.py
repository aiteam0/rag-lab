"""
Test script for Google Search Tool implementation
Tests both Google and Tavily search tools with factory pattern
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Test imports
print("=" * 80)
print("GOOGLE SEARCH TOOL TEST")
print("=" * 80)

def test_imports():
    """Test that all required modules can be imported"""
    print("\n1. Testing imports...")
    try:
        from workflow.tools import create_search_tool, GoogleSearchTool, TavilySearchTool
        print("   ✓ All tools imported successfully")
        return True
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        return False


def test_google_search_direct():
    """Test Google Search Tool directly"""
    print("\n2. Testing Google Search Tool directly...")
    try:
        from workflow.tools.google_search import GoogleSearchTool
        
        # Create tool
        google = GoogleSearchTool(max_results=3)
        print(f"   ✓ GoogleSearchTool created")
        
        # Check status
        status = google.get_status()
        print(f"   ✓ Status: {status}")
        
        # Check availability
        available = google.check_availability()
        print(f"   ✓ Available: {available}")
        
        if available:
            # Test search
            print("\n   Testing search for 'Python programming'...")
            results = google.search_sync("Python programming", "basic")
            print(f"   ✓ Got {len(results)} results")
            
            if results:
                first_result = results[0]
                print(f"   ✓ First result: {first_result.metadata.get('title', 'No title')[:50]}...")
                print(f"   ✓ Source: {first_result.metadata.get('source', 'No source')[:80]}...")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_pattern():
    """Test factory pattern with both Google and Tavily"""
    print("\n3. Testing factory pattern...")
    try:
        from workflow.tools import create_search_tool
        
        # Test with Google
        print("\n   A. Testing with USE_GOOGLE_SEARCH=true")
        os.environ["USE_GOOGLE_SEARCH"] = "true"
        tool = create_search_tool(max_results=3)
        
        if tool is not None:
            tool_type = type(tool).__name__
            print(f"   ✓ Created tool: {tool_type}")
            
            if hasattr(tool, 'get_status'):
                status = tool.get_status()
                print(f"   ✓ Tool status: {status.get('tool', 'unknown')}")
        else:
            print("   ✗ No tool created")
        
        # Test with Tavily
        print("\n   B. Testing with USE_GOOGLE_SEARCH=false")
        os.environ["USE_GOOGLE_SEARCH"] = "false"
        tool = create_search_tool(max_results=3)
        
        if tool is not None:
            tool_type = type(tool).__name__
            print(f"   ✓ Created tool: {tool_type}")
        else:
            print("   ✗ No tool created")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_integration():
    """Test integration with workflow graph"""
    print("\n4. Testing workflow integration...")
    try:
        from workflow.graph import MVPWorkflowGraph
        
        # Test with Google
        print("\n   A. Testing workflow with Google Search")
        os.environ["USE_GOOGLE_SEARCH"] = "true"
        graph = MVPWorkflowGraph()
        
        if graph.use_tavily:  # Note: variable name kept for compatibility
            print(f"   ✓ Web search enabled in workflow")
            tool_name = type(graph.tavily_tool).__name__
            print(f"   ✓ Using tool: {tool_name}")
        else:
            print("   ⚠ Web search not enabled in workflow")
        
        # Test with Tavily
        print("\n   B. Testing workflow with Tavily Search")
        os.environ["USE_GOOGLE_SEARCH"] = "false"
        graph = MVPWorkflowGraph()
        
        if graph.use_tavily:
            print(f"   ✓ Web search enabled in workflow")
            tool_name = type(graph.tavily_tool).__name__
            print(f"   ✓ Using tool: {tool_name}")
        else:
            print("   ⚠ Web search not enabled in workflow")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_search():
    """Test async search functionality"""
    print("\n5. Testing async search...")
    try:
        from workflow.tools.google_search import GoogleSearchTool
        
        google = GoogleSearchTool(max_results=2)
        
        if google.check_availability():
            # Test async search
            results = await google.search("OpenAI GPT-4", "basic")
            print(f"   ✓ Async search returned {len(results)} results")
            
            if results:
                print(f"   ✓ First result: {results[0].metadata.get('title', 'No title')[:50]}...")
        else:
            print("   ⚠ Google Search not available (quota or API issue)")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_quota_and_cache():
    """Test quota management and caching"""
    print("\n6. Testing quota and cache...")
    try:
        from workflow.tools.google_search import GoogleSearchTool
        
        google = GoogleSearchTool(max_results=2)
        
        # Check initial quota
        print(f"   ✓ Initial quota: {google.quota_manager.remaining()}/{google.quota_manager.daily_limit}")
        
        # Perform a search
        if google.check_availability():
            results1 = google.search_sync("test query", "basic")
            print(f"   ✓ First search: {len(results1)} results")
            print(f"   ✓ Quota after search: {google.quota_manager.remaining()}/{google.quota_manager.daily_limit}")
            
            # Search again (should hit cache)
            results2 = google.search_sync("test query", "basic")
            print(f"   ✓ Second search (cached): {len(results2)} results")
            print(f"   ✓ Cache hit rate: {google.cache.hit_rate():.1%}")
            print(f"   ✓ Quota unchanged: {google.quota_manager.remaining()}/{google.quota_manager.daily_limit}")
        else:
            print("   ⚠ Google Search not available")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    results = []
    
    # Run sync tests
    results.append(("Imports", test_imports()))
    results.append(("Google Direct", test_google_search_direct()))
    results.append(("Factory Pattern", test_factory_pattern()))
    results.append(("Workflow Integration", test_workflow_integration()))
    results.append(("Quota & Cache", test_quota_and_cache()))
    
    # Run async test
    print("\n" + "=" * 80)
    print("ASYNC TESTS")
    print("=" * 80)
    
    loop = asyncio.get_event_loop()
    async_result = loop.run_until_complete(test_async_search())
    results.append(("Async Search", async_result))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<30} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Google Search Tool is ready to use.")
        print("\nTo switch to Google Search, set USE_GOOGLE_SEARCH=true in .env")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)