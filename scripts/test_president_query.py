#!/usr/bin/env python3
"""
대통령 관련 쿼리 테스트 - 검색 결과 상세 분석
"""

import os
import sys
import json

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from workflow.nodes.direct_response import DirectResponseNode
from workflow.tools.google_search import GoogleSearchTool
from langchain_core.messages import HumanMessage

# 환경변수 로드
load_dotenv()

# Web search 기능 강제 활성화
os.environ["ENABLE_DIRECT_RESPONSE_SEARCH"] = "true"
os.environ["USE_GOOGLE_SEARCH"] = "true"


def test_president_query_detailed():
    """대통령 쿼리 상세 테스트"""
    print("=" * 80)
    print("대통령 관련 쿼리 검색 결과 분석")
    print("=" * 80)
    
    # 1. 먼저 Google Search Tool 직접 테스트
    print("\n[1] Google Search Tool 직접 테스트")
    print("-" * 60)
    
    try:
        google_tool = GoogleSearchTool(max_results=5)
        
        # 다양한 검색어 테스트
        search_queries = [
            "한국 대통령",
            "대한민국 현재 대통령",
            "Korea president 2025",
            "현재 한국 대통령 누구"
        ]
        
        for query in search_queries:
            print(f"\n검색어: '{query}'")
            results = google_tool.search_sync(query, "detailed")
            
            print(f"검색 결과 수: {len(results)}")
            for i, doc in enumerate(results[:3], 1):
                print(f"\n  결과 {i}:")
                print(f"  - 제목: {doc.metadata.get('title', 'N/A')}")
                print(f"  - 소스: {doc.metadata.get('source', 'N/A')}")
                print(f"  - 내용 미리보기: {doc.page_content[:200]}...")
                
    except Exception as e:
        print(f"Google Search 에러: {e}")
    
    # 2. DirectResponseNode 테스트
    print("\n\n[2] DirectResponseNode 응답 테스트")
    print("-" * 60)
    
    node = DirectResponseNode()
    
    # 테스트 쿼리들
    test_queries = [
        "지금 대통령은 누구야?",
        "현재 한국 대통령이 누구야?",
        "대한민국 대통령 알려줘"
    ]
    
    for query in test_queries:
        print(f"\n쿼리: '{query}'")
        print("-" * 40)
        
        state = {
            "query": query,
            "messages": [HumanMessage(content=query)],
            "metadata": {}
        }
        
        try:
            # 노드 실행
            result = node(state)
            
            if result.get("final_answer"):
                answer = result["final_answer"]
                
                # 메타데이터 확인
                meta = result.get("metadata", {}).get("direct_response", {})
                print(f"Web search 사용: {meta.get('web_search_used', False)}")
                
                # 답변 분석
                print(f"\n[답변 내용]")
                print(answer[:500] + "..." if len(answer) > 500 else answer)
                
                # 대통령 이름 검색
                print(f"\n[언급된 이름 검색]")
                names_to_check = ["윤석열", "이재명", "문재인", "박근혜", "Yoon", "Lee"]
                for name in names_to_check:
                    if name in answer:
                        print(f"  ✓ '{name}' 발견")
                
        except Exception as e:
            print(f"에러: {e}")
            import traceback
            traceback.print_exc()


def test_direct_google_search():
    """Google API 직접 호출 테스트"""
    print("\n" + "=" * 80)
    print("[3] Google Custom Search API 직접 호출")
    print("=" * 80)
    
    try:
        from googleapiclient.discovery import build
        
        api_key = os.getenv("GOOGLE_API_KEY")
        search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        
        if not api_key or not search_engine_id:
            print("API 키 또는 Search Engine ID가 없습니다.")
            return
        
        service = build("customsearch", "v1", developerKey=api_key)
        
        # 직접 API 호출
        query = "현재 한국 대통령 2025"
        print(f"\n검색어: '{query}'")
        
        result = service.cse().list(
            q=query,
            cx=search_engine_id,
            num=5,
            hl="ko"  # 한국어 우선
        ).execute()
        
        items = result.get('items', [])
        print(f"검색 결과 수: {len(items)}")
        
        for i, item in enumerate(items, 1):
            print(f"\n결과 {i}:")
            print(f"  제목: {item.get('title')}")
            print(f"  링크: {item.get('link')}")
            print(f"  스니펫: {item.get('snippet', '')[:200]}")
            
    except Exception as e:
        print(f"API 직접 호출 에러: {e}")


if __name__ == "__main__":
    # 순차적 테스트 실행
    test_president_query_detailed()
    test_direct_google_search()
    
    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)