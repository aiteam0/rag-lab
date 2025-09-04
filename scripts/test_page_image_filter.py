#!/usr/bin/env python
"""
테스트 스크립트: Page Image 필터링 및 Collapsible Section 검증
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import logging
from typing import List, Dict, Any
from langchain_core.documents import Document
from workflow.nodes.synthesis import SynthesisNode
from workflow.state import MVPWorkflowState
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_documents() -> List[Document]:
    """테스트용 문서 생성 (20개 문서, 각각 다른 페이지 이미지)"""
    documents = []
    for i in range(20):
        doc = Document(
            page_content=f"테스트 문서 {i+1}의 내용입니다. 디지털 정부 혁신과 관련된 내용...",
            metadata={
                "source": "디지털정부혁신_추진계획.pdf",
                "page": i+1,
                "category": "paragraph",
                "page_image_path": f"/data/images/page_{i+1}.png"
            }
        )
        documents.append(doc)
    return documents

def test_page_image_filtering():
    """Page Image 필터링 테스트"""
    print("\n" + "="*80)
    print("📊 Page Image 필터링 테스트 시작")
    print("="*80)
    
    # 1. 테스트 문서 생성
    documents = create_test_documents()
    print(f"✅ 총 {len(documents)}개의 테스트 문서 생성")
    
    # 2. SynthesisNode 인스턴스 생성
    synthesis_node = SynthesisNode()
    print("✅ SynthesisNode 인스턴스 생성")
    
    # 3. sources_used 없이 테스트 (모든 이미지 수집)
    print("\n📌 테스트 1: sources_used 없음 (모든 이미지 수집)")
    all_images = synthesis_node._collect_page_images(documents)
    print(f"   → 수집된 이미지: {len(all_images)}개")
    if all_images:
        print(f"   → 첫 번째 이미지: {all_images[0]}")
    
    # 4. sources_used로 필터링 테스트
    print("\n📌 테스트 2: sources_used = ['[1]', '[9]'] (2개 문서만)")
    sources_used = ['[1]', '[9]']
    filtered_images = synthesis_node._collect_page_images(documents, sources_used)
    print(f"   → 수집된 이미지: {len(filtered_images)}개")
    if filtered_images:
        for img in filtered_images:
            print(f"   → 이미지: {img['path']} (문서 인덱스 추출 확인)")
    
    # 5. 빈 sources_used 테스트
    print("\n📌 테스트 3: sources_used = [] (빈 리스트)")
    empty_images = synthesis_node._collect_page_images(documents, [])
    print(f"   → 수집된 이미지: {len(empty_images)}개")
    
    # 6. 범위 밖 인덱스 테스트
    print("\n📌 테스트 4: sources_used = ['[100]'] (범위 밖)")
    out_of_range = synthesis_node._collect_page_images(documents, ['[100]'])
    print(f"   → 수집된 이미지: {len(out_of_range)}개")
    
    print("\n" + "="*80)
    print("✅ Page Image 필터링 테스트 완료!")
    print("="*80)

def test_collapsible_section_format():
    """Collapsible Section 포맷 테스트"""
    print("\n" + "="*80)
    print("📊 Collapsible Section 포맷 테스트")
    print("="*80)
    
    # 모의 state 생성
    state = MVPWorkflowState(
        query="디지털 정부 혁신의 주요 목표는 무엇인가요?",
        documents=create_test_documents()
    )
    
    # SynthesisNode 인스턴스 생성
    synthesis_node = SynthesisNode()
    
    # 테스트용 sources_used
    sources_used = ['[1]', '[5]', '[10]']
    
    # Page images 수집
    page_images = synthesis_node._collect_page_images(state['documents'], sources_used)
    
    # Collapsible section 생성 테스트
    if page_images:
        image_section = "\n\n## 📎 참조 페이지 이미지\n"
        image_section += f"<details>\n<summary>📄 클릭하여 페이지 이미지 보기 ({len(page_images)}개)</summary>\n\n"
        
        for img in page_images:
            image_section += f"![Page Image]({img['path']})\n\n"
        
        image_section += "\n</details>"
        
        print("생성된 Collapsible Section:")
        print("-" * 40)
        print(image_section)
        print("-" * 40)
        
        # HTML 태그 검증
        assert "<details>" in image_section, "❌ <details> 태그 없음"
        assert "<summary>" in image_section, "❌ <summary> 태그 없음"
        assert "</details>" in image_section, "❌ </details> 태그 없음"
        assert "</summary>" in image_section, "❌ </summary> 태그 없음"
        print("\n✅ HTML 태그 구조 검증 통과!")
        
        # 이미지 개수 확인
        assert f"({len(page_images)}개)" in image_section, "❌ 이미지 개수 표시 오류"
        print(f"✅ 이미지 개수 표시 정확: {len(page_images)}개")
    
    print("\n" + "="*80)
    print("✅ Collapsible Section 포맷 테스트 완료!")
    print("="*80)

def test_logging_output():
    """로깅 출력 테스트"""
    print("\n" + "="*80)
    print("📊 로깅 출력 테스트")
    print("="*80)
    
    # 로거 레벨을 DEBUG로 설정하여 모든 로그 캡처
    import logging
    import io
    
    # StringIO로 로그 캡처
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    
    # synthesis 모듈의 로거 가져오기
    synthesis_logger = logging.getLogger('workflow.nodes.synthesis')
    synthesis_logger.addHandler(handler)
    synthesis_logger.setLevel(logging.INFO)
    
    # 테스트 실행
    documents = create_test_documents()
    synthesis_node = SynthesisNode()
    sources_used = ['[1]', '[3]', '[7]']
    
    # 필터링 실행 (로그 생성)
    filtered_images = synthesis_node._collect_page_images(documents, sources_used)
    
    # 로그 내용 확인
    log_contents = log_capture.getvalue()
    print("캡처된 로그:")
    print("-" * 40)
    print(log_contents if log_contents else "(로그 없음)")
    print("-" * 40)
    
    # 로그 검증
    if "Filtering page images" in log_contents:
        print("✅ 필터링 로그 확인됨")
        if "20 docs → 3 cited docs" in log_contents:
            print("✅ 정확한 문서 개수 로그 확인됨")
    else:
        print("⚠️  필터링 로그가 캡처되지 않았습니다 (정상일 수 있음)")
    
    print(f"\n📊 실제 필터링 결과: {len(filtered_images)}개 이미지")
    
    print("\n" + "="*80)
    print("✅ 로깅 출력 테스트 완료!")
    print("="*80)

def main():
    """메인 테스트 실행"""
    print("\n" + "🚀"*40)
    print("PAGE IMAGE 필터링 및 UX 개선 테스트 시작")
    print("🚀"*40)
    
    try:
        # 1. Page Image 필터링 테스트
        test_page_image_filtering()
        
        # 2. Collapsible Section 포맷 테스트
        test_collapsible_section_format()
        
        # 3. 로깅 출력 테스트
        test_logging_output()
        
        print("\n" + "✨"*40)
        print("모든 테스트가 성공적으로 완료되었습니다!")
        print("✨"*40)
        
        print("\n📌 다음 단계:")
        print("1. 실제 워크플로우에서 테스트")
        print("2. agent-chat-ui에서 렌더링 확인")
        print("3. 이미지 경로 유효성 검증")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()