#!/usr/bin/env python3
"""
Test script for SynthesisResult schema enhancements
Tests the new fields: human_feedback_used, entity_references, warnings
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflow.nodes.synthesis import SynthesisNode, EntityReference
from langchain_core.documents import Document

def create_test_documents():
    """Create test documents with various metadata types"""
    
    docs = [
        # Document with 똑딱이 entity
        Document(
            page_content="디지털 정부혁신 계획에 따르면 클라우드 전환율을 2025년까지 50%로 향상시킬 예정입니다.",
            metadata={
                "source": "디지털정부혁신_추진계획.pdf",
                "page": 15,
                "category": "paragraph",
                "entity": {
                    "type": "똑딱이",
                    "title": "클라우드 전환 목표",
                    "details": "공공 부문 클라우드 전환율 목표치",
                    "keywords": ["클라우드", "전환율", "2025년", "50%"]
                },
                "page_image_path": "data/images/디지털정부혁신_추진계획-page-15.png"
            }
        ),
        
        # Document with table entity
        Document(
            page_content="엔진 오일 교체 주기는 다음 표를 참조하세요.",
            metadata={
                "source": "gv80_owners_manual_TEST6P.pdf",
                "page": 5,
                "category": "table",
                "entity": {
                    "title": "엔진 오일 교체 주기표",
                    "details": "주행 조건별 교체 주기",
                    "keywords": ["엔진오일", "교체주기", "정비"]
                },
                "page_image_path": "data/images/gv80_owners_manual_TEST6P-page-5.png"
            }
        ),
        
        # Document with figure entity
        Document(
            page_content="그림 3-1은 엔진룸 구성요소를 보여줍니다.",
            metadata={
                "source": "gv80_owners_manual_TEST6P.pdf",
                "page": 6,
                "category": "figure",
                "entity": {
                    "title": "엔진룸 구성도",
                    "details": "엔진룸 주요 부품 위치 설명"
                },
                "caption": "그림 3-1. 엔진룸 구성요소",
                "page_image_path": "data/images/gv80_owners_manual_TEST6P-page-6.png"
            }
        ),
        
        # Document with human feedback
        Document(
            page_content="엔진 오일은 10,000km마다 교체하세요.",
            metadata={
                "source": "gv80_owners_manual_TEST6P.pdf",
                "page": 7,
                "category": "paragraph",
                "human_feedback": "정정: 가혹 조건에서는 5,000km마다 교체 필요",
                "page_image_path": "data/images/gv80_owners_manual_TEST6P-page-7.png"
            }
        ),
        
        # Document with warning content
        Document(
            page_content="경고: 엔진이 뜨거울 때는 절대 오일 캡을 열지 마세요. 주의: 화상의 위험이 있습니다.",
            metadata={
                "source": "gv80_owners_manual_TEST6P.pdf",
                "page": 8,
                "category": "paragraph"
            }
        ),
        
        # Regular document without special metadata
        Document(
            page_content="정기적인 엔진 오일 점검은 차량 성능 유지에 중요합니다.",
            metadata={
                "source": "gv80_owners_manual_TEST6P.pdf",
                "page": 9,
                "category": "paragraph"
            }
        )
    ]
    
    return docs

def test_synthesis_with_new_fields():
    """Test synthesis with new schema fields"""
    
    print("\n" + "="*60)
    print("Testing SynthesisResult Schema Enhancements")
    print("="*60)
    
    # Initialize synthesis node
    synthesis_node = SynthesisNode()
    
    # Create test documents
    test_docs = create_test_documents()
    print(f"\n✅ Created {len(test_docs)} test documents")
    
    # Test query
    query = "엔진 오일 교체 방법과 주의사항을 알려주세요"
    print(f"\n🔍 Query: {query}")
    
    # Generate answer
    print("\n⚙️  Generating synthesis...")
    result = synthesis_node._generate_answer_with_fallback(query, test_docs)
    
    # Check results
    print("\n" + "-"*60)
    print("📊 SYNTHESIS RESULTS")
    print("-"*60)
    
    # Basic fields
    print(f"\n✅ Answer generated: {len(result.answer)} characters")
    print(f"✅ Confidence: {result.confidence:.2%}")
    print(f"✅ Sources used: {result.sources_used}")
    print(f"✅ Key points: {len(result.key_points)} points")
    
    # Check new fields
    print("\n" + "-"*40)
    print("🆕 NEW FIELDS CHECK")
    print("-"*40)
    
    # 1. Human feedback
    if result.human_feedback_used:
        print(f"\n✅ Human feedback captured: {len(result.human_feedback_used)} entries")
        for feedback in result.human_feedback_used:
            print(f"   - {feedback[:50]}...")
    else:
        print("\n⚠️  No human feedback found (expected at least 1)")
    
    # 2. Entity references
    if result.entity_references:
        print(f"\n✅ Entity references captured: {len(result.entity_references)} entities")
        for ref in result.entity_references:
            print(f"   - {ref.entity_type}: {ref.title} (from {ref.source_doc})")
            if ref.details:
                print(f"     Details: {ref.details[:50]}...")
    else:
        print("\n⚠️  No entity references found (expected at least 3)")
    
    # 3. Warnings
    if result.warnings:
        print(f"\n✅ Warnings extracted: {len(result.warnings)} warnings")
        for warning in result.warnings:
            print(f"   - {warning[:80]}...")
    else:
        print("\n⚠️  No warnings found (expected at least 1)")
    
    # 4. Page images (regression test)
    if result.page_images:
        print(f"\n✅ Page images preserved: {len(result.page_images)} images")
        for img in result.page_images[:3]:  # Show first 3
            print(f"   - Page {img.page}: {img.source}")
    else:
        print("\n⚠️  No page images found (expected at least 4)")
    
    # Validation summary
    print("\n" + "="*60)
    print("📋 VALIDATION SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    # Check each new field
    tests = [
        ("Human feedback collection", result.human_feedback_used and len(result.human_feedback_used) > 0),
        ("Entity references (똑딱이)", 
         result.entity_references and any(r.entity_type == "똑딱이" for r in result.entity_references)),
        ("Entity references (table)", 
         result.entity_references and any(r.entity_type == "table" for r in result.entity_references)),
        ("Entity references (figure)", 
         result.entity_references and any(r.entity_type == "figure" for r in result.entity_references)),
        ("Warnings extraction", result.warnings and len(result.warnings) > 0),
        ("Page images (regression)", result.page_images and len(result.page_images) > 0),
        ("References table exists", result.references_table and len(result.references_table) > 0)
    ]
    
    for test_name, test_result in tests:
        if test_result:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: FAILED")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    # Show answer preview
    print("\n" + "-"*60)
    print("📝 ANSWER PREVIEW (first 500 chars)")
    print("-"*60)
    preview = result.answer[:500] + "..." if len(result.answer) > 500 else result.answer
    print(preview)
    
    # Overall result
    print("\n" + "="*60)
    if failed == 0:
        print("🎉 All tests PASSED! Schema enhancements working correctly.")
    else:
        print(f"⚠️  {failed} tests failed. Please check the implementation.")
    print("="*60)
    
    return result

def test_entity_specific():
    """Test entity reference extraction specifically"""
    print("\n" + "="*60)
    print("Testing Entity Reference Extraction")
    print("="*60)
    
    synthesis_node = SynthesisNode()
    
    # Create document with multiple entity types
    docs = [
        Document(
            page_content="Test content",
            metadata={
                "entity": {
                    "type": "똑딱이",
                    "title": "Test 똑딱이",
                    "details": "Test details"
                },
                "category": "paragraph"
            }
        ),
        Document(
            page_content="Table content",
            metadata={
                "entity": {
                    "title": "Test Table",
                    "details": "Table details",
                    "keywords": ["test", "table"]
                },
                "category": "table"
            }
        )
    ]
    
    # Create doc_idx_map
    doc_idx_map = {0: "[1]", 1: "[2]"}
    
    # Test entity collection
    entity_refs = synthesis_node._collect_entity_references(docs, doc_idx_map)
    
    print(f"\nFound {len(entity_refs)} entity references:")
    for ref in entity_refs:
        print(f"  - Type: {ref.entity_type}")
        print(f"    Title: {ref.title}")
        print(f"    Details: {ref.details}")
        print(f"    Source: {ref.source_doc}")
    
    assert len(entity_refs) == 2, f"Expected 2 entities, got {len(entity_refs)}"
    assert entity_refs[0].entity_type == "똑딱이", "First entity should be 똑딱이"
    assert entity_refs[1].entity_type == "table", "Second entity should be table"
    
    print("\n✅ Entity reference extraction test PASSED")

if __name__ == "__main__":
    try:
        # Run main test
        result = test_synthesis_with_new_fields()
        
        # Run entity-specific test
        test_entity_specific()
        
        print("\n✨ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)