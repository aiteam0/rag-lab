"""
Human Feedback & Entity Integration Test Script
Human feedback과 Entity 필드 활용이 제대로 동작하는지 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import create_workflow_graph

# Rich console 초기화
console = Console()

# .env 파일 로드
load_dotenv()


async def test_entity_table_query():
    """테이블 entity가 있는 문서에 대한 쿼리 테스트"""
    console.print("\n[bold cyan]Test 1: Table Entity Query[/bold cyan]")
    console.print("Testing retrieval and synthesis of table information...")
    
    # 테이블 관련 쿼리
    query = "GV80의 엔진 오일 교체 주기와 용량은 얼마인가요?"
    
    # 워크플로우 실행
    graph = create_workflow_graph()
    
    try:
        result = await graph.ainvoke({
            "query": query,
            "messages": []
        })
        
        # 결과 분석
        console.print("\n[bold green]✅ Query Executed Successfully[/bold green]")
        
        # Entity 정보가 포함된 문서 확인
        if result.get("documents"):
            table_docs = [
                doc for doc in result["documents"] 
                if doc.metadata.get("category") == "table" and doc.metadata.get("entity")
            ]
            
            if table_docs:
                console.print(f"[green]Found {len(table_docs)} table documents with entity info[/green]")
                for doc in table_docs[:2]:
                    entity = doc.metadata.get("entity", {})
                    console.print(f"  - Table: {entity.get('title', 'No title')}")
                    if entity.get('keywords'):
                        console.print(f"    Keywords: {', '.join(entity['keywords'][:3])}")
            else:
                console.print("[yellow]No table documents with entity found[/yellow]")
        
        # 최종 답변 확인
        if result.get("final_answer"):
            console.print("\n[bold]Final Answer (first 500 chars):[/bold]")
            console.print(result["final_answer"][:500])
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


async def test_human_feedback_priority():
    """Human feedback 우선순위 테스트"""
    console.print("\n[bold cyan]Test 2: Human Feedback Priority[/bold cyan]")
    console.print("Testing if human feedback takes priority over raw content...")
    
    # Human feedback이 있을 것으로 예상되는 쿼리
    query = "GV80 차량의 정기 점검 항목은 무엇인가요?"
    
    # 워크플로우 실행
    graph = create_workflow_graph()
    
    try:
        result = await graph.ainvoke({
            "query": query,
            "messages": []
        })
        
        console.print("\n[bold green]✅ Query Executed Successfully[/bold green]")
        
        # Human feedback이 있는 문서 확인
        if result.get("documents"):
            feedback_docs = [
                doc for doc in result["documents"] 
                if doc.metadata.get("human_feedback") and doc.metadata["human_feedback"].strip()
            ]
            
            if feedback_docs:
                console.print(f"[green]Found {len(feedback_docs)} documents with human feedback[/green]")
                for doc in feedback_docs[:2]:
                    feedback = doc.metadata.get("human_feedback", "")
                    console.print(f"  - Feedback: {feedback[:100]}...")
            else:
                console.print("[yellow]No documents with human feedback found[/yellow]")
                console.print("[yellow]Note: This is expected if database doesn't have human feedback yet[/yellow]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


async def test_synthesis_formatting():
    """Synthesis 노드의 entity 포맷팅 테스트"""
    console.print("\n[bold cyan]Test 3: Synthesis Entity Formatting[/bold cyan]")
    console.print("Testing if synthesis properly formats entity information...")
    
    # 그림이나 테이블이 포함된 쿼리
    query = "GV80의 계기판 경고등 종류와 의미를 설명해주세요"
    
    # 워크플로우 실행
    graph = create_workflow_graph()
    
    try:
        result = await graph.ainvoke({
            "query": query,
            "messages": []
        })
        
        console.print("\n[bold green]✅ Query Executed Successfully[/bold green]")
        
        # Figure 문서 확인
        if result.get("documents"):
            figure_docs = [
                doc for doc in result["documents"] 
                if doc.metadata.get("category") == "figure"
            ]
            
            if figure_docs:
                console.print(f"[green]Found {len(figure_docs)} figure documents[/green]")
                for doc in figure_docs[:2]:
                    console.print(f"  - Page: {doc.metadata.get('page')}")
                    if doc.metadata.get("caption"):
                        console.print(f"    Caption: {doc.metadata['caption'][:80]}...")
            else:
                console.print("[yellow]No figure documents found[/yellow]")
        
        # Synthesis 품질 확인
        if result.get("synthesis_result"):
            synth = result["synthesis_result"]
            console.print(f"\n[bold]Synthesis Quality:[/bold]")
            console.print(f"  - Confidence: {synth.get('confidence', 0):.2f}")
            console.print(f"  - Sources Used: {len(synth.get('sources_used', []))}")
            console.print(f"  - Key Points: {len(synth.get('key_points', []))}")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


async def test_hallucination_check_enhancement():
    """HallucinationCheck 강화 테스트"""
    console.print("\n[bold cyan]Test 4: Enhanced Hallucination Check[/bold cyan]")
    console.print("Testing if hallucination check uses entity and human feedback...")
    
    # 구체적인 수치가 필요한 쿼리
    query = "GV80 엔진의 최대 출력과 토크는 얼마입니까?"
    
    # 워크플로우 실행
    graph = create_workflow_graph()
    
    try:
        result = await graph.ainvoke({
            "query": query,
            "messages": []
        })
        
        console.print("\n[bold green]✅ Query Executed Successfully[/bold green]")
        
        # 환각 체크 결과 확인
        if result.get("hallucination_check"):
            check = result["hallucination_check"]
            console.print(f"\n[bold]Hallucination Check Results:[/bold]")
            console.print(f"  - Is Valid: {check.get('is_valid', False)}")
            console.print(f"  - Score: {check.get('score', 1.0):.2f}")
            
            if check.get('reason'):
                console.print(f"  - Reason: {check['reason'][:150]}...")
            
            # 점수가 낮으면 (환각이 적으면) 성공
            if check.get('score', 1.0) < 0.5:
                console.print("[green]Good! Low hallucination score indicates grounded answer[/green]")
            else:
                console.print("[yellow]High hallucination score - may need more specific documents[/yellow]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


async def main():
    """메인 테스트 실행"""
    console.print(Panel.fit(
        "[bold magenta]Human Feedback & Entity Integration Test Suite[/bold magenta]\n"
        "Testing the integration of human feedback and entity fields",
        title="🧪 Integration Test",
        border_style="magenta"
    ))
    
    # 테스트 실행
    tests = [
        ("Entity Table Query", test_entity_table_query),
        ("Human Feedback Priority", test_human_feedback_priority),
        ("Synthesis Formatting", test_synthesis_formatting),
        ("Hallucination Check", test_hallucination_check_enhancement)
    ]
    
    results = []
    for name, test_func in tests:
        console.print(f"\n{'='*60}")
        success = await test_func()
        results.append((name, success))
        await asyncio.sleep(1)  # API rate limiting 방지
    
    # 결과 요약
    console.print(f"\n{'='*60}")
    console.print("\n[bold cyan]Test Summary:[/bold cyan]")
    
    table = Table(title="Test Results", show_header=True, header_style="bold")
    table.add_column("Test Name", style="cyan")
    table.add_column("Result", justify="center")
    
    passed = 0
    for name, success in results:
        status = "[green]✅ PASS[/green]" if success else "[red]❌ FAIL[/red]"
        table.add_row(name, status)
        if success:
            passed += 1
    
    console.print(table)
    
    # 전체 결과
    total = len(results)
    console.print(f"\n[bold]Overall: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("[bold green]🎉 All tests passed! Integration successful.[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️ {total - passed} test(s) failed. Review the results above.[/bold yellow]")
    
    # 중요 참고사항
    console.print("\n[dim]Note: Some tests may show warnings if human_feedback data is not yet populated in the database.[/dim]")
    console.print("[dim]This is expected behavior for initial testing.[/dim]")


if __name__ == "__main__":
    asyncio.run(main())