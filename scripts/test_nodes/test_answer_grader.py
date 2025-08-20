#!/usr/bin/env python3
"""
Answer Grader Node Test
답변 품질 평가 노드가 답변의 품질을 올바르게 평가하는지 테스트
"""

import sys
import asyncio
from pathlib import Path
from langchain_core.documents import Document

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from workflow.nodes.answer_grader import AnswerGraderNode
from workflow.state import MVPWorkflowState


async def test_answer_grader():
    """Answer Grader 노드 테스트"""
    print("=" * 60)
    print("Answer Grader Node Test")
    print("=" * 60)
    
    # 노드 생성
    node = AnswerGraderNode()
    print("✅ Node created successfully\n")
    
    # 테스트용 문서
    test_documents = [
        Document(
            page_content="엔진 오일 교체 절차: 1. 차량을 평평한 곳에 주차 2. 엔진을 끄고 식힘 3. 드레인 플러그 제거 4. 오일 배출 5. 새 필터 장착 6. 새 오일 주입",
            metadata={"source": "manual.pdf", "page": 45, "category": "list"}
        ),
        Document(
            page_content="권장 오일: 5W-30, 용량: 4.5리터, 교체 주기: 10,000km",
            metadata={"source": "manual.pdf", "page": 46, "category": "paragraph"}
        )
    ]
    
    # 테스트 케이스 1: 고품질 답변 (통과해야 함)
    print("\n" + "="*40)
    print("Test Case 1: High Quality Answer (Should Pass)")
    print("="*40)
    
    high_quality_answer = """
    엔진 오일 교체 방법:
    
    1. 준비 단계:
       - 차량을 평평한 곳에 주차합니다
       - 엔진을 끄고 충분히 식힙니다 (최소 10분)
    
    2. 오일 배출:
       - 드레인 플러그를 제거합니다
       - 기존 오일을 완전히 배출시킵니다
    
    3. 필터 교체:
       - 기존 오일 필터를 제거합니다
       - 새 필터를 장착합니다
    
    4. 새 오일 주입:
       - 권장 오일(5W-30)을 사용합니다
       - 규정 용량(4.5리터)만큼 주입합니다
    
    5. 교체 주기:
       - 10,000km마다 또는 6개월마다 교체하세요
    
    주의사항: 반드시 엔진이 식은 후 작업하시고, 폐오일은 적절히 처리하세요.
    """
    
    state_1 = {
        "query": "엔진 오일 교체 방법을 자세히 설명해주세요",
        "final_answer": high_quality_answer,
        "documents": test_documents,
        "confidence_score": 0.9,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print("📊 Grading high quality answer...")
        result_1 = await node(state_1)
        
        # 결과 검증
        assert "answer_grade" in result_1, "answer_grade field missing"
        
        grade_result = result_1["answer_grade"]
        print(f"\n✅ Grade Result:")
        print(f"  - Is valid: {grade_result.get('is_valid', False)}")
        print(f"  - Score: {grade_result.get('score', 0.0):.3f}")
        print(f"  - Needs retry: {grade_result.get('needs_retry', False)}")
        
        if grade_result.get('is_valid'):
            print("  ✅ Answer quality approved")
        else:
            print("  ⚠️  Answer quality insufficient")
        
        # 메타데이터 확인
        if "metadata" in result_1 and "answer_grade" in result_1["metadata"]:
            grade_meta = result_1["metadata"]["answer_grade"]
            print(f"\n📈 Quality Scores:")
            print(f"  - Overall: {grade_meta.get('overall_score', 0.0):.3f}")
            print(f"  - Completeness: {grade_meta.get('completeness', 0.0):.3f}")
            print(f"  - Relevance: {grade_meta.get('relevance', 0.0):.3f}")
            print(f"  - Clarity: {grade_meta.get('clarity', 0.0):.3f}")
            print(f"  - Usefulness: {grade_meta.get('usefulness', 0.0):.3f}")
            
            if grade_meta.get('strengths'):
                print(f"\n  💪 Strengths:")
                for strength in grade_meta['strengths'][:3]:
                    print(f"    • {strength}")
        
    except Exception as e:
        print(f"❌ Test Case 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 2: 저품질 답변 (실패해야 함)
    print("\n" + "="*40)
    print("Test Case 2: Low Quality Answer (Should Fail)")
    print("="*40)
    
    low_quality_answer = """
    오일을 교체하세요.
    """
    
    state_2 = {
        "query": "엔진 오일 교체 방법을 자세히 설명해주세요",
        "final_answer": low_quality_answer,
        "documents": test_documents,
        "confidence_score": 0.3,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print("📊 Grading low quality answer...")
        result_2 = await node(state_2)
        
        grade_result = result_2["answer_grade"]
        print(f"\n✅ Grade Result:")
        print(f"  - Is valid: {grade_result.get('is_valid', False)}")
        print(f"  - Score: {grade_result.get('score', 0.0):.3f}")
        print(f"  - Needs retry: {grade_result.get('needs_retry', False)}")
        
        if not grade_result.get('is_valid'):
            print("  ✅ Low quality correctly detected")
            print(f"  - Reason: {grade_result.get('reason', 'N/A')[:200]}...")
            
            if grade_result.get('suggestions'):
                print(f"\n  📝 Improvement suggestions:")
                for suggestion in grade_result['suggestions'][:3]:
                    print(f"    • {suggestion}")
        
        # 메타데이터에서 missing aspects 확인
        if "metadata" in result_2 and "answer_grade" in result_2["metadata"]:
            grade_meta = result_2["metadata"]["answer_grade"]
            if grade_meta.get('missing_aspects'):
                print(f"\n  ❌ Missing aspects:")
                for aspect in grade_meta['missing_aspects'][:3]:
                    print(f"    • {aspect}")
        
    except Exception as e:
        print(f"❌ Test Case 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 3: 중간 품질 답변 (경계 케이스)
    print("\n" + "="*40)
    print("Test Case 3: Medium Quality Answer (Edge Case)")
    print("="*40)
    
    medium_quality_answer = """
    엔진 오일을 교체하려면:
    1. 드레인 플러그를 열어 오일을 배출합니다
    2. 새 오일을 4.5리터 넣습니다
    3. 10,000km마다 교체하세요
    
    권장 오일은 5W-30입니다.
    """
    
    state_3 = {
        "query": "엔진 오일 교체 방법을 자세히 설명해주세요",
        "final_answer": medium_quality_answer,
        "documents": test_documents,
        "confidence_score": 0.6,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print("📊 Grading medium quality answer...")
        result_3 = await node(state_3)
        
        grade_result = result_3["answer_grade"]
        print(f"\n✅ Grade Result:")
        print(f"  - Is valid: {grade_result.get('is_valid', False)}")
        print(f"  - Score: {grade_result.get('score', 0.0):.3f}")
        print(f"  - Analysis: Acceptable but could be improved")
        
        # Threshold 확인
        if "metadata" in result_3 and "answer_grade" in result_3["metadata"]:
            threshold = result_3["metadata"]["answer_grade"].get('threshold', 0.6)
            score = grade_result.get('score', 0.0)
            print(f"\n  📏 Threshold comparison:")
            print(f"    Score: {score:.3f} {'≥' if score >= threshold else '<'} Threshold: {threshold}")
        
    except Exception as e:
        print(f"❌ Test Case 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 4: 답변 없음 (에러 케이스)
    print("\n" + "="*40)
    print("Test Case 4: No Answer (Error Case)")
    print("="*40)
    
    state_4 = {
        "query": "엔진 오일 교체 방법",
        # final_answer와 intermediate_answer 모두 없음
        "documents": test_documents,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print("⚠️  Testing with no answer...")
        result_4 = await node(state_4)
        
        grade_result = result_4.get("answer_grade", {})
        if not grade_result.get('is_valid'):
            print(f"✅ Correctly handled missing answer")
            print(f"  - Reason: {grade_result.get('reason', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n" + "="*60)
    print("Answer Grader Test Completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_answer_grader())