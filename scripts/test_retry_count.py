#!/usr/bin/env python3
"""
retry_count 증가 메커니즘 테스트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from workflow.nodes.synthesis import SynthesisNode
from langchain_core.documents import Document

async def test_retry_count():
    """retry_count 증가 테스트"""
    
    synthesis = SynthesisNode()
    
    # 테스트 문서
    documents = [
        Document(
            page_content="엔진 오일은 정기적으로 교체해야 합니다.",
            metadata={"source": "manual.pdf", "page": 45}
        )
    ]
    
    print("\n=== Test 1: 첫 번째 시도 (retry_count = 0) ===")
    state1 = {
        "query": "엔진 오일 교체 방법",
        "documents": documents,
        "retry_count": 0,
        "metadata": {}
    }
    
    result1 = await synthesis(state1)
    print(f"Result retry_count: {result1.get('retry_count', 'NOT FOUND')}")
    print(f"Expected: 0")
    
    print("\n=== Test 2: 품질 재시도 (needs_retry = True) ===")
    state2 = {
        "query": "엔진 오일 교체 방법",
        "documents": documents,
        "retry_count": 0,
        "answer_grade": {
            "is_valid": False,
            "score": 0.45,
            "needs_retry": True,
            "suggestions": ["Add step-by-step procedure"]
        },
        "metadata": {
            "answer_grade": {
                "missing_aspects": ["Tools needed", "Time required"],
                "strengths": ["Clear language"]
            }
        }
    }
    
    result2 = await synthesis(state2)
    print(f"Result retry_count: {result2.get('retry_count', 'NOT FOUND')}")
    print(f"Expected: 1 (증가되어야 함)")
    
    print("\n=== Test 3: 두 번째 재시도 (retry_count = 1) ===")
    state3 = {
        "query": "엔진 오일 교체 방법",
        "documents": documents,
        "retry_count": 1,  # 이미 1회 재시도됨
        "answer_grade": {
            "is_valid": False,
            "score": 0.55,
            "needs_retry": True,
            "suggestions": ["Still missing details"]
        },
        "metadata": {
            "answer_grade": {
                "missing_aspects": ["Safety warnings"],
                "strengths": ["Better structure"]
            }
        }
    }
    
    result3 = await synthesis(state3)
    print(f"Result retry_count: {result3.get('retry_count', 'NOT FOUND')}")
    print(f"Expected: 2 (증가되어야 함)")
    
    print("\n=== Test 4: 환각 재시도 ===")
    state4 = {
        "query": "엔진 오일 교체 방법",
        "documents": documents,
        "retry_count": 0,
        "hallucination_check": {
            "is_valid": False,
            "score": 0.3,
            "needs_retry": True,
            "suggestions": ["Remove unsupported claims"]
        },
        "metadata": {
            "hallucination_check": {
                "problematic_claims": ["오일 용량 4.5L"],
                "supported_claims": ["정기적 교체 필요"]
            }
        }
    }
    
    result4 = await synthesis(state4)
    print(f"Result retry_count: {result4.get('retry_count', 'NOT FOUND')}")
    print(f"Expected: 1 (증가되어야 함)")
    
    print("\n=== 테스트 완료 ===")
    return all([
        result1.get('retry_count') == 0,
        result2.get('retry_count') == 1,
        result3.get('retry_count') == 2,
        result4.get('retry_count') == 1
    ])

if __name__ == "__main__":
    success = asyncio.run(test_retry_count())
    if success:
        print("\n✅ 모든 테스트 통과!")
    else:
        print("\n❌ 일부 테스트 실패!")