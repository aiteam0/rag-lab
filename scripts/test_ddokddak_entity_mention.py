#!/usr/bin/env python3
"""
똑딱이 Entity 언급 테스트
PPT 삽입 문서(똑딱이)가 답변에서 올바르게 언급되는지 테스트
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from workflow.graph import MVPWorkflowGraph
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_workflow(query: str) -> Dict[str, Any]:
    """
    워크플로우 실행
    
    Args:
        query: 테스트 쿼리
        
    Returns:
        워크플로우 실행 결과
    """
    # 워크플로우 그래프 생성
    workflow_graph = MVPWorkflowGraph()
    
    # 초기 상태 설정
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "subtasks": [],
        "current_subtask_idx": 0,
        "subtask_results": [],
        "query_variations": [],
        "documents": [],
        "search_filter": None,
        "search_language": "korean",
        "intermediate_answer": None,
        "final_answer": None,
        "hallucination_check": None,
        "answer_grade": None,
        "iteration_count": 0,
        "max_iterations": 5,
        "retry_count": 0,
        "should_use_web": False,
        "should_retry": False,
        "confidence_score": 0.0,
        "error": None,
        "warnings": [],
        "metadata": {},
        "execution_time": {},
        "next_node": None,
        "workflow_status": "running",
        "query_type": None,
        "enhanced_query": None,
        "current_node": None
    }
    
    # 워크플로우 실행
    try:
        result = workflow_graph.app.invoke(initial_state)
        return result
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        return None


def check_ddokddak_mention(answer: str) -> Dict[str, Any]:
    """
    답변에서 똑딱이 언급 여부 확인
    
    Args:
        answer: 생성된 답변
        
    Returns:
        체크 결과
    """
    # 관련 키워드
    keywords = {
        "똑딱이": 0,
        "PPT": 0,
        "삽입 문서": 0,
        "embedded": 0,
        "프레젠테이션": 0,
        "PPT 삽입 문서": 0,
        "SPECIAL": 0,
        "📌": 0
    }
    
    # 키워드 카운트
    for keyword in keywords:
        keywords[keyword] = answer.count(keyword)
    
    # 전체 언급 여부
    mentioned = sum(keywords.values()) > 0
    
    # 강조 표시 확인
    has_emphasis = keywords["SPECIAL"] > 0 or keywords["📌"] > 0
    
    return {
        "mentioned": mentioned,
        "has_emphasis": has_emphasis,
        "keyword_counts": keywords,
        "total_mentions": sum(keywords.values())
    }


def print_test_result(query: str, result: Dict[str, Any], check_result: Dict[str, Any]):
    """
    테스트 결과 출력
    """
    print("\n" + "="*80)
    print(f"🔍 Query: {query}")
    print("="*80)
    
    # 답변 출력
    final_answer = result.get("final_answer", "No answer")
    print("\n📝 Answer Preview (first 500 chars):")
    print("-"*40)
    print(final_answer[:500] + "..." if len(final_answer) > 500 else final_answer)
    
    # 똑딱이 언급 체크 결과
    print("\n✅ 똑딱이 Entity 언급 체크:")
    print("-"*40)
    print(f"  • 언급 여부: {'✓ Yes' if check_result['mentioned'] else '✗ No'}")
    print(f"  • 강조 표시: {'✓ Yes' if check_result['has_emphasis'] else '✗ No'}")
    print(f"  • 총 언급 횟수: {check_result['total_mentions']}")
    
    # 키워드별 카운트
    print("\n  • 키워드별 언급:")
    for keyword, count in check_result['keyword_counts'].items():
        if count > 0:
            print(f"    - {keyword}: {count}회")
    
    # 메타데이터 확인
    metadata = result.get("metadata", {})
    entity_check = metadata.get("entity_mention_check", {})
    if entity_check:
        print("\n📊 Entity Mention Check Metadata:")
        print(f"  • Has Special Entity: {entity_check.get('has_special_entity', False)}")
        print(f"  • Entity Mentioned: {entity_check.get('entity_mentioned', False)}")
        if entity_check.get('entity_titles'):
            print(f"  • Entity Titles: {', '.join(entity_check['entity_titles'])}")
    
    # Hallucination Check 결과
    hallucination_check = result.get("hallucination_check", {})
    if hallucination_check:
        print("\n🔍 Hallucination Check:")
        print(f"  • Score: {hallucination_check.get('score', 0):.2f}")
        print(f"  • Valid: {hallucination_check.get('is_valid', False)}")


def main():
    """
    메인 테스트 함수
    """
    print("\n" + "="*80)
    print("🧪 똑딱이 Entity 언급 테스트 시작")
    print("="*80)
    
    # 테스트 쿼리들
    test_queries = [
        "디지털 정부혁신 추진계획에 대해 알려줘",
        "디지털 정부혁신의 개요를 설명해줘",
        "디지털 정부혁신 추진계획 및 중장기 로드맵에 대해 설명해줘",
        "page 3에 있는 내용을 요약해줘"
    ]
    
    # 테스트 결과 저장
    test_results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📌 Test {i}/{len(test_queries)}: {query}")
        print("-"*40)
        
        try:
            # 워크플로우 실행
            result = run_workflow(query)
            
            if result and result.get("final_answer"):
                # 똑딱이 언급 체크
                check_result = check_ddokddak_mention(result["final_answer"])
                
                # 결과 출력
                print_test_result(query, result, check_result)
                
                # 결과 저장
                test_results.append({
                    "query": query,
                    "passed": check_result["mentioned"],
                    "check_result": check_result
                })
            else:
                print("  ❌ Failed to get answer")
                test_results.append({
                    "query": query,
                    "passed": False,
                    "check_result": None
                })
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            test_results.append({
                "query": query,
                "passed": False,
                "error": str(e)
            })
    
    # 최종 결과 요약
    print("\n" + "="*80)
    print("📊 테스트 결과 요약")
    print("="*80)
    
    passed = sum(1 for r in test_results if r["passed"])
    total = len(test_results)
    
    print(f"\n✅ 통과: {passed}/{total} ({passed/total*100:.1f}%)")
    
    for i, result in enumerate(test_results, 1):
        status = "✓" if result["passed"] else "✗"
        print(f"  {status} Test {i}: {result['query'][:50]}...")
        if result.get("check_result") and result["passed"]:
            print(f"     - 총 {result['check_result']['total_mentions']}회 언급")
    
    # 개선 제안
    if passed < total:
        print("\n💡 개선 제안:")
        print("  1. Synthesis 프롬프트에서 '똑딱이' 언급 강조 확인")
        print("  2. Document Formatter에서 강조 표시 확인")
        print("  3. 검색된 문서에 실제로 '똑딱이' entity가 있는지 확인")
    else:
        print("\n🎉 모든 테스트 통과! '똑딱이' entity 언급이 정상적으로 작동합니다.")


if __name__ == "__main__":
    main()