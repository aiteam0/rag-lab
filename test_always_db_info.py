#!/usr/bin/env python3
"""
Test: DB Info Always Included
모든 응답에 DB 정보가 포함되는지 테스트
"""

import sys
from pathlib import Path
from datetime import datetime
from langchain_core.messages import HumanMessage

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from workflow.graph import MVPWorkflowGraph
from dotenv import load_dotenv

load_dotenv()

# 색상 코드
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# 다양한 쿼리 테스트
TEST_QUERIES = [
    "안녕하세요",
    "오늘 날씨 어때?",
    "2 + 2는 뭐야?",
    "자동차 수명은 얼마나 되나요?",
    "What's your name?",
    "How are you?",
]

def check_db_info_in_response(response: str) -> bool:
    """응답에 DB 정보가 포함되어 있는지 확인"""
    db_keywords = [
        "280", "문서", "document", 
        "파일", "file", "소스", "source",
        "디지털정부혁신", "gv80", "GV80",
        "158", "122", "청크", "chunk",
        "데이터", "data", "시스템", "system"
    ]
    
    response_lower = response.lower()
    found_keywords = [kw for kw in db_keywords if kw.lower() in response_lower]
    
    if found_keywords:
        print(f"{GREEN}  ✓ DB info found: {', '.join(found_keywords[:3])}{RESET}")
        return True
    else:
        print(f"{RED}  ✗ No DB info found in response{RESET}")
        return False

def test_query(graph, query: str, test_num: int):
    """단일 쿼리 테스트"""
    print(f"\n{BLUE}Test {test_num}: {query}{RESET}")
    print("-" * 60)
    
    try:
        # 워크플로우 실행
        result = graph.app.invoke(
            {"query": query, "messages": [HumanMessage(content=query)]},
            config={"configurable": {"thread_id": f"test_{test_num}"}}
        )
        
        final_answer = result.get("final_answer", "No answer")
        query_type = result.get("query_type", "unknown")
        
        print(f"  Query Type: {YELLOW}{query_type}{RESET}")
        print(f"  Response Preview: {final_answer[:150]}...")
        
        # DB 정보 포함 여부 확인
        has_db_info = check_db_info_in_response(final_answer)
        
        return has_db_info
        
    except Exception as e:
        print(f"{RED}  ✗ Error: {str(e)}{RESET}")
        return False

def main():
    """메인 테스트 실행"""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}   TEST: DB Info Always Included in Responses{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 워크플로우 그래프 초기화
    print(f"\n{YELLOW}Initializing workflow graph...{RESET}")
    graph = MVPWorkflowGraph()
    print(f"{GREEN}✓ Graph initialized{RESET}")
    
    # 각 쿼리 테스트
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        success = test_query(graph, query, i)
        results.append((query, success))
    
    # 결과 요약
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}                  TEST RESULTS{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for query, success in results:
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        query_short = query[:30] + "..." if len(query) > 30 else query
        print(f"  {status} {query_short:35} {'DB info included' if success else 'NO DB INFO'}")
    
    print(f"\n  Total: {passed}/{total} queries included DB info")
    
    if passed == total:
        print(f"\n{GREEN}✅ All responses include DB info!{RESET}")
        return 0
    else:
        print(f"\n{YELLOW}⚠️  Only {passed}/{total} responses include DB info{RESET}")
        print(f"{YELLOW}   Prompt modification needed to enforce DB info inclusion{RESET}")
        return 1

if __name__ == "__main__":
    exit(main())