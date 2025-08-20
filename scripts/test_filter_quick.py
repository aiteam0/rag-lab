#!/usr/bin/env python3
"""
Quick test for Search Filter Generation
Tests only key scenarios to verify filter generation
"""

import sys
import logging
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph

# 로깅 설정 - INFO 레벨로 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_filter_generation(query):
    """단일 쿼리로 필터 생성 테스트"""
    print(f"\n{'='*60}")
    print(f"Testing: '{query}'")
    print('-'*60)
    
    try:
        workflow = MVPWorkflowGraph()
        result = workflow.run(query)
        
        # 에러 체크
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
            return False
        
        # 서브태스크에서 필터 정보 확인
        subtasks = result.get("subtasks", [])
        if subtasks:
            subtask = subtasks[0]
            
            # extracted_info 확인
            extracted_info = subtask.get("extracted_info", {})
            print(f"\n📋 Extracted Info:")
            for key, value in extracted_info.items():
                if value:
                    print(f"   - {key}: {value}")
            
            # 서브태스크의 search_filter 확인
            if "search_filter" in subtask:
                filter_dict = subtask["search_filter"]
                if filter_dict:
                    print(f"\n✅ Filter Generated:")
                    for key, value in filter_dict.items():
                        if value:
                            print(f"   - {key}: {value}")
                    return True
                else:
                    print(f"\n⚠️ No filter generated (None)")
        
        # 전역 search_filter 확인
        global_filter = result.get("search_filter")
        if global_filter:
            print(f"\n✅ Global Filter Generated:")
            for key, value in global_filter.items():
                if value:
                    print(f"   - {key}: {value}")
            return True
        else:
            print(f"\n⚠️ No global filter generated")
            
        return False
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("QUICK FILTER GENERATION TEST")
    print("="*70)
    
    # 핵심 테스트 케이스만
    test_queries = [
        # 페이지 필터가 생성되어야 하는 쿼리
        "6페이지의 안전벨트 착용 방법",
        
        # 테이블 카테고리 필터가 생성되어야 하는 쿼리
        "표로 정리된 엔진 오일 사양",
        
        # 이미지 관련 필터가 생성되어야 하는 쿼리
        "그림으로 설명된 전자식 파킹 브레이크",
        
        # 필터가 생성되지 않아야 하는 일반 쿼리
        "엔진 오일 교체 방법"
    ]
    
    results = []
    for query in test_queries:
        filter_generated = test_filter_generation(query)
        results.append((query, filter_generated))
    
    # 결과 요약
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for query, success in results:
        status = "✅ Filter Generated" if success else "⚠️ No Filter"
        print(f"{status}: {query}")
    
    # 통계
    total = len(results)
    filtered = sum(1 for _, success in results if success)
    print(f"\nFilter Generation Rate: {filtered}/{total} ({filtered/total*100:.0f}%)")
    
    # 분석
    print("\n📊 Analysis:")
    if filtered == 0:
        print("❌ No filters generated - SubtaskExecutor may be too conservative")
    elif filtered < total - 1:  # -1 because last query shouldn't generate filter
        print("⚠️ Some expected filters not generated - Check extraction logic")
    else:
        print("✅ Filter generation working as expected")


if __name__ == "__main__":
    main()