#!/usr/bin/env python3
"""
Hallucination Check Node Test
환각 체크 노드가 답변의 사실성을 올바르게 검증하는지 테스트
"""

import sys
import asyncio
from pathlib import Path
from langchain_core.documents import Document

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from workflow.nodes.hallucination import HallucinationCheckNode
from workflow.state import MVPWorkflowState


async def test_hallucination_check():
    """Hallucination Check 노드 테스트"""
    print("=" * 60)
    print("Hallucination Check Node Test")
    print("=" * 60)
    
    # 노드 생성
    node = HallucinationCheckNode()
    print("✅ Node created successfully\n")
    
    # 테스트용 문서
    test_documents = [
        Document(
            page_content="엔진 오일은 5W-30 또는 0W-30을 사용하세요. 교체 주기는 10,000km 또는 6개월입니다.",
            metadata={"source": "manual.pdf", "page": 45, "category": "paragraph"}
        ),
        Document(
            page_content="오일 용량은 4.5리터입니다. 드레인 플러그는 오일 팬 하단에 위치합니다.",
            metadata={"source": "manual.pdf", "page": 46, "category": "paragraph"}
        )
    ]
    
    # 테스트 케이스 1: 사실적인 답변 (통과해야 함)
    print("\n" + "="*40)
    print("Test Case 1: Grounded Answer (Should Pass)")
    print("="*40)
    
    grounded_answer = """
    엔진 오일 교체 시 5W-30 또는 0W-30 오일을 사용하세요. 
    오일 용량은 4.5리터이며, 교체 주기는 10,000km 또는 6개월입니다.
    드레인 플러그는 오일 팬 하단에 있습니다.
    """
    
    state_1 = {
        "query": "엔진 오일 교체 정보",
        "final_answer": grounded_answer,
        "documents": test_documents,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print("🔍 Checking grounded answer...")
        result_1 = await node(state_1)
        
        # 결과 검증
        assert "hallucination_check" in result_1, "hallucination_check field missing"
        
        check_result = result_1["hallucination_check"]
        print(f"\n✅ Check Result:")
        print(f"  - Is valid: {check_result.get('is_valid', False)}")
        print(f"  - Score: {check_result.get('score', 0.0):.3f}")
        print(f"  - Needs retry: {check_result.get('needs_retry', False)}")
        
        if check_result.get('is_valid'):
            print("  ✅ Answer is grounded (no hallucination)")
        else:
            print("  ⚠️  Hallucination detected")
            print(f"  - Reason: {check_result.get('reason', 'N/A')}")
            if check_result.get('suggestions'):
                print(f"  - Problematic claims: {check_result['suggestions']}")
        
        # 메타데이터 확인
        if "metadata" in result_1 and "hallucination_check" in result_1["metadata"]:
            hall_meta = result_1["metadata"]["hallucination_check"]
            print(f"\n📊 Hallucination Metadata:")
            print(f"  - Hallucination score: {hall_meta.get('hallucination_score', 0.0):.3f}")
            print(f"  - Is grounded: {hall_meta.get('is_grounded', False)}")
            print(f"  - Supported claims: {len(hall_meta.get('supported_claims', []))}")
            print(f"  - Problematic claims: {len(hall_meta.get('problematic_claims', []))}")
        
    except Exception as e:
        print(f"❌ Test Case 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 2: 환각이 포함된 답변 (실패해야 함)
    print("\n" + "="*40)
    print("Test Case 2: Hallucinated Answer (Should Fail)")
    print("="*40)
    
    hallucinated_answer = """
    엔진 오일은 5W-30을 사용하세요. 오일 용량은 6리터입니다.
    교체 주기는 5,000km마다이며, 특수 첨가제를 반드시 넣어야 합니다.
    오일 필터는 매 2회마다 교체하면 됩니다.
    """
    
    state_2 = {
        "query": "엔진 오일 교체 정보",
        "final_answer": hallucinated_answer,
        "documents": test_documents,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print("🔍 Checking hallucinated answer...")
        result_2 = await node(state_2)
        
        check_result = result_2["hallucination_check"]
        print(f"\n✅ Check Result:")
        print(f"  - Is valid: {check_result.get('is_valid', False)}")
        print(f"  - Score: {check_result.get('score', 0.0):.3f}")
        print(f"  - Needs retry: {check_result.get('needs_retry', False)}")
        
        if not check_result.get('is_valid'):
            print("  ✅ Hallucination correctly detected")
            print(f"  - Reason: {check_result.get('reason', 'N/A')[:200]}...")
            if check_result.get('suggestions'):
                print(f"\n  Problematic claims:")
                for claim in check_result['suggestions'][:3]:
                    print(f"    • {claim}")
        else:
            print("  ⚠️  Failed to detect hallucination")
        
    except Exception as e:
        print(f"❌ Test Case 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 3: 부분적 환각 (경계 케이스)
    print("\n" + "="*40)
    print("Test Case 3: Partial Hallucination (Edge Case)")
    print("="*40)
    
    partial_answer = """
    엔진 오일은 5W-30 또는 0W-30을 사용하세요.
    오일 용량은 약 4-5리터입니다.
    정기적인 교체가 중요합니다.
    """
    
    state_3 = {
        "query": "엔진 오일 교체 정보",
        "final_answer": partial_answer,
        "documents": test_documents,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print("🔍 Checking partially grounded answer...")
        result_3 = await node(state_3)
        
        check_result = result_3["hallucination_check"]
        print(f"\n✅ Check Result:")
        print(f"  - Is valid: {check_result.get('is_valid', False)}")
        print(f"  - Score: {check_result.get('score', 0.0):.3f}")
        print(f"  - Analysis: Partial information, mostly grounded")
        
    except Exception as e:
        print(f"❌ Test Case 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 4: 빈 문서 처리 (에러 케이스)
    print("\n" + "="*40)
    print("Test Case 4: Empty Documents (Error Case)")
    print("="*40)
    
    state_4 = {
        "query": "엔진 오일 교체 정보",
        "final_answer": "Test answer",
        "documents": [],  # 빈 문서
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print("⚠️  Testing with empty documents...")
        result_4 = await node(state_4)
        
        if result_4.get("error"):
            print(f"✅ Error correctly caught: {result_4['error']}")
        
    except ValueError as e:
        print(f"✅ ValueError correctly raised: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n" + "="*60)
    print("Hallucination Check Test Completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_hallucination_check())