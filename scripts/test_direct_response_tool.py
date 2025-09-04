#!/usr/bin/env python3
"""
DirectResponseNode의 Web Search Tool 사용 테스트
Tool 정의 개선 후 동작 확인
"""

import os
import sys
import asyncio
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


def test_tool_parameter_fix():
    """Tool 파라미터 스키마 수정 테스트"""
    print("=" * 70)
    print("Direct Response Node - Tool Parameter Fix Test")
    print("=" * 70)
    
    # DirectResponseNode 초기화
    node = DirectResponseNode()
    
    # Web search 활성화 확인
    print(f"\n[INFO] Web search enabled: {node.web_search_enabled}")
    print(f"[INFO] Tool bound: {hasattr(node.llm_with_tools, 'kwargs') and 'tools' in getattr(node.llm_with_tools, 'kwargs', {})}")
    
    # 테스트 케이스들
    test_cases = [
        {
            "query": "지금 몇시야?",
            "expected": "현재 시간을 검색"
        },
        {
            "query": "오늘 날짜가 뭐야?",
            "expected": "오늘 날짜를 검색"
        },
        {
            "query": "최신 AI 뉴스 알려줘",
            "expected": "최신 AI 뉴스를 검색"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"테스트 {i}: {test_case['query']}")
        print(f"{'='*60}")
        
        # State 준비
        state = {
            "query": test_case["query"],
            "messages": [
                HumanMessage(content=test_case["query"])
            ],
            "metadata": {}
        }
        
        try:
            # Node 실행
            result = node(state)
            
            # 결과 확인
            if result.get("final_answer"):
                print(f"\n✅ 응답 생성 성공")
                print(f"응답 길이: {len(result['final_answer'])} 문자")
                
                # 메타데이터 확인
                if result.get("metadata", {}).get("direct_response", {}):
                    dr_meta = result["metadata"]["direct_response"]
                    print(f"\n[메타데이터]")
                    print(f"- Web search enabled: {dr_meta.get('web_search_enabled')}")
                    print(f"- Web search used: {dr_meta.get('web_search_used')}")
                    
                    if dr_meta.get('web_search_used'):
                        print("✨ Web search가 성공적으로 사용되었습니다!")
                
                # 응답 내용 일부 출력
                answer = result["final_answer"]
                print(f"\n[응답 미리보기]")
                print(answer[:300] + "..." if len(answer) > 300 else answer)
            else:
                print(f"\n❌ 응답 생성 실패")
                if result.get("error"):
                    print(f"에러: {result['error']}")
                    
        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("테스트 완료")
    print("="*70)


if __name__ == "__main__":
    test_tool_parameter_fix()