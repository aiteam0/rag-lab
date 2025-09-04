#!/usr/bin/env python3
"""
Chain of Thought 개선 후 대통령 쿼리 테스트
구조화된 분석과 CoT 프롬프트 검증
"""

import os
import sys
import json
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from workflow.nodes.direct_response import DirectResponseNode, SearchResultAnalysis
from workflow.tools.google_search import GoogleSearchTool
from langchain_core.messages import HumanMessage

# 환경변수 로드
load_dotenv()

# Web search 기능 강제 활성화
os.environ["ENABLE_DIRECT_RESPONSE_SEARCH"] = "true"
os.environ["USE_GOOGLE_SEARCH"] = "true"


def test_analysis_only():
    """검색 결과 분석 기능만 별도 테스트"""
    print("=" * 80)
    print("1. SearchResultAnalysis 기능 테스트")
    print("=" * 80)
    
    # Google Search Tool로 직접 검색
    google_tool = GoogleSearchTool(max_results=3)
    query = "현재 한국 대통령 2025"
    
    print(f"\n검색어: '{query}'")
    search_results = google_tool.search_sync(query, "basic")
    
    if search_results:
        print(f"검색 결과: {len(search_results)}개")
        
        # DirectResponseNode의 analyze_search_results 테스트
        node = DirectResponseNode()
        analysis = node.analyze_search_results(query, search_results)
        
        if analysis:
            print("\n[구조화된 분석 결과]")
            print(f"- 시간 민감 쿼리: {analysis.is_time_sensitive}")
            print(f"- 기본 지식 Override: {analysis.should_override_base_knowledge}")
            print(f"- 신뢰도: {analysis.confidence_level}")
            print(f"- 주요 답변: {analysis.primary_answer}")
            print(f"- 추론: {analysis.reasoning}")
            print(f"\n- 핵심 사실들:")
            for i, fact in enumerate(analysis.key_facts[:5], 1):
                print(f"  {i}. {fact}")
        else:
            print("❌ 분석 실패")
    else:
        print("❌ 검색 결과 없음")


def test_cot_president_query():
    """CoT 통합 대통령 쿼리 테스트"""
    print("\n" + "=" * 80)
    print("2. Chain of Thought 통합 테스트")
    print("=" * 80)
    
    node = DirectResponseNode()
    
    test_queries = [
        "지금 대통령은 누구야?",
        "현재 한국 대통령이 누구인지 알려줘",
        "대한민국 대통령 알려줘"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"쿼리: '{query}'")
        print(f"{'='*60}")
        
        state = {
            "query": query,
            "messages": [HumanMessage(content=query)],
            "metadata": {}
        }
        
        try:
            # Node 실행
            result = node(state)
            
            if result.get("final_answer"):
                answer = result["final_answer"]
                
                # 메타데이터 확인
                meta = result.get("metadata", {}).get("direct_response", {})
                print(f"\n[메타데이터]")
                print(f"- Web search 사용: {meta.get('web_search_used', False)}")
                
                # 답변 분석
                print(f"\n[답변 분석]")
                
                # 언급된 이름 확인
                names_to_check = {
                    "이재명": False,
                    "윤석열": False, 
                    "Lee Jae-myung": False,
                    "Yoon Suk-yeol": False,
                    "2025": False,
                    "2024": False,
                    "2022": False
                }
                
                for name in names_to_check:
                    if name in answer:
                        names_to_check[name] = True
                
                print("언급된 키워드:")
                for name, found in names_to_check.items():
                    if found:
                        print(f"  ✓ {name}")
                
                # 정답 판정
                if names_to_check["이재명"] or names_to_check["Lee Jae-myung"]:
                    print("\n✅ 정답! 이재명이 언급됨")
                elif names_to_check["윤석열"] or names_to_check["Yoon Suk-yeol"]:
                    print("\n❌ 오답! 윤석열이 언급됨 (2025년 현재는 이재명)")
                else:
                    print("\n⚠️ 불명확한 답변")
                
                # 답변 미리보기
                print(f"\n[답변 내용]")
                # 대통령 관련 부분만 추출
                lines = answer.split('\n')
                for line in lines:
                    if any(keyword in line for keyword in ["대통령", "이재명", "윤석열", "President", "Lee", "Yoon"]):
                        print(f"  > {line}")
                
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()


def analyze_search_behavior():
    """검색 동작 상세 분석"""
    print("\n" + "=" * 80)
    print("3. 검색 동작 상세 분석")
    print("=" * 80)
    
    # 로그 레벨 상세 설정
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
    
    node = DirectResponseNode()
    query = "지금 한국 대통령이 누구야?"
    
    print(f"\n테스트 쿼리: '{query}'")
    print(f"현재 날짜: {datetime.now().strftime('%Y년 %m월 %d일')}")
    print(f"LLM 지식 cutoff: 2024년 4월")
    
    state = {
        "query": query,
        "messages": [HumanMessage(content=query)],
        "metadata": {}
    }
    
    print("\n실행 중...")
    result = node(state)
    
    if result.get("final_answer"):
        answer = result["final_answer"]
        
        # CoT 추론 과정 확인
        print("\n[Chain of Thought 추론 확인]")
        cot_indicators = [
            "STEP 1", "STEP 2", "STEP 3", "STEP 4",
            "time-sensitive", "current information",
            "supersedes", "override", "search results"
        ]
        
        for indicator in cot_indicators:
            if indicator.lower() in answer.lower():
                print(f"  ✓ CoT 지표 발견: {indicator}")
        
        # 최종 판정
        print("\n[최종 판정]")
        if "이재명" in answer:
            print("✅ 성공! CoT 기반 추론이 올바르게 작동")
        else:
            print("❌ 실패! CoT 추론이 제대로 작동하지 않음")


if __name__ == "__main__":
    print("Chain of Thought 대통령 쿼리 통합 테스트")
    print("=" * 80)
    
    # 순차 실행
    test_analysis_only()
    test_cot_president_query()
    analyze_search_behavior()
    
    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)