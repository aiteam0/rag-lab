#!/usr/bin/env python3
"""
페이지 이미지 포함 테스트 스크립트
SynthesisResult의 page_images 필드와 답변 내 이미지 섹션 확인
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflow.graph import create_workflow
from workflow.state import MVPWorkflowState
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint

# 환경변수 로드
load_dotenv()

# Rich 콘솔 설정
console = Console()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def test_page_image_inclusion():
    """페이지 이미지가 답변에 포함되는지 테스트"""
    
    console.print("\n[bold cyan]🔍 페이지 이미지 포함 테스트 시작[/bold cyan]\n")
    
    # 테스트 쿼리들 (처음 1개만 테스트)
    test_queries = [
        "엔진 오일 교체 방법을 알려줘"
    ]
    
    # 워크플로우 생성
    app = create_workflow()
    
    for idx, query in enumerate(test_queries, 1):
        console.print(f"\n[yellow]📝 테스트 {idx}/{len(test_queries)}: {query}[/yellow]")
        console.print("-" * 50)
        
        # 초기 상태 설정
        initial_state = {
            "query": query,
            "messages": [],
            "documents": [],
            "subtasks": [],
            "current_subtask_idx": 0,
            "final_answer": None,
            "confidence_score": 0.0,
            "metadata": {},
            "warnings": [],
            "error": None,
            "workflow_status": "running",
            "retry_count": 0
        }
        
        try:
            # 워크플로우 실행
            logger.info(f"워크플로우 실행 중: {query}")
            final_state = app.invoke(initial_state)
            
            # 결과 확인
            final_answer = final_state.get("final_answer")
            confidence = final_state.get("confidence_score", 0.0)
            metadata = final_state.get("metadata", {})
            
            if final_answer:
                # 페이지 이미지 섹션 확인
                has_page_images = "## 📎 참조 페이지 이미지" in final_answer
                image_count = final_answer.count("![Page ")
                
                # synthesis 메타데이터에서 page_images 확인
                synthesis_meta = metadata.get("synthesis", {})
                page_images_meta = synthesis_meta.get("page_images", [])
                
                # 결과 출력
                console.print(f"\n[green]✅ 답변 생성 성공[/green]")
                console.print(f"   신뢰도: {confidence:.0%}")
                console.print(f"   답변 길이: {len(final_answer)} 문자")
                
                # 페이지 이미지 정보
                if has_page_images:
                    console.print(f"   [bold green]📸 페이지 이미지 섹션: 있음[/bold green]")
                    console.print(f"   이미지 개수: {image_count}개")
                else:
                    console.print(f"   [bold red]❌ 페이지 이미지 섹션: 없음[/bold red]")
                
                # 메타데이터 확인
                if page_images_meta:
                    console.print(f"   [green]📋 메타데이터 page_images: {len(page_images_meta)}개[/green]")
                    for img in page_images_meta[:3]:  # 처음 3개만 표시
                        if isinstance(img, dict):
                            console.print(f"      - Page {img.get('page', '?')}: {img.get('source', 'Unknown')}")
                else:
                    console.print(f"   [yellow]⚠️ 메타데이터에 page_images 없음[/yellow]")
                
                # 답변 내용 일부 표시
                console.print(f"\n[dim]답변 미리보기 (처음 500자):[/dim]")
                preview = final_answer[:500] + "..." if len(final_answer) > 500 else final_answer
                console.print(Panel(preview, title="답변", border_style="cyan"))
                
                # 이미지 섹션 추출 및 표시
                if "## 📎 참조 페이지 이미지" in final_answer:
                    image_section_start = final_answer.index("## 📎 참조 페이지 이미지")
                    image_section = final_answer[image_section_start:]
                    console.print(f"\n[bold cyan]페이지 이미지 섹션:[/bold cyan]")
                    console.print(Panel(image_section, border_style="green"))
                
            else:
                console.print(f"[red]❌ 답변 생성 실패[/red]")
                if final_state.get("error"):
                    console.print(f"   에러: {final_state['error']}")
                
        except Exception as e:
            console.print(f"[red]❌ 워크플로우 실행 중 에러: {str(e)}[/red]")
            logger.error(f"에러 상세: {e}", exc_info=True)
    
    console.print("\n[bold cyan]✨ 테스트 완료![/bold cyan]\n")


def check_image_files():
    """실제 이미지 파일 존재 확인"""
    console.print("\n[bold cyan]📂 이미지 파일 확인[/bold cyan]\n")
    
    image_dir = project_root / "data" / "images"
    
    if image_dir.exists():
        image_files = list(image_dir.glob("*.png"))
        console.print(f"이미지 디렉토리: {image_dir}")
        console.print(f"총 이미지 파일: {len(image_files)}개\n")
        
        # 처음 10개 파일만 표시
        for img_file in image_files[:10]:
            size_kb = img_file.stat().st_size / 1024
            console.print(f"  📷 {img_file.name} ({size_kb:.1f} KB)")
        
        if len(image_files) > 10:
            console.print(f"  ... 외 {len(image_files) - 10}개")
    else:
        console.print(f"[red]❌ 이미지 디렉토리가 존재하지 않습니다: {image_dir}[/red]")


if __name__ == "__main__":
    # 이미지 파일 확인
    check_image_files()
    
    # 페이지 이미지 포함 테스트
    test_page_image_inclusion()