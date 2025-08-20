#!/usr/bin/env python3
"""
Test script for Web Search Tool node
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.tools.tavily_search import TavilySearchTool


async def test_tavily_search():
    """Tavily 검색 도구 테스트"""
    print("=" * 60)
    print("Tavily Search Tool Test")
    print("=" * 60)
    
    try:
        # Tavily 도구 초기화
        print("\n1. Initializing Tavily tool...")
        try:
            tavily = TavilySearchTool(max_results=3)
            print("   ✅ Tavily tool initialized")
        except ValueError as e:
            print(f"   ❌ Tavily initialization failed: {e}")
            print("   Make sure TAVILY_API_KEY is set in .env file")
            return False
        
        # 테스트 쿼리들
        test_queries = [
            "엔진 오일 교체 방법",
            "how to change engine oil",
            "타이어 공기압 점검"
        ]
        
        for idx, query in enumerate(test_queries, 1):
            print(f"\n2.{idx} Testing query: '{query}'")
            
            # 검색 실행
            print(f"   Executing search...")
            results = await tavily.search(query)
            
            # 결과 검증
            print(f"   Type of results: {type(results)}")
            
            if results is None:
                print(f"   ❌ ERROR: search() returned None!")
                print(f"   This should not happen - search() should return empty list on error")
                return False
            
            if not isinstance(results, list):
                print(f"   ❌ ERROR: search() returned {type(results)}, expected list")
                return False
            
            print(f"   ✅ Returned valid list with {len(results)} documents")
            
            # 각 문서 검증
            for doc_idx, doc in enumerate(results[:2], 1):  # 처음 2개만 출력
                print(f"\n   Document {doc_idx}:")
                print(f"     - Type: {type(doc)}")
                print(f"     - Has page_content: {hasattr(doc, 'page_content')}")
                print(f"     - Has metadata: {hasattr(doc, 'metadata')}")
                if hasattr(doc, 'page_content'):
                    preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                    print(f"     - Content preview: {preview}")
                if hasattr(doc, 'metadata'):
                    print(f"     - Metadata keys: {list(doc.metadata.keys())}")
        
        # 에러 케이스 테스트
        print("\n3. Testing error cases...")
        
        # 빈 쿼리
        print("   Testing empty query...")
        empty_results = await tavily.search("")
        print(f"   Empty query results: {type(empty_results)}, length: {len(empty_results)}")
        
        if empty_results is None:
            print(f"   ❌ ERROR: Empty query returned None instead of empty list")
            return False
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    success = asyncio.run(test_tavily_search())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()