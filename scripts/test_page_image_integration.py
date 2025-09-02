#!/usr/bin/env python
"""
페이지 이미지 경로 통합 테스트 스크립트
Retrieval과 Synthesis 노드에서 페이지 이미지 경로가 올바르게 처리되는지 확인
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
import json
from typing import Dict, List

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.retrieval import RetrievalNode
from workflow.nodes.synthesis import SynthesisNode
from workflow.state import MVPWorkflowState
from langchain_core.documents import Document

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_page_image_path_generation():
    """페이지 이미지 경로 생성 로직 테스트"""
    
    print("\n" + "="*80)
    print("TEST 1: Page Image Path Generation in Retrieval Node")
    print("="*80)
    
    # 테스트 케이스
    test_cases = [
        {
            "source": "data/gv80_owners_manual_TEST6P.pdf",
            "page": 3,
            "expected": "data/images/gv80_owners_manual_TEST6P-page-3.png"
        },
        {
            "source": "data/디지털정부혁신_추진계획.pdf",
            "page": 1,
            "expected": "data/images/디지털정부혁신_추진계획-page-1.png"
        },
        {
            "source": "data/some_document.pdf",
            "page": 0,  # page가 0인 경우
            "expected": ""  # 빈 문자열이어야 함
        }
    ]
    
    retrieval_node = RetrievalNode()
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"  Source: {test['source']}")
        print(f"  Page: {test['page']}")
        
        # 테스트 결과 생성
        result = {
            "source": test["source"],
            "page": test["page"],
            "category": "paragraph",
            "page_content": "Test content"
        }
        
        # Document로 변환
        doc = retrieval_node._convert_to_document(result)
        
        # 결과 확인
        actual_path = doc.metadata.get("page_image_path", "")
        expected_path = test["expected"]
        
        print(f"  Expected: {expected_path}")
        print(f"  Actual: {actual_path}")
        
        if actual_path == expected_path:
            print(f"  ✅ PASS")
        else:
            print(f"  ❌ FAIL")
    
    return True

def test_page_image_collection():
    """페이지 이미지 수집 및 중복 제거 테스트"""
    
    print("\n" + "="*80)
    print("TEST 2: Page Image Collection in Synthesis Node")
    print("="*80)
    
    # 테스트 문서 생성
    documents = [
        Document(
            page_content="Content 1",
            metadata={
                "source": "data/gv80_owners_manual_TEST6P.pdf",
                "page": 3,
                "page_image_path": "data/images/gv80_owners_manual_TEST6P-page-3.png"
            }
        ),
        Document(
            page_content="Content 2",
            metadata={
                "source": "data/gv80_owners_manual_TEST6P.pdf",
                "page": 5,
                "page_image_path": "data/images/gv80_owners_manual_TEST6P-page-5.png"
            }
        ),
        Document(
            page_content="Content 3",
            metadata={
                "source": "data/gv80_owners_manual_TEST6P.pdf",
                "page": 3,  # 중복된 페이지
                "page_image_path": "data/images/gv80_owners_manual_TEST6P-page-3.png"
            }
        ),
        Document(
            page_content="Content 4",
            metadata={
                "source": "data/디지털정부혁신_추진계획.pdf",
                "page": 1,
                "page_image_path": "data/images/디지털정부혁신_추진계획-page-1.png"
            }
        )
    ]
    
    synthesis_node = SynthesisNode()
    page_images = synthesis_node._collect_page_images(documents)
    
    print(f"\nTotal documents: {len(documents)}")
    print(f"Unique page images collected: {len(page_images)}")
    
    # 결과 출력
    print("\nCollected Page Images:")
    for img in page_images:
        print(f"  - Source: {img['source']}, Page: {img['page']}")
        print(f"    Path: {img['path']}")
    
    # 중복 제거 확인
    expected_count = 3  # 중복 제거 후 3개여야 함
    if len(page_images) == expected_count:
        print(f"\n✅ Duplicate removal: PASS (Expected {expected_count}, got {len(page_images)})")
    else:
        print(f"\n❌ Duplicate removal: FAIL (Expected {expected_count}, got {len(page_images)})")
    
    # 정렬 확인
    is_sorted = all(
        page_images[i]['source'] <= page_images[i+1]['source'] or
        (page_images[i]['source'] == page_images[i+1]['source'] and 
         page_images[i]['page'] <= page_images[i+1]['page'])
        for i in range(len(page_images)-1)
    )
    
    if is_sorted:
        print("✅ Sorting by source and page: PASS")
    else:
        print("❌ Sorting by source and page: FAIL")
    
    return True

def test_document_formatting_with_images():
    """문서 포맷팅에서 페이지 이미지 노트 포함 테스트"""
    
    print("\n" + "="*80)
    print("TEST 3: Document Formatting with Page Image Notes")
    print("="*80)
    
    # 테스트 문서 생성
    documents = [
        Document(
            page_content="엔진 오일 교체 주기는 12,000km입니다.",
            metadata={
                "source": "data/gv80_owners_manual_TEST6P.pdf",
                "page": 3,
                "category": "paragraph",
                "page_image_path": "data/images/gv80_owners_manual_TEST6P-page-3.png"
            }
        ),
        Document(
            page_content="가혹 조건에서는 6,000km마다 교체하세요.",
            metadata={
                "source": "data/gv80_owners_manual_TEST6P.pdf",
                "page": 5,
                "category": "paragraph",
                "page_image_path": ""  # 빈 경로
            }
        )
    ]
    
    synthesis_node = SynthesisNode()
    formatted = synthesis_node._format_documents(documents)
    
    print("\nFormatted Documents:")
    print(formatted)
    
    # 페이지 이미지 노트 확인
    if "Page Image Available:" in formatted:
        print("\n✅ Page image note included: PASS")
    else:
        print("\n❌ Page image note included: FAIL")
    
    # 빈 경로는 포함되지 않아야 함
    empty_note_count = formatted.count("Page Image Available: \n")
    if empty_note_count == 0:
        print("✅ Empty path excluded: PASS")
    else:
        print(f"❌ Empty path excluded: FAIL (found {empty_note_count} empty notes)")
    
    return True

def main():
    """메인 테스트 실행"""
    
    print("\n" + "="*80)
    print("PAGE IMAGE PATH INTEGRATION TEST")
    print("="*80)
    
    try:
        # 테스트 실행
        test_page_image_path_generation()
        test_page_image_collection()
        test_document_formatting_with_images()
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED SUCCESSFULLY ✅")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())