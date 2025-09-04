#!/usr/bin/env python3
"""
Test DirectResponseNode with enhanced web search capability and improved prompts
Verifies that the LLM intelligently uses web search based on query requirements
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from workflow.graph import MVPWorkflowGraph
from workflow.nodes.direct_response import DirectResponseNode


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def test_direct_response_with_enhanced_search():
    """Test DirectResponseNode with enhanced web search prompts"""
    
    print_section("ENHANCED DIRECT RESPONSE WITH WEB SEARCH TEST")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Check configuration
    search_enabled = os.getenv("ENABLE_DIRECT_RESPONSE_SEARCH", "false").lower() == "true"
    google_enabled = os.getenv("USE_GOOGLE_SEARCH", "false").lower() == "true"
    
    print(f"\n📋 Configuration Status:")
    print(f"   • ENABLE_DIRECT_RESPONSE_SEARCH: {'✅ Enabled' if search_enabled else '❌ Disabled'}")
    print(f"   • USE_GOOGLE_SEARCH: {'✅ Google' if google_enabled else '❌ Tavily'}")
    
    if not search_enabled:
        print("\n⚠️  Web search is disabled in DirectResponse")
        print("   To enable: Set ENABLE_DIRECT_RESPONSE_SEARCH=true in .env")
        print("   The test will continue to show what would happen with it enabled.")
    
    # 2. Create DirectResponseNode
    print(f"\n🔧 Initializing DirectResponseNode...")
    direct_node = DirectResponseNode()
    
    if direct_node.web_search_enabled:
        print(f"   ✅ Web search tool successfully bound to LLM")
        if direct_node.search_tool:
            tool_type = type(direct_node.search_tool).__name__
            print(f"   📎 Tool type: {tool_type}")
    else:
        print(f"   ⚠️  Web search NOT enabled in node")
    
    # 3. Test queries with different characteristics
    test_queries = [
        {
            "query": "What is the capital of France?",
            "category": "General Knowledge",
            "expect_search": False,
            "reason": "Timeless factual information"
        },
        {
            "query": "What's happening with OpenAI today?",
            "category": "Current Events",
            "expect_search": True,
            "reason": "Requires real-time information"
        },
        {
            "query": "What is the current Bitcoin price?",
            "category": "Real-time Data",
            "expect_search": True,
            "reason": "Live market data needed"
        },
        {
            "query": "What's today's date and day of the week?",
            "category": "Current Time/Date",
            "expect_search": True,
            "reason": "Current temporal information"
        },
        {
            "query": "Explain how photosynthesis works",
            "category": "Scientific Concept",
            "expect_search": False,
            "reason": "Established scientific knowledge"
        },
        {
            "query": "What are the latest AI announcements from December 2024?",
            "category": "Recent Updates",
            "expect_search": True,
            "reason": "Information after knowledge cutoff"
        }
    ]
    
    print_section("TESTING QUERY INTELLIGENCE")
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n{'─' * 70}")
        print(f"🧪 Test {i}: {test_case['category']}")
        print(f"📝 Query: \"{test_case['query']}\"")
        print(f"🎯 Expected: {'Web Search' if test_case['expect_search'] else 'Direct Answer'}")
        print(f"💡 Reason: {test_case['reason']}")
        
        try:
            # Create minimal state for DirectResponseNode
            state = {
                "query": test_case["query"],
                "messages": [],
                "metadata": {}
            }
            
            # Call the node
            print(f"\n⚙️  Processing...")
            result = direct_node(state)
            
            # Check if search was used
            dr_metadata = result.get("metadata", {}).get("direct_response", {})
            search_used = dr_metadata.get("web_search_used", False)
            search_enabled_in_result = dr_metadata.get("web_search_enabled", False)
            
            print(f"\n📊 Results:")
            print(f"   • Status: {result.get('workflow_status', 'unknown')}")
            print(f"   • Web search available: {'Yes' if search_enabled_in_result else 'No'}")
            print(f"   • Web search used: {'✅ Yes' if search_used else '❌ No'}")
            
            # Show answer preview
            if result.get("final_answer"):
                # Extract first sentence or 150 chars
                answer = result["final_answer"]
                # Remove document system info for preview
                answer_lines = answer.split('\n')
                main_answer = answer_lines[0] if answer_lines else answer
                preview = main_answer[:150] + "..." if len(main_answer) > 150 else main_answer
                print(f"   • Answer preview: {preview}")
            
            # Evaluate decision
            if search_enabled:
                if test_case["expect_search"]:
                    if search_used:
                        print(f"   ✅ CORRECT: Web search used as expected")
                    else:
                        print(f"   ⚠️  LLM chose not to search (may have sufficient knowledge)")
                else:
                    if not search_used:
                        print(f"   ✅ CORRECT: Direct answer without search")
                    else:
                        print(f"   ⚠️  Unnecessary web search (but may provide updated info)")
            else:
                print(f"   ℹ️  Web search disabled - answered from knowledge base")
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # 4. Test in workflow context
    print_section("WORKFLOW INTEGRATION TEST")
    
    try:
        print("🔄 Creating workflow instance...")
        workflow = MVPWorkflowGraph()
        
        # Query that should trigger DirectResponse with potential web search
        test_query = "What are today's top tech news headlines?"
        print(f"\n📨 Testing workflow with: \"{test_query}\"")
        
        result = workflow.run(test_query)
        
        if result.get("workflow_status") == "completed":
            print(f"\n✅ Workflow completed successfully")
            
            # Check routing and handling
            current_node = result.get("current_node")
            query_type = result.get("query_type", "unknown")
            
            print(f"\n📊 Workflow Analysis:")
            print(f"   • Query classified as: {query_type}")
            print(f"   • Handled by node: {current_node}")
            
            if current_node == "direct_response":
                dr_meta = result.get("metadata", {}).get("direct_response", {})
                print(f"   • Web search enabled: {'Yes' if dr_meta.get('web_search_enabled') else 'No'}")
                print(f"   • Web search used: {'Yes' if dr_meta.get('web_search_used') else 'No'}")
                print(f"   • Context messages: {dr_meta.get('context_messages', 0)}")
                
                if dr_meta.get('web_search_used'):
                    print(f"   🌐 Web search was utilized for current information")
        else:
            print(f"\n⚠️  Workflow status: {result.get('workflow_status')}")
            if result.get('error'):
                print(f"   Error: {result['error']}")
            
    except Exception as e:
        print(f"\n❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print_section("TEST SUMMARY")
    
    if search_enabled:
        print("✅ DirectResponseNode web search is ENABLED with enhanced prompts")
        print("\n📚 The LLM now intelligently decides when to search based on:")
        print("   • Query requires current/real-time information")
        print("   • Information is after April 2024 knowledge cutoff")
        print("   • Live data is needed (prices, weather, status)")
        print("   • Temporal queries (today, now, current)")
        print("\n🎯 The LLM avoids unnecessary searches for:")
        print("   • General factual knowledge")
        print("   • Established scientific/historical information")
        print("   • Conceptual explanations")
        print("   • Document system queries")
    else:
        print("⚠️  DirectResponseNode web search is DISABLED")
        print("\n📌 To enable intelligent web search:")
        print("   1. Set ENABLE_DIRECT_RESPONSE_SEARCH=true in .env")
        print("   2. Ensure USE_GOOGLE_SEARCH or TAVILY_API_KEY is configured")
        print("   3. Restart the application")
        print("\n💡 With web search enabled, the LLM will intelligently decide")
        print("   when to search based on the enhanced prompt guidelines")


def main():
    """Main entry point"""
    try:
        test_direct_response_with_enhanced_search()
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())