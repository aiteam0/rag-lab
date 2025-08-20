#!/usr/bin/env python3
"""
Test cases for source extraction logic
These should be tested after implementing the fixes
"""

test_cases = [
    {
        "id": 1,
        "query": "GV80 엔진 오일 교체 주기",
        "expected": {
            "source_mentioned": None,
            "reasoning": "차량 모델만 언급, 문서 언급 없음"
        }
    },
    {
        "id": 2,
        "query": "GV80 매뉴얼에서 오일 교체 방법",
        "expected": {
            "source_mentioned": "manual",
            "reasoning": "매뉴얼 명시적 언급"
        }
    },
    {
        "id": 3,
        "query": "사용 설명서 50페이지의 안전 기능",
        "expected": {
            "source_mentioned": "user guide",
            "page_numbers": [50],
            "reasoning": "설명서와 페이지 명시"
        }
    },
    {
        "id": 4,
        "query": "Genesis G90 브레이크 시스템",
        "expected": {
            "source_mentioned": None,
            "reasoning": "차량 모델만, 문서 없음"
        }
    },
    {
        "id": 5,
        "query": "owner's manual에 나온 타이어 압력",
        "expected": {
            "source_mentioned": "owner's manual",
            "reasoning": "owner's manual 명시"
        }
    },
    {
        "id": 6,
        "query": "엔진 오일 권장 사양",
        "expected": {
            "source_mentioned": None,
            "reasoning": "일반 쿼리, 문서 언급 없음"
        }
    },
    {
        "id": 7,
        "query": "GV70 핸드북 35페이지",
        "expected": {
            "source_mentioned": "handbook",
            "page_numbers": [35],
            "reasoning": "핸드북과 페이지 명시"
        }
    },
    {
        "id": 8,
        "query": "안전벨트 착용 방법",
        "expected": {
            "source_mentioned": None,
            "reasoning": "일반 쿼리, 문서 없음"
        }
    }
]

def print_test_cases():
    """Print test cases for manual verification"""
    print("=" * 70)
    print("SOURCE EXTRACTION TEST CASES")
    print("=" * 70)
    print("\nThese cases should be tested after implementing the fixes:\n")
    
    for case in test_cases:
        print(f"Test {case['id']}:")
        print(f"  Query: \"{case['query']}\"")
        print(f"  Expected source: {case['expected']['source_mentioned']}")
        if 'page_numbers' in case['expected']:
            print(f"  Expected pages: {case['expected']['page_numbers']}")
        print(f"  Reasoning: {case['expected']['reasoning']}")
        print()
    
    print("=" * 70)
    print("KEY PRINCIPLES:")
    print("=" * 70)
    print("✅ Extract source ONLY when document is explicitly mentioned")
    print("✅ Vehicle models (GV80, G90, etc.) are NOT sources")
    print("✅ Document indicators: 매뉴얼, manual, guide, 설명서, 문서, handbook")
    print("❌ Don't extract source from vehicle model alone")
    print("=" * 70)

if __name__ == "__main__":
    print_test_cases()