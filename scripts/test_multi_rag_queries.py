#!/usr/bin/env python
"""
Multi-turn RAG 문서 누적 수정 테스트 - 두 개의 명확한 RAG 쿼리 사용
Custom reducer가 제대로 작동하여 문서가 누적되지 않는지 검증
"""

import os
import sys
import time
import logging
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from workflow.graph import MVPWorkflowGraph
from rich.console import Console
from rich.table import Table

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()

def test_multi_rag():
    """두 개의 RAG 쿼리로 문서 누적 테스트"""
    
    console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]")
    console.print("[bold cyan]Multi-turn RAG 문서 누적 수정 테스트 v2[/bold cyan]")
    console.print("[bold cyan]" + "="*60 + "[/bold cyan]")
    
    # 워크플로우 그래프 생성
    workflow = MVPWorkflowGraph()
    
    # 명확한 RAG 쿼리들
    test_queries = [
        ("안녕", "simple"),
        ("클라우드와 디지털 서비스 이용 활성화에 대해 알려줘", "rag"),
        ("디지털 정부혁신 추진계획의 주요 내용을 설명해줘", "rag"),
    ]
    
    # 결과 저장
    results = []
    rag_doc_counts = []
    
    for i, (query, expected_type) in enumerate(test_queries, 1):
        console.print(f"\n[bold yellow]--- 쿼리 {i}: '{query}' (예상: {expected_type}) ---[/bold yellow]")
        
        # 워크플로우 실행
        try:
            start_time = time.time()
            result = workflow.run(query)
            elapsed = time.time() - start_time
            
            # 결과 저장
            results.append(result)
            
            # 문서 수 확인
            documents = result.get("documents", [])
            query_type = result.get("query_type", "unknown")
            
            console.print(f"[green]✅ 쿼리 완료 ({elapsed:.2f}초)[/green]")
            console.print(f"   - 쿼리 타입: {query_type}")
            console.print(f"   - state의 문서 수: {len(documents)}")
            
            # RAG 쿼리의 경우 문서 수 기록
            if query_type == "rag_required" or expected_type == "rag":
                rag_doc_counts.append(len(documents))
                console.print(f"   [bold blue]📝 RAG 쿼리 #{len(rag_doc_counts)}: {len(documents)} documents[/bold blue]")
                
                # Synthesis 정보 확인
                metadata = result.get("metadata", {})
                synthesis_info = metadata.get("synthesis", {})
                docs_used = synthesis_info.get("documents_used", 0)
                if docs_used > 0:
                    console.print(f"   - Synthesis 사용 문서: {docs_used}")
            
        except Exception as e:
            console.print(f"[red]❌ 쿼리 실행 실패: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
            break
    
    # 결과 분석
    console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]")
    console.print("[bold cyan]테스트 결과 분석[/bold cyan]")
    console.print("[bold cyan]" + "="*60 + "[/bold cyan]")
    
    if len(rag_doc_counts) >= 2:
        first_rag = rag_doc_counts[0]
        second_rag = rag_doc_counts[1]
        
        # 결과 테이블
        table = Table(title="Multi-turn RAG 문서 수 비교")
        table.add_column("RAG 쿼리", style="cyan")
        table.add_column("문서 수", style="magenta")
        table.add_column("상태", style="green")
        
        table.add_row("첫 번째 RAG", str(first_rag), "✅")
        table.add_row("두 번째 RAG", str(second_rag), "✅" if second_rag <= first_rag else "❌")
        
        console.print(table)
        
        # 누적 검사
        if second_rag > first_rag * 1.5:
            console.print(f"\n[red]❌ 문서 누적 발생! ({first_rag} → {second_rag})[/red]")
            console.print("[red]Custom reducer가 제대로 작동하지 않음[/red]")
        else:
            console.print(f"\n[green]✅ 문서 누적 없음! (첫 RAG: {first_rag}, 두 번째 RAG: {second_rag})[/green]")
            console.print("[green]Custom reducer가 정상 작동 중[/green]")
            
        # 추가 검증
        if second_rag <= 30:  # 합리적인 문서 수
            console.print("[green]✅ 두 번째 RAG 문서 수가 정상 범위[/green]")
        else:
            console.print(f"[yellow]⚠️ 두 번째 RAG 문서 수가 많음: {second_rag}[/yellow]")
            
    else:
        console.print(f"[yellow]⚠️ RAG 쿼리가 {len(rag_doc_counts)}개만 실행됨 (최소 2개 필요)[/yellow]")
    
    console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]")
    console.print("[bold cyan]테스트 완료[/bold cyan]")
    console.print("[bold cyan]" + "="*60 + "[/bold cyan]")


if __name__ == "__main__":
    test_multi_rag()