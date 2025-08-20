#!/usr/bin/env python3
"""
Test script for AnswerGraderNode - isolated testing
Tests the node with various inputs to verify it works correctly
"""

import sys
import asyncio
from pathlib import Path
from langchain_core.documents import Document

# Add project path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.answer_grader import AnswerGraderNode
from workflow.state import MVPWorkflowState


async def test_answer_grader_node():
    """Test answer grader node with various scenarios"""
    print("=" * 60)
    print("Answer Grader Node Test")
    print("=" * 60)
    
    # Create node instance
    node = AnswerGraderNode()
    print("\n✅ Node created successfully")
    
    # Test Case 1: Good quality answer
    print("\n" + "=" * 40)
    print("Test 1: Good quality answer")
    print("=" * 40)
    
    test_state_1 = {
        "query": "엔진 오일 교체 방법",
        "final_answer": "엔진 오일을 교체하려면 다음 단계를 따르십시오:\n1. 차량을 평평한 곳에 주차하고 엔진을 식힙니다.\n2. 오일 드레인 플러그를 열어 기존 오일을 배출합니다.\n3. 새 오일 필터를 장착합니다.\n4. 권장 오일(5W-30)을 규정량만큼 주입합니다.\n이 작업은 약 30분이 소요됩니다.",
        "documents": [
            Document(
                page_content="엔진 오일 교체: 차량을 평평한 곳에 주차하고 엔진을 식힙니다. 오일 드레인 플러그를 열어 오일을 배출합니다.",
                metadata={"source": "manual.pdf", "page": 45, "category": "paragraph"}
            )
        ],
        "confidence_score": 0.85,
        "metadata": {}
    }
    
    try:
        result_1 = await node(test_state_1)
        print(f"✅ Test 1 passed")
        print(f"   - answer_grade: {result_1.get('answer_grade', {})}")
        print(f"   - warnings type: {type(result_1.get('warnings'))}")
        print(f"   - warnings value: {result_1.get('warnings')}")
        
        # Critical check: warnings must be a list or None (but should be list for Annotated[List, add])
        if result_1.get('warnings') is not None and not isinstance(result_1.get('warnings'), list):
            raise ValueError(f"CRITICAL: warnings is not a list! Type: {type(result_1.get('warnings'))}")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 2: Low quality answer
    print("\n" + "=" * 40)
    print("Test 2: Low quality answer")
    print("=" * 40)
    
    test_state_2 = {
        "query": "엔진 오일 교체 방법",
        "final_answer": "오일을 교체하세요.",  # Too brief
        "documents": [
            Document(
                page_content="엔진 오일 교체 상세 절차...",
                metadata={"source": "manual.pdf", "page": 45, "category": "paragraph"}
            )
        ],
        "confidence_score": 0.3,
        "metadata": {}
    }
    
    try:
        result_2 = await node(test_state_2)
        print(f"✅ Test 2 passed")
        print(f"   - answer_grade: {result_2.get('answer_grade', {})}")
        print(f"   - warnings type: {type(result_2.get('warnings'))}")
        print(f"   - warnings value: {result_2.get('warnings')}")
        
        # Should have warnings for low quality
        if result_2.get('warnings') is not None:
            if not isinstance(result_2.get('warnings'), list):
                raise ValueError(f"CRITICAL: warnings is not a list! Type: {type(result_2.get('warnings'))}")
            print(f"   ⚠️  Warnings detected (expected): {result_2.get('warnings')}")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 3: No answer available
    print("\n" + "=" * 40)
    print("Test 3: No answer available")
    print("=" * 40)
    
    test_state_3 = {
        "query": "엔진 오일 교체 방법",
        "documents": [
            Document(
                page_content="Test document",
                metadata={"source": "manual.pdf", "page": 1, "category": "paragraph"}
            )
        ],
        "metadata": {}
        # No final_answer or intermediate_answer
    }
    
    try:
        result_3 = await node(test_state_3)
        print(f"✅ Test 3 passed")
        print(f"   - answer_grade: {result_3.get('answer_grade', {})}")
        print(f"   - warnings type: {type(result_3.get('warnings'))}")
        print(f"   - warnings value: {result_3.get('warnings')}")
        
        if result_3.get('warnings') is not None and not isinstance(result_3.get('warnings'), list):
            raise ValueError(f"CRITICAL: warnings is not a list! Type: {type(result_3.get('warnings'))}")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 4: Documents is None (invalid state)
    print("\n" + "=" * 40)
    print("Test 4: Documents is None (invalid state)")
    print("=" * 40)
    
    test_state_4 = {
        "query": "엔진 오일 교체 방법",
        "final_answer": "Test answer",
        "documents": None,  # This is invalid!
        "confidence_score": 0.5,
        "metadata": {}
    }
    
    try:
        result_4 = await node(test_state_4)
        # If we reach here, the node didn't validate properly
        print(f"⚠️  Test 4: Node returned result even with None documents")
        print(f"   This indicates weak validation - should have raised an error!")
        print(f"   Result: {result_4}")
    except Exception as e:
        print(f"✅ Test 4: Correctly handled None documents")
        print(f"   Error (expected): {e}")
    
    # Test Case 5: Empty answer (should fail quality check)
    print("\n" + "=" * 40)
    print("Test 5: Empty answer")
    print("=" * 40)
    
    test_state_5 = {
        "query": "엔진 오일 교체 방법",
        "final_answer": "",  # Empty answer
        "documents": [
            Document(
                page_content="엔진 오일 교체 절차...",
                metadata={"source": "manual.pdf", "page": 45, "category": "paragraph"}
            )
        ],
        "confidence_score": 0.0,
        "metadata": {}
    }
    
    try:
        result_5 = await node(test_state_5)
        print(f"✅ Test 5 passed")
        print(f"   - answer_grade: {result_5.get('answer_grade', {})}")
        print(f"   - should have low score for empty answer")
        print(f"   - warnings type: {type(result_5.get('warnings'))}")
        print(f"   - warnings value: {result_5.get('warnings')}")
        
        if result_5.get('warnings') is not None and not isinstance(result_5.get('warnings'), list):
            raise ValueError(f"CRITICAL: warnings is not a list! Type: {type(result_5.get('warnings'))}")
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("✅ All tests completed")
    print("\nKey findings:")
    print("1. Check if warnings field is always a list (never None)")
    print("2. Check if node handles missing inputs gracefully")
    print("3. Check if node validates None values properly")
    print("4. Check quality scoring for various answer types")


if __name__ == "__main__":
    asyncio.run(test_answer_grader_node())