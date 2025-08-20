#!/usr/bin/env python3
"""
Retrieval Node Test
검색 노드가 문서를 올바르게 검색하고 상태를 업데이트하는지 테스트
"""

import sys
import asyncio
from pathlib import Path
from pprint import pprint
import uuid

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from workflow.nodes.retrieval import RetrievalNode
from workflow.state import MVPWorkflowState


async def test_retrieval():
    """Retrieval 노드 테스트"""
    print("=" * 60)
    print("Retrieval Node Test")
    print("=" * 60)
    
    # 노드 생성
    node = RetrievalNode()
    print("✅ Node created successfully\n")
    
    # 테스트 케이스 1: 기본 검색
    print("\n" + "="*40)
    print("Test Case 1: Basic Retrieval")
    print("="*40)
    
    # 테스트용 서브태스크
    test_subtask = {
        "id": str(uuid.uuid4())[:8],
        "query": "엔진 오일 교체 절차",
        "priority": 1,
        "status": "executing",
        "query_variations": [
            "엔진 오일 교체 절차",
            "How to change engine oil",
            "엔진 오일 교환 방법 및 순서",
            "모터 오일 드레인 및 리필 절차"
        ]
    }
    
    state_1 = {
        "query": "엔진 오일 교체 방법",
        "subtasks": [test_subtask],
        "current_subtask_idx": 0,
        "query_variations": test_subtask["query_variations"],
        "search_filter": None,
        "documents": [],
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print(f"🔍 Searching with {len(state_1['query_variations'])} query variations...")
        result_1 = await node(state_1)
        
        # 결과 검증
        assert "documents" in result_1, "documents field missing"
        assert "search_language" in result_1, "search_language field missing"
        assert "confidence_score" in result_1, "confidence_score field missing"
        
        documents = result_1.get("documents", [])
        print(f"\n✅ Retrieved {len(documents)} documents")
        
        # 언어 감지 결과
        language = result_1.get("search_language", "unknown")
        print(f"🌐 Detected language: {language}")
        
        # 신뢰도 점수
        confidence = result_1.get("confidence_score", 0.0)
        print(f"📊 Confidence score: {confidence:.3f}")
        
        # 상위 3개 문서 미리보기
        if documents:
            print(f"\n📄 Top {min(3, len(documents))} documents:")
            for i, doc in enumerate(documents[:3], 1):
                print(f"\n  Document {i}:")
                print(f"    - Source: {doc.metadata.get('source', 'Unknown')}")
                print(f"    - Page: {doc.metadata.get('page', 'N/A')}")
                print(f"    - Category: {doc.metadata.get('category', 'Unknown')}")
                print(f"    - Content preview: {doc.page_content[:100]}...")
                if doc.metadata.get('similarity'):
                    print(f"    - Similarity: {doc.metadata['similarity']:.3f}")
        
        # 서브태스크 상태 업데이트 확인
        if "subtasks" in result_1:
            updated_subtask = result_1["subtasks"][0]
            print(f"\n📊 Subtask Status Update:")
            print(f"  - Status: executing → {updated_subtask['status']}")
            print(f"  - Documents attached: {len(updated_subtask.get('documents', []))}")
        
        # 메타데이터 확인
        if "metadata" in result_1 and "retrieval" in result_1["metadata"]:
            retrieval_meta = result_1["metadata"]["retrieval"]
            print(f"\n📈 Retrieval Metadata:")
            print(f"  - Query variations used: {retrieval_meta.get('query_variations_count', 0)}")
            print(f"  - Total documents: {retrieval_meta.get('total_documents', 0)}")
            print(f"  - Unique documents: {retrieval_meta.get('unique_documents', 0)}")
            print(f"  - Search strategy: {retrieval_meta.get('search_strategy', 'N/A')}")
        
        # 실행 시간 확인
        if "execution_time" in result_1:
            exec_time = result_1["execution_time"].get("retrieval", 0)
            print(f"\n⏱️  Execution time: {exec_time:.3f}s")
        
    except Exception as e:
        print(f"❌ Test Case 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 2: 필터링된 검색
    print("\n" + "="*40)
    print("Test Case 2: Filtered Retrieval")
    print("="*40)
    
    state_2 = {
        "query": "엔진 오일 교체 방법",
        "subtasks": [test_subtask],
        "current_subtask_idx": 0,
        "query_variations": ["엔진 오일 교체"],
        "search_filter": {
            "categories": ["paragraph", "list"],
            "pages": None,
            "sources": None
        },
        "documents": [],
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print(f"🔍 Searching with filter: {state_2['search_filter']}")
        result_2 = await node(state_2)
        
        documents = result_2.get("documents", [])
        print(f"\n✅ Retrieved {len(documents)} filtered documents")
        
        # 필터 적용 확인
        if documents:
            categories = set(doc.metadata.get("category") for doc in documents[:5])
            print(f"📋 Document categories found: {categories}")
        
    except Exception as e:
        print(f"❌ Test Case 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 3: 빈 query_variations 처리 (에러 케이스)
    print("\n" + "="*40)
    print("Test Case 3: Empty Query Variations (Error Case)")
    print("="*40)
    
    state_3 = {
        "query": "엔진 오일 교체 방법",
        "subtasks": [test_subtask],
        "current_subtask_idx": 0,
        "query_variations": [],  # 빈 리스트
        "search_filter": None,
        "documents": [],
        "metadata": {},
        "workflow_status": "running"
    }
    
    try:
        print(f"⚠️  Testing with empty query_variations...")
        result_3 = await node(state_3)
        
        # 에러 처리 확인
        if result_3.get("error"):
            print(f"✅ Error correctly caught: {result_3['error']}")
        else:
            print(f"⚠️  No error raised for empty query_variations")
        
    except ValueError as e:
        print(f"✅ ValueError correctly raised: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Retrieval Node Test Completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_retrieval())