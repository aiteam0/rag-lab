#!/usr/bin/env python3
"""
Direct test of SubtaskExecutor filter generation
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.subtask_executor import SubtaskExecutorNode


async def test_filter_extraction():
    """SubtaskExecutor의 필터 추출 테스트"""
    print("="*60)
    print("Testing SubtaskExecutor Filter Generation")
    print("="*60)
    
    # SubtaskExecutor 노드 생성
    executor = SubtaskExecutorNode()
    
    # 테스트 쿼리들
    test_queries = [
        "6페이지의 안전벨트 착용 방법",
        "표로 정리된 엔진 오일 사양",
        "그림으로 설명된 파킹 브레이크",
        "엔진 오일 교체 방법"  # 필터 없음
    ]
    
    # 가상의 메타데이터 (실제 데이터베이스에서 오는 것)
    metadata = {
        "categories": ["heading1", "heading2", "heading3", "paragraph", "list", "table", "figure"],
        "entity_types": ["image", "table"]
    }
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        print("-"*40)
        
        try:
            # 1. 쿼리 정보 추출
            extraction = await executor._extract_query_info(query, metadata)
            print(f"Extracted Info:")
            print(f"  - Page numbers: {extraction.page_numbers}")
            print(f"  - Entity type: {extraction.entity_type}")
            print(f"  - Source mentioned: {extraction.source_mentioned}")
            print(f"  - Categories mentioned: {extraction.categories_mentioned}")
            print(f"  - Keywords: {extraction.keywords}")
            
            # 2. 필터 생성
            search_filter = await executor._generate_filter(query, extraction, metadata)
            
            if search_filter:
                filter_dict = search_filter.to_dict()
                print(f"\n✅ Filter Generated:")
                for key, value in filter_dict.items():
                    if value:
                        print(f"  - {key}: {value}")
            else:
                print(f"\n⚠️ No filter generated")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_filter_extraction())