#!/usr/bin/env python3
"""
Advanced test for Search Filter Generation in SubtaskExecutor
Tests various query types that should trigger filter generation
"""

import sys
import logging
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class FilterTestScenario:
    """필터 테스트 시나리오"""
    def __init__(self, query, expected_filter_type, description):
        self.query = query
        self.expected_filter_type = expected_filter_type
        self.description = description


def analyze_filter_generation(result):
    """필터 생성 결과 분석"""
    # 상태에서 search_filter 확인
    search_filter = result.get("search_filter")
    
    if search_filter:
        print("      ✅ Filter generated:")
        for key, value in search_filter.items():
            if value:  # None이 아니고 빈 리스트가 아닌 경우만
                print(f"         - {key}: {value}")
        return True
    else:
        print("      ⚠️ No filter generated (None)")
        return False


def run_test_scenario(scenario: FilterTestScenario):
    """단일 테스트 시나리오 실행"""
    print(f"\n   📝 Test: {scenario.description}")
    print(f"      Query: '{scenario.query}'")
    print(f"      Expected: {scenario.expected_filter_type}")
    
    try:
        # 워크플로우 생성 및 실행
        workflow = MVPWorkflowGraph()
        result = workflow.run(scenario.query)
        
        # 에러 체크
        if result.get("error"):
            print(f"      ❌ Error: {result['error']}")
            return False
            
        # 필터 생성 분석
        filter_generated = analyze_filter_generation(result)
        
        # 서브태스크 정보 출력
        subtasks = result.get("subtasks", [])
        if subtasks:
            subtask = subtasks[0]
            extracted_info = subtask.get("extracted_info", {})
            if extracted_info:
                print("      📋 Extracted Info:")
                for key, value in extracted_info.items():
                    if value:
                        print(f"         - {key}: {value}")
        
        # 메타데이터 정보
        metadata = result.get("metadata", {})
        executor_meta = metadata.get("subtask_executor", {})
        if executor_meta:
            filter_status = executor_meta.get("filter_generated", False)
            print(f"      📊 Metadata - Filter Generated: {filter_status}")
        
        return filter_generated
        
    except Exception as e:
        print(f"      ❌ Exception: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("=" * 70)
    print("SEARCH FILTER GENERATION TEST")
    print("=" * 70)
    
    # 테스트 시나리오 정의
    test_scenarios = [
        # 페이지 관련 쿼리
        FilterTestScenario(
            "6페이지의 안전벨트 착용 방법을 알려주세요",
            "page filter",
            "Korean page number query"
        ),
        FilterTestScenario(
            "page 245의 엔진 오일 교체 절차",
            "page filter",
            "English page number query"
        ),
        FilterTestScenario(
            "50페이지부터 55페이지까지의 정비 주기",
            "page range filter",
            "Page range query"
        ),
        
        # 문서 타입 관련 쿼리
        FilterTestScenario(
            "표로 정리된 엔진 오일 사양을 보여주세요",
            "category filter (table)",
            "Table category query"
        ),
        FilterTestScenario(
            "그림으로 설명된 안전벨트 착용법",
            "category filter (figure)",
            "Figure category query"
        ),
        FilterTestScenario(
            "전자식 파킹 브레이크 관련 이미지",
            "entity filter (image)",
            "Image entity query"
        ),
        
        # 특정 문서명 관련 쿼리
        FilterTestScenario(
            "GV80 매뉴얼에서 브레이크 시스템 설명",
            "source filter",
            "Specific document source query"
        ),
        FilterTestScenario(
            "owner's manual의 안전 주의사항",
            "source filter",
            "Document name in English"
        ),
        
        # 복합 필터 쿼리
        FilterTestScenario(
            "245페이지의 표에서 오일 용량 확인",
            "page + category filter",
            "Complex filter with page and table"
        ),
        FilterTestScenario(
            "GV80 매뉴얼 6페이지의 그림",
            "source + page + category filter",
            "Multiple filter conditions"
        ),
        
        # 필터가 생성되지 않아야 하는 쿼리
        FilterTestScenario(
            "엔진 오일 교체 방법",
            "no filter",
            "General query without specific filters"
        ),
        FilterTestScenario(
            "안전벨트 착용의 중요성",
            "no filter",
            "Abstract query"
        )
    ]
    
    # 결과 통계
    total = len(test_scenarios)
    passed = 0
    failed = 0
    
    print(f"\n🧪 Running {total} test scenarios...")
    print("-" * 70)
    
    for scenario in test_scenarios:
        result = run_test_scenario(scenario)
        if result and scenario.expected_filter_type != "no filter":
            passed += 1
            print("      ✅ PASS: Filter generated as expected")
        elif not result and scenario.expected_filter_type == "no filter":
            passed += 1
            print("      ✅ PASS: No filter generated (as expected)")
        else:
            failed += 1
            print("      ❌ FAIL: Unexpected filter behavior")
    
    # 최종 결과 출력
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    
    # 성공률에 따른 평가
    success_rate = passed / total * 100
    print("\nOverall Assessment:")
    if success_rate >= 80:
        print("✅ EXCELLENT: Filter generation working well")
    elif success_rate >= 60:
        print("⚠️ GOOD: Filter generation mostly working")
    elif success_rate >= 40:
        print("⚠️ FAIR: Filter generation needs improvement")
    else:
        print("❌ POOR: Filter generation has significant issues")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)