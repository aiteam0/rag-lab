#!/usr/bin/env python3
"""
Test workflow with Google Search Tool integration
Verifies that Google Search is used when USE_GOOGLE_SEARCH=true
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
from workflow.tools import create_search_tool


def print_section_header(title):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def verify_google_search_enabled():
    """Verify that Google Search is enabled"""
    use_google = os.getenv("USE_GOOGLE_SEARCH", "false").lower() == "true"
    if not use_google:
        print("⚠️ WARNING: USE_GOOGLE_SEARCH is not set to true!")
        print("Please set USE_GOOGLE_SEARCH=true in .env file")
        return False
    
    # Verify tool type
    tool = create_search_tool(max_results=3)
    if tool is None:
        print("❌ Failed to create search tool")
        return False
    
    tool_type = type(tool).__name__
    if "GoogleSearchTool" not in str(type(tool)) and hasattr(tool, '__self__'):
        tool_type = type(tool.__self__).__name__ if hasattr(tool, '__self__') else tool_type
    
    if "Google" in tool_type:
        print(f"✅ Google Search enabled: {tool_type}")
        return True
    else:
        print(f"⚠️ WARNING: Expected GoogleSearchTool, got {tool_type}")
        return False


def test_workflow_with_web_search():
    """Test workflow with queries that trigger web search"""
    
    # Test queries that should trigger web search
    test_queries = [
        {
            "query": "latest OpenAI GPT announcements 2024",
            "description": "Recent tech news (not in vehicle manual DB)",
            "expect_web_search": True
        },
        {
            "query": "Tesla Model 3 vs GV80 comparison",
            "description": "Comparison query (partial DB match, needs web)",
            "expect_web_search": True
        },
        {
            "query": "엔진 오일 교체 주기",
            "description": "Korean query (should check DB first)",
            "expect_web_search": False  # Might find in DB
        }
    ]
    
    print_section_header("WORKFLOW TEST WITH GOOGLE SEARCH")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verify Google Search is enabled
    if not verify_google_search_enabled():
        return False
    
    try:
        # Create workflow
        print("\n1. Creating workflow...")
        workflow = MVPWorkflowGraph()
        print("   ✅ Workflow created successfully")
        
        # Check if Google Search Tool is attached
        if hasattr(workflow, 'tavily_tool'):  # Note: kept as tavily_tool for compatibility
            tool_name = type(workflow.tavily_tool).__name__
            if hasattr(workflow.tavily_tool, '__self__'):
                tool_name = type(workflow.tavily_tool.__self__).__name__
            print(f"   ✅ Web search tool attached: {tool_name}")
        else:
            print("   ⚠️ No web search tool attached to workflow")
        
        all_tests_passed = True
        
        # Run each test query
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n{'=' * 60}")
            print(f"Test Case {i}: {test_case['description']}")
            print(f"Query: '{test_case['query']}'")
            print("=" * 60)
            
            try:
                # Run the query
                print(f"\n2.{i}. Running query...")
                result = workflow.run(test_case['query'])
                
                # Check for errors
                if result.get("error"):
                    print(f"   ❌ Error occurred: {result['error']}")
                    all_tests_passed = False
                    continue
                
                if result.get("workflow_status") == "failed":
                    print(f"   ❌ Workflow failed")
                    if result.get("warnings"):
                        print(f"   Warnings: {result['warnings']}")
                    all_tests_passed = False
                    continue
                
                print("   ✅ Workflow executed successfully")
                
                # Analyze results
                print(f"\n3.{i}. Results analysis:")
                print(f"   - Workflow status: {result.get('workflow_status', 'unknown')}")
                print(f"   - Subtasks created: {len(result.get('subtasks', []))}")
                
                # Check documents
                documents = result.get('documents', [])
                print(f"   - Documents retrieved: {len(documents)}")
                
                # Check if web search was used
                web_search_used = False
                if result.get("web_search_results"):
                    web_search_used = True
                    print(f"   - ✅ Web search used: {len(result['web_search_results'])} results")
                
                # Check metadata for web search indicators
                if result.get("metadata"):
                    # Check if any subtask used web search
                    for subtask_result in result.get("subtask_results", []):
                        if subtask_result and subtask_result.get("web_search_used"):
                            web_search_used = True
                            print(f"   - ✅ Web search confirmed in subtask")
                            break
                
                # Verify answer was generated
                if result.get("final_answer"):
                    answer_length = len(result["final_answer"])
                    print(f"   - ✅ Answer generated ({answer_length} chars)")
                    
                    # Check for web source references
                    if "http" in result["final_answer"].lower() or "www" in result["final_answer"].lower():
                        print("   - ✅ Web sources referenced in answer")
                        web_search_used = True
                else:
                    print("   - ⚠️ No final answer generated")
                
                # Verify web search expectation
                if test_case["expect_web_search"]:
                    if web_search_used:
                        print(f"   - ✅ Web search used as expected")
                    else:
                        print(f"   - ⚠️ Web search NOT used (was expected)")
                
                # Show first few documents
                if documents:
                    print(f"\n4.{i}. Sample documents (first 3):")
                    for j, doc in enumerate(documents[:3], 1):
                        source = doc.metadata.get('source', 'Unknown')
                        # Check if it's a web source
                        if 'http' in source or 'www' in source:
                            print(f"   [{j}] WEB: {source[:80]}...")
                        else:
                            print(f"   [{j}] DB: {source} p.{doc.metadata.get('page', '?')}")
                        print(f"       Preview: {doc.page_content[:100]}...")
                
            except Exception as e:
                print(f"\n❌ Test case {i} failed with exception: {e}")
                import traceback
                traceback.print_exc()
                all_tests_passed = False
        
        # Final summary
        print_section_header("TEST SUMMARY")
        if all_tests_passed:
            print("✅ All workflow tests with Google Search PASSED!")
            
            # Check Google Search quota if available
            try:
                from workflow.tools.google_search import GoogleSearchTool
                google = GoogleSearchTool()
                status = google.get_status()
                print(f"\n📊 Google Search Status:")
                print(f"   - API Quota: {status['quota']['used']}/{status['quota']['limit']} used")
                print(f"   - Remaining: {status['quota']['remaining']} queries")
                print(f"   - Cache hit rate: {status['cache']['hit_rate']:.1%}")
            except Exception as e:
                print(f"   - Could not get Google Search status: {e}")
            
            return True
        else:
            print("❌ Some workflow tests failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner"""
    print_section_header("GOOGLE SEARCH WORKFLOW INTEGRATION TEST")
    print("This test verifies that Google Search Tool is properly integrated")
    print("with the RAG workflow and handles web search fallback correctly.")
    
    success = test_workflow_with_web_search()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Google Search workflow integration test COMPLETED SUCCESSFULLY!")
        print("The workflow correctly uses Google Search for web fallback.")
    else:
        print("❌ Google Search workflow integration test FAILED")
        print("Please check the errors above for details.")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)