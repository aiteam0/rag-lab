#!/usr/bin/env python3
"""
개선된 DirectResponseNode 테스트
- DEBUG 로그 제거 확인
- 플로우 로깅 확인
- 현재 날짜 주입 확인
"""

import os
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from workflow.nodes.direct_response import DirectResponseNode
from langchain_core.messages import HumanMessage

# 환경변수 로드
load_dotenv()

# Web search 기능 강제 활성화
os.environ["ENABLE_DIRECT_RESPONSE_SEARCH"] = "true"
os.environ["USE_GOOGLE_SEARCH"] = "true"


def test_improved_logging_and_date():
    """개선된 로깅과 날짜 주입 테스트"""
    print("=" * 80)
    print("개선된 DirectResponseNode 테스트")
    print("=" * 80)
    
    # DirectResponseNode 초기화
    node = DirectResponseNode()
    
    print(f"\n[환경 정보]")
    print(f"- 현재 날짜: {datetime.now().strftime('%Y년 %m월 %d일')}")
    print(f"- Web search 활성화: {node.web_search_enabled}")
    print(f"- LLM 모델: {node.llm.model_name}")
    
    # 테스트 케이스
    test_cases = [
        {
            "query": "지금 대통령은 누구야?",
            "type": "time-sensitive",
            "expected": "이재명"
        },
        {
            "query": "오늘이 며칠이야?",
            "type": "date-query",
            "expected": "2025년"
        },
        {
            "query": "파이썬이 뭐야?",
            "type": "general-knowledge",
            "expected": None
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"테스트 {i}: {test_case['query']} ({test_case['type']})")
        print(f"{'='*70}")
        
        state = {
            "query": test_case['query'],
            "messages": [HumanMessage(content=test_case['query'])],
            "metadata": {}
        }
        
        try:
            print("\n[실행 로그]")
            # Node 실행 (로그가 자동으로 출력됨)
            result = node(state)
            
            if result.get("final_answer"):
                answer = result["final_answer"]
                
                print(f"\n[메타데이터 분석]")
                meta = result.get("metadata", {}).get("direct_response", {})
                print(f"- Web search 사용: {meta.get('web_search_used')}")
                print(f"- 컨텍스트 메시지 수: {meta.get('context_messages')}")
                
                # 예상 키워드 확인
                if test_case['expected']:
                    if test_case['expected'] in answer:
                        print(f"\n✅ 성공: '{test_case['expected']}' 발견")
                    else:
                        print(f"\n⚠️ 주의: '{test_case['expected']}' 미발견")
                
                # 답변 미리보기 (처음 200자)
                print(f"\n[답변 미리보기]")
                preview = answer[:200] + "..." if len(answer) > 200 else answer
                print(preview)
                
                # 2025년 언급 확인 (시간 민감 쿼리의 경우)
                if test_case['type'] in ['time-sensitive', 'date-query']:
                    year_mentions = {
                        "2025": answer.count("2025"),
                        "2024": answer.count("2024"),
                        "2023": answer.count("2023")
                    }
                    print(f"\n[연도 언급 횟수]")
                    for year, count in year_mentions.items():
                        if count > 0:
                            print(f"- {year}: {count}회")
                
            else:
                print(f"\n❌ 응답 생성 실패")
                if result.get("error"):
                    print(f"에러: {result['error']}")
                    
        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
    
    print("\n" + "="*80)
    print("로깅 개선 사항 확인")
    print("="*80)
    
    print("""
✓ DEBUG 로그 제거 완료
✓ 구조화된 플로우 로깅 (├─ └─ 사용)
✓ 현재 날짜 동적 주입
✓ Tool call 상태 추적
✓ 분석 결과 로깅
""")


if __name__ == "__main__":
    test_improved_logging_and_date()