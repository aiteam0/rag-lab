#!/usr/bin/env python3
"""
Test script for Retrieval Node
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.retrieval import RetrievalNode
from workflow.state import MVPWorkflowState


async def test_retrieval_node():
    """Retrieval 노드 테스트"""
    print("=" * 60)
    print("Retrieval Node Test")
    print("=" * 60)
    
    try:
        # 노드 초기화
        print("\n1. Initializing Retrieval node...")
        retrieval_node = RetrievalNode()
        print("   ✅ Retrieval node initialized")
        
        # 테스트 케이스 1: 단순 쿼리
        print("\n2. Test Case 1: Simple query without subtasks")
        state1: MVPWorkflowState = {
            "query": "엔진 오일 교체 방법",
            "workflow_status": "started",
            "metadata": {},
            "retry_count": 0,
            "documents": [],
            "execution_time": {},
            "current_subtask_idx": 0,
            "subtasks": []
        }
        
        print("   Executing retrieval...")
        result1 = await retrieval_node(state1)
        
        print(f"   Result type: {type(result1)}")
        print(f"   Result keys: {result1.keys() if result1 else 'None'}")
        
        # 문서 검증
        if "documents" in result1:
            docs = result1["documents"]
            print(f"   Documents type: {type(docs)}")
            
            if docs is None:
                print(f"   ❌ ERROR: Retrieved documents is None!")
                return False
            
            if not isinstance(docs, list):
                print(f"   ❌ ERROR: Documents is not a list: {type(docs)}")
                return False
            
            print(f"   ✅ Retrieved {len(docs)} documents")
            
            # 처음 2개 문서 확인
            for idx, doc in enumerate(docs[:2], 1):
                print(f"\n   Document {idx}:")
                print(f"     - Type: {type(doc)}")
                if hasattr(doc, 'page_content'):
                    preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                    print(f"     - Content preview: {preview}")
                if hasattr(doc, 'metadata'):
                    print(f"     - Metadata keys: {list(doc.metadata.keys())}")
        else:
            print(f"   ⚠️  No 'documents' key in result")
        
        # 테스트 케이스 2: 서브태스크가 있는 경우
        print("\n3. Test Case 2: Query with subtasks")
        state2: MVPWorkflowState = {
            "query": "엔진 오일 교체 방법",
            "workflow_status": "started",
            "metadata": {},
            "retry_count": 0,
            "documents": [],
            "execution_time": {},
            "current_subtask_idx": 0,
            "subtasks": [
                {
                    "id": "subtask-001",
                    "query": "엔진 오일 드레인 플러그 위치",
                    "priority": 1,
                    "dependencies": [],
                    "search_language": "korean",
                    "status": "executing",
                    "query_variations": [
                        "엔진 오일 드레인 플러그 위치",
                        "engine oil drain plug location",
                        "오일 배출 플러그 찾기"
                    ]
                }
            ],
            "query_variations": [
                "엔진 오일 드레인 플러그 위치",
                "engine oil drain plug location",
                "오일 배출 플러그 찾기"
            ]
        }
        
        print("   Executing retrieval with subtask...")
        result2 = await retrieval_node(state2)
        
        print(f"   Result type: {type(result2)}")
        print(f"   Result keys: {result2.keys() if result2 else 'None'}")
        
        # 서브태스크 검증
        if "subtasks" in result2:
            subtasks = result2["subtasks"]
            print(f"   Subtasks type: {type(subtasks)}")
            
            if subtasks and len(subtasks) > 0:
                subtask = subtasks[0]
                print(f"   Subtask status: {subtask.get('status')}")
                print(f"   Subtask has documents: {'documents' in subtask}")
                
                if "documents" in subtask:
                    subdocs = subtask["documents"]
                    print(f"   Subtask documents type: {type(subdocs)}")
                    
                    if subdocs is None:
                        print(f"   ❌ ERROR: Subtask documents is None!")
                        return False
                    
                    print(f"   ✅ Subtask has {len(subdocs)} documents")
        
        # 테스트 케이스 3: 필터가 있는 경우
        print("\n4. Test Case 3: Query with search filter")
        state3: MVPWorkflowState = {
            "query": "페이지 150의 정비 일정표",
            "workflow_status": "started",
            "metadata": {},
            "retry_count": 0,
            "documents": [],
            "execution_time": {},
            "current_subtask_idx": 0,
            "subtasks": [],
            "search_filter": {
                "pages": [150],
                "categories": ["table"]
            }
        }
        
        print("   Executing retrieval with filter...")
        result3 = await retrieval_node(state3)
        
        print(f"   Result type: {type(result3)}")
        
        if "documents" in result3:
            docs = result3["documents"]
            if docs is None:
                print(f"   ❌ ERROR: Filtered documents is None!")
                return False
            print(f"   ✅ Retrieved {len(docs)} filtered documents")
        
        print("\n✅ All retrieval node tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    success = asyncio.run(test_retrieval_node())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()