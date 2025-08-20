#!/usr/bin/env python3
"""
Test filter generation in complete workflow
Focus on filter propagation through nodes
"""

import sys
import json
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph


def test_workflow_with_filter(query):
    """필터가 있는 쿼리로 워크플로우 테스트"""
    print(f"\n{'='*70}")
    print(f"Testing Workflow with Query: '{query}'")
    print('='*70)
    
    workflow = MVPWorkflowGraph()
    
    try:
        result = workflow.run(query)
        
        # 에러 체크
        if result.get("error"):
            print(f"❌ Workflow Error: {result['error']}")
            return
        
        # 서브태스크 분석
        subtasks = result.get("subtasks", [])
        if subtasks:
            print(f"\n📋 Subtasks: {len(subtasks)}")
            for i, subtask in enumerate(subtasks):
                print(f"\n  Subtask {i+1}:")
                print(f"    Query: {subtask.get('query', 'N/A')}")
                print(f"    Status: {subtask.get('status', 'N/A')}")
                
                # extracted_info 확인
                extracted_info = subtask.get("extracted_info", {})
                if extracted_info:
                    print(f"    Extracted Info:")
                    for key, value in extracted_info.items():
                        if value:
                            print(f"      - {key}: {value}")
                
                # search_filter 확인
                if "search_filter" in subtask:
                    filter_dict = subtask["search_filter"]
                    if filter_dict:
                        print(f"    ✅ Filter in Subtask:")
                        for key, value in filter_dict.items():
                            if value:
                                print(f"      - {key}: {value}")
        
        # 전역 search_filter 확인
        global_filter = result.get("search_filter")
        if global_filter:
            print(f"\n✅ Global Search Filter:")
            for key, value in global_filter.items():
                if value:
                    print(f"  - {key}: {value}")
        else:
            print(f"\n⚠️ No global search filter")
        
        # 메타데이터 확인
        metadata = result.get("metadata", {})
        
        # SubtaskExecutor 메타데이터
        executor_meta = metadata.get("subtask_executor", {})
        if executor_meta:
            print(f"\n📊 SubtaskExecutor Metadata:")
            filter_gen = executor_meta.get("filter_generated", False)
            print(f"  - Filter Generated: {filter_gen}")
            if "extracted_info" in executor_meta:
                print(f"  - Extracted Info Present: Yes")
        
        # Retrieval 메타데이터
        retrieval_meta = metadata.get("retrieval", {})
        if retrieval_meta:
            print(f"\n📊 Retrieval Metadata:")
            print(f"  - Total Documents: {retrieval_meta.get('total_documents', 0)}")
            print(f"  - Search Strategy: {retrieval_meta.get('search_strategy', 'N/A')}")
        
        # 문서 개수
        documents = result.get("documents", [])
        print(f"\n📄 Documents Retrieved: {len(documents)}")
        
        # 최종 답변 존재 여부
        if result.get("final_answer"):
            print(f"\n✅ Final Answer Generated: Yes")
        else:
            print(f"\n⚠️ Final Answer: Not generated")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 테스트"""
    print("\n" + "="*70)
    print("WORKFLOW FILTER PROPAGATION TEST")
    print("="*70)
    
    # 필터가 생성될 쿼리들
    test_queries = [
        "6페이지의 안전벨트 착용 방법",
        "표로 정리된 엔진 오일 사양",
        "그림으로 설명된 전자식 파킹 브레이크"
    ]
    
    print("\n🔍 Testing filter generation and propagation...")
    
    for query in test_queries:
        test_workflow_with_filter(query)
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    print("\n📝 Summary:")
    print("1. SubtaskExecutor extracts filter information from queries")
    print("2. Filters are generated for page numbers, categories, and entity types")
    print("3. Filters should be passed to Retrieval node for targeted search")


if __name__ == "__main__":
    main()