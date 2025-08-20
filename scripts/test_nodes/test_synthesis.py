#!/usr/bin/env python3
"""
Synthesis Node Test
답변 생성 노드가 문서를 기반으로 답변을 올바르게 생성하는지 테스트
"""

import sys
import asyncio
from pathlib import Path
from langchain_core.documents import Document

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from workflow.nodes.synthesis import SynthesisNode
from workflow.state import MVPWorkflowState


async def test_synthesis():
    """Synthesis 노드 테스트"""
    print("=" * 60)
    print("Synthesis Node Test")
    print("=" * 60)
    
    # 노드 생성
    node = SynthesisNode()
    print("✅ Node created successfully\n")
    
    # 테스트용 문서 생성
    test_documents = [
        Document(
            page_content="엔진 오일을 교체하려면 먼저 차량을 평평한 곳에 주차하고 엔진을 끄세요. 엔진이 완전히 식을 때까지 기다린 후 작업을 시작하세요.",
            metadata={"source": "manual.pdf", "page": 45, "category": "paragraph"}
        ),
        Document(
            page_content="1. 오일 드레인 플러그를 찾아 렌치로 풀어주세요. 2. 기존 오일을 완전히 배출시킵니다. 3. 새 오일 필터를 장착합니다. 4. 권장 오일을 규정량만큼 주입합니다.",
            metadata={"source": "manual.pdf", "page": 46, "category": "list"}
        ),
        Document(
            page_content="권장 엔진 오일: 5W-30 또는 0W-30 (기후에 따라 선택). 오일 용량: 4.5리터",
            metadata={"source": "manual.pdf", "page": 47, "category": "paragraph"}
        )
    ]
    
    # 테스트 케이스 1: 기본 답변 생성
    print("\n" + "="*40)
    print("Test Case 1: Basic Answer Generation")
    print("="*40)
    
    state_1 = {
        "query": "엔진 오일 교체 방법",
        "documents": test_documents,
        "subtasks": [],
        "current_subtask_idx": 0,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print(f"📄 Generating answer from {len(test_documents)} documents...")
        result_1 = await node(state_1)
        
        # 결과 검증
        assert "final_answer" in result_1 or "intermediate_answer" in result_1, "No answer generated"
        assert "confidence_score" in result_1, "confidence_score field missing"
        
        answer = result_1.get("final_answer") or result_1.get("intermediate_answer")
        print(f"\n✅ Answer generated (length: {len(answer)} chars)")
        print(f"\n📝 Answer preview:")
        print("-" * 40)
        print(answer[:500] + "..." if len(answer) > 500 else answer)
        print("-" * 40)
        
        # 신뢰도 점수
        confidence = result_1.get("confidence_score", 0.0)
        print(f"\n📊 Confidence score: {confidence:.3f}")
        
        # 메타데이터 확인
        if "metadata" in result_1 and "synthesis" in result_1["metadata"]:
            synthesis_meta = result_1["metadata"]["synthesis"]
            print(f"\n📈 Synthesis Metadata:")
            print(f"  - Documents used: {synthesis_meta.get('documents_used', 0)}")
            print(f"  - Sources: {synthesis_meta.get('sources', [])}")
            print(f"  - Key points: {len(synthesis_meta.get('key_points', []))}")
        
    except Exception as e:
        print(f"❌ Test Case 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 2: 서브태스크 답변 생성
    print("\n" + "="*40)
    print("Test Case 2: Subtask Answer Generation")
    print("="*40)
    
    test_subtask = {
        "id": "test123",
        "query": "엔진 오일 종류",
        "status": "retrieved",
        "documents": test_documents
    }
    
    state_2 = {
        "query": "엔진 오일 교체 방법과 종류",
        "documents": test_documents,
        "subtasks": [test_subtask],
        "current_subtask_idx": 0,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print(f"📄 Generating answer for subtask: '{test_subtask['query']}'")
        result_2 = await node(state_2)
        
        # intermediate_answer 확인
        if "intermediate_answer" in result_2:
            answer = result_2["intermediate_answer"]
            print(f"\n✅ Intermediate answer generated (length: {len(answer)} chars)")
            print(f"\n📝 Answer preview:")
            print("-" * 40)
            print(answer[:300] + "..." if len(answer) > 300 else answer)
            print("-" * 40)
        
        # 서브태스크 업데이트 확인
        if "subtasks" in result_2:
            updated_subtask = result_2["subtasks"][0]
            print(f"\n📊 Subtask Update:")
            print(f"  - Status: {updated_subtask.get('status', 'N/A')}")
            print(f"  - Has answer: {updated_subtask.get('answer') is not None}")
        
    except Exception as e:
        print(f"❌ Test Case 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 3: 빈 문서 처리 (에러 케이스)
    print("\n" + "="*40)
    print("Test Case 3: Empty Documents (Error Case)")
    print("="*40)
    
    state_3 = {
        "query": "엔진 오일 교체 방법",
        "documents": [],  # 빈 문서 리스트
        "subtasks": [],
        "current_subtask_idx": 0,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print(f"⚠️  Testing with empty documents...")
        result_3 = await node(state_3)
        
        # 에러 처리 확인
        if result_3.get("error"):
            print(f"✅ Error correctly caught: {result_3['error']}")
        else:
            print(f"⚠️  No error raised for empty documents")
        
    except ValueError as e:
        print(f"✅ ValueError correctly raised: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 4: 긴 문서 처리 (토큰 제한 테스트)
    print("\n" + "="*40)
    print("Test Case 4: Long Documents (Token Limit Test)")
    print("="*40)
    
    # 매우 긴 문서 생성
    long_documents = [
        Document(
            page_content="엔진 오일 교체 관련 내용... " * 500,  # 매우 긴 내용
            metadata={"source": "manual.pdf", "page": i, "category": "paragraph"}
        )
        for i in range(10)
    ]
    
    state_4 = {
        "query": "엔진 오일 교체 방법",
        "documents": long_documents,
        "subtasks": [],
        "current_subtask_idx": 0,
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print(f"📄 Testing with {len(long_documents)} long documents...")
        result_4 = await node(state_4)
        
        if "final_answer" in result_4:
            print(f"✅ Successfully handled long documents with fallback")
            print(f"  Answer length: {len(result_4['final_answer'])} chars")
        
    except Exception as e:
        print(f"❌ Test Case 4 failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Synthesis Node Test Completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_synthesis())