#!/usr/bin/env python
"""
간단한 Page Image 필터링 테스트
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
import re


def test_page_image_filtering():
    """Page Image 필터링 테스트 - 단일 쿼리"""
    
    print("="*60)
    print("Page Image 필터링 테스트 - 단일 쿼리")
    print("="*60)
    
    # 워크플로우 생성
    print("\n1. 워크플로우 생성...")
    workflow = MVPWorkflowGraph()
    print("   ✅ 워크플로우 생성 완료")
    
    # 테스트 쿼리 - RAG가 필요한 쿼리
    query = "GV80의 엔진 오일 교체 주기는?"
    print(f"\n2. 테스트 쿼리: '{query}'")
    
    # 워크플로우 실행
    print("\n3. 워크플로우 실행 중...")
    result = workflow.run(query)
    
    # 결과 분석
    print("\n4. 결과 분석:")
    
    if result.get("error"):
        print(f"   ❌ 오류 발생: {result['error']}")
        return False
    
    if result.get("workflow_status") == "failed":
        print(f"   ❌ 워크플로우 실패")
        return False
    
    # 답변 확인
    answer = result.get("final_answer", "")
    if not answer:
        print("   ⚠️  답변이 생성되지 않았습니다")
        return False
    
    print(f"   ✅ 답변 생성됨 (길이: {len(answer)}자)")
    
    # Page Image 섹션 확인
    print("\n5. Page Image 섹션 분석:")
    
    if "## 📎 참조 페이지 이미지" in answer:
        print("   ✅ Page Image 섹션 발견!")
        
        # Collapsible 태그 확인
        if "<details>" in answer and "</details>" in answer:
            print("   ✅ Collapsible section (<details> 태그) 확인됨")
        else:
            print("   ❌ Collapsible section 태그가 없습니다")
        
        # 이미지 개수 추출
        match = re.search(r'보기 \((\d+)개\)', answer)
        if match:
            image_count = int(match.group(1))
            print(f"   ✅ 표시된 이미지 개수: {image_count}개")
            
            # 실제 이미지 경로 추출
            image_paths = re.findall(r'!\[.*?\]\((.*?)\)', answer)
            actual_count = len(image_paths)
            print(f"   ✅ 실제 이미지 개수: {actual_count}개")
            
            if image_count == actual_count:
                print("   ✅ 이미지 개수가 일치합니다!")
            else:
                print(f"   ⚠️  이미지 개수 불일치: 표시={image_count}, 실제={actual_count}")
        
        # Page Image 섹션 추출 및 표시
        section_match = re.search(
            r'## 📎 참조 페이지 이미지.*?(?=##|\Z)', 
            answer, 
            re.DOTALL
        )
        
        if section_match:
            section = section_match.group(0)
            print("\n   📄 Page Image 섹션 내용:")
            print("   " + "="*50)
            # 처음 500자만 표시
            preview = section[:500] + "..." if len(section) > 500 else section
            print(f"   {preview}")
            print("   " + "="*50)
    else:
        print("   ℹ️  Page Image 섹션이 답변에 없습니다")
    
    # sources_used 확인
    print("\n6. 소스 필터링 분석:")
    
    # 메타데이터에서 sources_used 확인
    metadata = result.get("metadata", {})
    synthesis_meta = metadata.get("synthesis", {})
    sources_used = synthesis_meta.get("sources", [])
    
    if sources_used:
        print(f"   ✅ 인용된 소스: {sources_used}")
    else:
        print("   ℹ️  sources_used 정보 없음")
    
    # 전체 문서와 비교
    documents = result.get("documents", [])
    if documents:
        total_docs = len(documents)
        print(f"   📊 총 검색된 문서: {total_docs}개")
        
        if sources_used:
            cited_count = len(sources_used)
            print(f"   📊 실제 인용된 문서: {cited_count}개")
            print(f"   📊 필터링 비율: {cited_count}/{total_docs} = {cited_count/total_docs*100:.1f}%")
    
    print("\n" + "="*60)
    print("✨ 테스트 완료!")
    print("="*60)
    
    return True


if __name__ == "__main__":
    success = test_page_image_filtering()
    sys.exit(0 if success else 1)
