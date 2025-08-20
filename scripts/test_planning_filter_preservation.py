#!/usr/bin/env python3
"""
Test PlanningAgent filter hint preservation
Verify if enhanced prompt preserves table/image/page hints in subtasks
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.planning_agent import PlanningAgentNode


async def test_filter_hint_preservation():
    """필터 힌트 보존 테스트"""
    print("="*70)
    print("PLANNING AGENT FILTER HINT PRESERVATION TEST")
    print("="*70)
    
    # PlanningAgent 노드 생성
    planning_agent = PlanningAgentNode()
    
    # 테스트 쿼리들 (기존에 실패했던 케이스들)
    test_queries = [
        {
            "query": "표로 정리된 엔진 오일 사양",
            "expected_hints": ["표", "테이블"],
            "description": "Table hint preservation"
        },
        {
            "query": "그림으로 설명된 전자식 파킹 브레이크",
            "expected_hints": ["그림", "이미지"],
            "description": "Image hint preservation"
        },
        {
            "query": "6페이지의 안전벨트 착용 방법",
            "expected_hints": ["6페이지", "페이지"],
            "description": "Page hint preservation"
        },
        {
            "query": "도표로 나타낸 연비 비교",
            "expected_hints": ["도표", "표"],
            "description": "Chart hint preservation"
        },
        {
            "query": "사진으로 보는 브레이크 구조",
            "expected_hints": ["사진", "이미지"],
            "description": "Photo hint preservation"
        }
    ]
    
    results = []
    
    for test_case in test_queries:
        query = test_case["query"]
        expected_hints = test_case["expected_hints"]
        description = test_case["description"]
        
        print(f"\n📝 Testing: '{query}'")
        print(f"   Expected hints: {expected_hints}")
        print("-" * 50)
        
        try:
            # 가상의 state 생성
            state = {"query": query}
            
            # Planning 실행
            result = await planning_agent(state)
            
            # 서브태스크 확인
            subtasks = result.get("subtasks", [])
            print(f"   Generated {len(subtasks)} subtasks:")
            
            hints_preserved = []
            for i, subtask in enumerate(subtasks):
                subtask_query = subtask.get("query", "")
                print(f"     {i+1}. {subtask_query}")
                
                # 힌트 보존 확인
                preserved = []
                for hint in expected_hints:
                    if hint in subtask_query or any(synonym in subtask_query for synonym in get_hint_synonyms(hint)):
                        preserved.append(hint)
                
                if preserved:
                    hints_preserved.extend(preserved)
            
            # 결과 평가
            success = len(hints_preserved) > 0
            unique_hints = list(set(hints_preserved))
            
            if success:
                print(f"   ✅ SUCCESS: Preserved hints: {unique_hints}")
            else:
                print(f"   ❌ FAILED: No hints preserved")
            
            results.append({
                "query": query,
                "description": description,
                "expected": expected_hints,
                "preserved": unique_hints,
                "success": success,
                "subtasks": [s.get("query", "") for s in subtasks]
            })
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({
                "query": query,
                "description": description,
                "success": False,
                "error": str(e)
            })
    
    # 결과 요약
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    for result in results:
        status = "✅" if result.get("success", False) else "❌"
        print(f"{status} {result['description']}: {result['query']}")
        if result.get("preserved"):
            print(f"    Preserved: {result['preserved']}")
        if result.get("error"):
            print(f"    Error: {result['error']}")
    
    print(f"\nSuccess Rate: {successful}/{total} ({successful/total*100:.0f}%)")
    
    # 상세 분석
    if successful > 0:
        print(f"\n📊 Detailed Analysis:")
        for result in results:
            if result.get("success") and result.get("subtasks"):
                print(f"\n✅ {result['query']}:")
                for i, subtask in enumerate(result["subtasks"]):
                    print(f"   → {subtask}")


def get_hint_synonyms(hint):
    """힌트 동의어 반환"""
    synonyms = {
        "표": ["테이블", "표 형태", "표에 나온"],
        "테이블": ["표", "표 형태", "테이블 형태"],
        "그림": ["이미지", "그림으로", "그림/이미지"],
        "이미지": ["그림", "사진", "이미지로"],
        "사진": ["이미지", "그림", "사진으로"],
        "도표": ["차트", "표", "도표로"],
        "페이지": ["페이지에", "페이지의"]
    }
    return synonyms.get(hint, [])


if __name__ == "__main__":
    asyncio.run(test_filter_hint_preservation())