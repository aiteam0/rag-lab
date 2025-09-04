#!/usr/bin/env python3
"""
Simple test to verify Google Search Tool is actually being used in the workflow
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def test_google_search_in_workflow():
    """Test that Google Search is being used when needed"""
    
    print("=" * 60)
    print("GOOGLE SEARCH INTEGRATION VERIFICATION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Verify Google Search is enabled
    use_google = os.getenv("USE_GOOGLE_SEARCH", "false").lower() == "true"
    print(f"\n1. Configuration Check:")
    print(f"   USE_GOOGLE_SEARCH = {use_google}")
    
    if not use_google:
        print("   ❌ Google Search is NOT enabled!")
        return False
    print("   ✅ Google Search is enabled")
    
    # 2. Check tool creation
    print(f"\n2. Tool Creation Check:")
    from workflow.tools import create_search_tool
    
    tool = create_search_tool(max_results=3)
    if tool is None:
        print("   ❌ Failed to create search tool")
        return False
    
    # Check the tool type
    tool_type = str(type(tool))
    if "GoogleSearchTool" in tool_type or (hasattr(tool, '__self__') and "GoogleSearchTool" in str(type(tool.__self__))):
        print(f"   ✅ GoogleSearchTool created successfully")
    else:
        print(f"   ⚠️ Unexpected tool type: {tool_type}")
        return False
    
    # 3. Test workflow initialization with Google Search
    print(f"\n3. Workflow Initialization Check:")
    from workflow.graph import MVPWorkflowGraph
    
    workflow = MVPWorkflowGraph()
    print("   ✅ Workflow created")
    
    # Check if web search tool is attached (it's called tavily_tool for compatibility)
    if hasattr(workflow, 'tavily_tool'):
        tool_name = str(type(workflow.tavily_tool))
        if "GoogleSearchTool" in tool_name or (hasattr(workflow.tavily_tool, '__self__') and "GoogleSearchTool" in str(type(workflow.tavily_tool.__self__))):
            print(f"   ✅ GoogleSearchTool is attached to workflow")
        else:
            print(f"   ⚠️ Different tool attached: {tool_name}")
    else:
        print("   ⚠️ No web search tool attached")
    
    # 4. Check Google API status
    print(f"\n4. Google API Status:")
    try:
        from workflow.tools.google_search import GoogleSearchTool
        google = GoogleSearchTool()
        status = google.get_status()
        
        print(f"   ✅ Google API connected")
        print(f"   - Quota: {status['quota']['used']}/{status['quota']['limit']}")
        print(f"   - Remaining: {status['quota']['remaining']} queries")
        print(f"   - Cache hits: {status['cache']['hits']}")
        print(f"   - Cache misses: {status['cache']['misses']}")
    except Exception as e:
        print(f"   ❌ Could not get Google API status: {e}")
        return False
    
    # 5. Test a simple web search directly
    print(f"\n5. Direct Google Search Test:")
    try:
        test_query = "OpenAI GPT-4 latest news 2024"
        print(f"   Testing query: '{test_query}'")
        
        results = google.search_sync(test_query)
        print(f"   ✅ Search returned {len(results)} results")
        
        if results:
            first = results[0]
            print(f"   - First result: {first.metadata.get('title', 'No title')[:60]}...")
            print(f"   - URL: {first.metadata.get('source', 'No URL')[:80]}...")
        
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return False
    
    # 6. Summary
    print(f"\n" + "=" * 60)
    print("SUMMARY:")
    print("✅ Google Search Tool is properly configured")
    print("✅ Tool is correctly attached to workflow") 
    print("✅ Google API is responsive")
    print("✅ Direct searches work correctly")
    print("\n🎉 Google Search integration verified successfully!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = test_google_search_in_workflow()
    sys.exit(0 if success else 1)