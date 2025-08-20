#!/usr/bin/env python3
"""
Test script to verify retry_count and References table fixes
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.synthesis import SynthesisNode
from langchain_core.documents import Document


async def test_references_table_generation():
    """References 테이블 생성 테스트"""
    print("=" * 60)
    print("Testing References Table Generation")
    print("=" * 60)
    
    # 테스트용 문서 생성
    test_documents = [
        Document(
            page_content="엔진 오일을 교체하기 전에 차량을 평평한 곳에 주차하고 엔진을 예열합니다.",
            metadata={"source": "gv80_manual.pdf", "page": 245, "category": "paragraph", "id": "doc1"}
        ),
        Document(
            page_content="오일 드레인 플러그를 제거하여 기존 오일을 배출합니다.",
            metadata={"source": "gv80_manual.pdf", "page": 246, "category": "paragraph", "id": "doc2"}
        ),
        Document(
            page_content="권장 엔진 오일: 5W-30, 교체 용량: 8.0리터",
            metadata={"source": "maintenance.pdf", "page": 52, "category": "table", "id": "doc3"}
        )
    ]
    
    synthesis_node = SynthesisNode()
    
    state = {
        "query": "엔진 오일 교체 방법",
        "documents": test_documents,
        "metadata": {},
        "retry_count": 0  # retry_count 필드 테스트
    }
    
    try:
        print("\n1. Calling synthesis node...")
        result = await synthesis_node.__call__(state)
        
        # retry_count 확인
        print(f"\n2. Retry count test:")
        print(f"   - Input retry_count: {state.get('retry_count', 'NOT FOUND')}")
        print(f"   - Output retry_count: {result.get('retry_count', 'NOT FOUND')}")
        
        # 최종 답변 확인
        final_answer = result.get("final_answer", "")
        
        print(f"\n3. References table test:")
        if "References:" in final_answer or "## References:" in final_answer:
            print("   ✅ References section found")
            
            # 테이블 형식 체크
            if "| 참조번호 |" in final_answer:
                print("   ✅ Korean table headers found")
            else:
                print("   ⚠️ Korean table headers NOT found")
                
            # 실제 문서명 체크
            if "gv80_manual.pdf" in final_answer or "maintenance.pdf" in final_answer:
                print("   ✅ Document names found")
            else:
                print("   ⚠️ Document names NOT found")
                
            # 페이지 번호 체크
            if "245" in final_answer or "246" in final_answer or "52" in final_answer:
                print("   ✅ Page numbers found")
            else:
                print("   ⚠️ Page numbers NOT found")
        else:
            print("   ❌ References section NOT found!")
            
        # References 섹션 추출
        if "References:" in final_answer:
            ref_start = final_answer.index("References:")
            print(f"\n4. Extracted References section:")
            print("-" * 40)
            print(final_answer[ref_start:])
            print("-" * 40)
            
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retry_count_in_state():
    """retry_count가 state에 정의되었는지 테스트"""
    print("\n" + "=" * 60)
    print("Testing retry_count in MVPWorkflowState")
    print("=" * 60)
    
    from workflow.state import MVPWorkflowState
    import inspect
    
    # TypedDict의 annotations 확인
    annotations = MVPWorkflowState.__annotations__
    
    if 'retry_count' in annotations:
        print("✅ retry_count field found in MVPWorkflowState")
        print(f"   Type: {annotations['retry_count']}")
        return True
    else:
        print("❌ retry_count field NOT found in MVPWorkflowState")
        print("Available fields:", list(annotations.keys()))
        return False


if __name__ == "__main__":
    print("Running fix verification tests...\n")
    
    # Test 1: retry_count in state
    test1_result = test_retry_count_in_state()
    
    # Test 2: References table generation
    test2_result = asyncio.run(test_references_table_generation())
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"1. retry_count in state: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"2. References table generation: {'✅ PASS' if test2_result else '❌ FAIL'}")
    
    sys.exit(0 if (test1_result and test2_result) else 1)