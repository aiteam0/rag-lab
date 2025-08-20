#!/usr/bin/env python3
"""
Test script for HallucinationCheckNode - isolated testing
Tests the node with various inputs to verify it works correctly
"""

import sys
import asyncio
from pathlib import Path
from langchain_core.documents import Document

# Add project path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.hallucination import HallucinationCheckNode
from workflow.state import MVPWorkflowState


async def test_hallucination_node():
    """Test hallucination node with various scenarios"""
    print("=" * 60)
    print("Hallucination Node Test")
    print("=" * 60)
    
    # Create node instance
    node = HallucinationCheckNode()
    print("\n✅ Node created successfully")
    
    # Test Case 1: Normal case with answer and documents
    print("\n" + "=" * 40)
    print("Test 1: Normal case with answer and documents")
    print("=" * 40)
    
    test_state_1 = {
        "query": "엔진 오일 교체 방법",
        "intermediate_answer": "엔진 오일을 교체하려면 먼저 차량을 평평한 곳에 주차하고 엔진을 식힌 후, 오일 드레인 플러그를 열어 오일을 배출합니다.",
        "documents": [
            Document(
                page_content="엔진 오일 교체: 차량을 평평한 곳에 주차하고 엔진을 식힙니다. 오일 드레인 플러그를 열어 오일을 배출합니다.",
                metadata={"source": "manual.pdf", "page": 45, "category": "paragraph"}
            ),
            Document(
                page_content="권장 오일: 5W-30 또는 0W-20 합성 오일을 사용하십시오.",
                metadata={"source": "manual.pdf", "page": 46, "category": "paragraph"}
            )
        ],
        "metadata": {}
    }
    
    try:
        result_1 = await node(test_state_1)
        print(f"✅ Test 1 passed")
        print(f"   - hallucination_check: {result_1.get('hallucination_check', {})}")
        print(f"   - should_retry: {result_1.get('should_retry', False)}")
        print(f"   - warnings type: {type(result_1.get('warnings'))}")
        print(f"   - warnings value: {result_1.get('warnings')}")
        
        # Critical check: warnings must be a list or None (but should be list for Annotated[List, add])
        if result_1.get('warnings') is not None and not isinstance(result_1.get('warnings'), list):
            raise ValueError(f"CRITICAL: warnings is not a list! Type: {type(result_1.get('warnings'))}")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 2: No answer available
    print("\n" + "=" * 40)
    print("Test 2: No answer available")
    print("=" * 40)
    
    test_state_2 = {
        "query": "엔진 오일 교체 방법",
        "documents": [
            Document(
                page_content="Test document",
                metadata={"source": "manual.pdf", "page": 1, "category": "paragraph"}
            )
        ],
        "metadata": {}
    }
    
    try:
        result_2 = await node(test_state_2)
        print(f"✅ Test 2 passed")
        print(f"   - hallucination_check: {result_2.get('hallucination_check', {})}")
        print(f"   - warnings type: {type(result_2.get('warnings'))}")
        print(f"   - warnings value: {result_2.get('warnings')}")
        
        if result_2.get('warnings') is not None and not isinstance(result_2.get('warnings'), list):
            raise ValueError(f"CRITICAL: warnings is not a list! Type: {type(result_2.get('warnings'))}")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 3: No documents available
    print("\n" + "=" * 40)
    print("Test 3: No documents available")
    print("=" * 40)
    
    test_state_3 = {
        "query": "엔진 오일 교체 방법",
        "intermediate_answer": "엔진 오일을 교체하려면...",
        "documents": [],  # Empty list
        "metadata": {}
    }
    
    try:
        result_3 = await node(test_state_3)
        print(f"✅ Test 3 passed")
        print(f"   - hallucination_check: {result_3.get('hallucination_check', {})}")
        print(f"   - should_retry: {result_3.get('should_retry', False)}")
        print(f"   - warnings type: {type(result_3.get('warnings'))}")
        print(f"   - warnings value: {result_3.get('warnings')}")
        
        if result_3.get('warnings') is not None and not isinstance(result_3.get('warnings'), list):
            raise ValueError(f"CRITICAL: warnings is not a list! Type: {type(result_3.get('warnings'))}")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 4: High hallucination score (should trigger warning)
    print("\n" + "=" * 40)
    print("Test 4: Answer with potential hallucination")
    print("=" * 40)
    
    test_state_4 = {
        "query": "엔진 오일 교체 방법",
        "intermediate_answer": "엔진 오일을 교체하려면 먼저 차량을 들어올리고, 특수 공구를 사용하여 엔진 블록을 분해한 후 내부를 청소합니다. 이 과정은 약 5시간이 소요됩니다.",
        "documents": [
            Document(
                page_content="엔진 오일 교체: 차량을 평평한 곳에 주차하고 오일 드레인 플러그를 열어 오일을 배출합니다. 약 30분 소요.",
                metadata={"source": "manual.pdf", "page": 45, "category": "paragraph"}
            )
        ],
        "metadata": {}
    }
    
    try:
        result_4 = await node(test_state_4)
        print(f"✅ Test 4 passed")
        print(f"   - hallucination_check: {result_4.get('hallucination_check', {})}")
        print(f"   - should_retry: {result_4.get('should_retry', False)}")
        print(f"   - warnings type: {type(result_4.get('warnings'))}")
        print(f"   - warnings value: {result_4.get('warnings')}")
        
        # This should have warnings (high hallucination score)
        if result_4.get('warnings') is not None:
            if not isinstance(result_4.get('warnings'), list):
                raise ValueError(f"CRITICAL: warnings is not a list! Type: {type(result_4.get('warnings'))}")
            print(f"   ⚠️  Warnings detected (expected): {result_4.get('warnings')}")
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 5: Documents is None (should fail with strong validation)
    print("\n" + "=" * 40)
    print("Test 5: Documents is None (invalid state)")
    print("=" * 40)
    
    test_state_5 = {
        "query": "엔진 오일 교체 방법",
        "intermediate_answer": "Test answer",
        "documents": None,  # This is invalid!
        "metadata": {}
    }
    
    try:
        result_5 = await node(test_state_5)
        # If we reach here, the node didn't validate properly
        print(f"⚠️  Test 5: Node returned result even with None documents")
        print(f"   This indicates weak validation - should have raised an error!")
        print(f"   Result: {result_5}")
    except Exception as e:
        print(f"✅ Test 5: Correctly handled None documents")
        print(f"   Error (expected): {e}")
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("✅ All tests completed")
    print("\nKey findings:")
    print("1. Check if warnings field is always a list (never None)")
    print("2. Check if node handles missing inputs gracefully")
    print("3. Check if node validates None values properly")


if __name__ == "__main__":
    asyncio.run(test_hallucination_node())