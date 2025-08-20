"""
Workflow Test Script
전체 LangGraph 워크플로우 테스트
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

load_dotenv()
console = Console()


def print_state_summary(state: Dict[str, Any], title: str = "State Summary"):
    """상태 요약 출력"""
    
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=30)
    table.add_column("Value", style="green")
    
    # 주요 필드만 표시
    key_fields = [
        "query",
        "workflow_status",
        "current_subtask_idx",
        "search_language",
        "confidence_score"
    ]
    
    for field in key_fields:
        if field in state:
            value = state[field]
            if isinstance(value, (list, dict)):
                value = f"{type(value).__name__} ({len(value)} items)"
            table.add_row(field, str(value))
    
    # 서브태스크 정보
    if "subtasks" in state:
        subtasks = state["subtasks"]
        table.add_row("subtasks", f"{len(subtasks)} subtasks")
        for idx, task in enumerate(subtasks):
            status = task.get("status", "pending")
            table.add_row(f"  └─ Subtask {idx}", f"{status}")
    
    # 문서 정보
    if "documents" in state:
        docs = state["documents"]
        table.add_row("documents", f"{len(docs)} documents retrieved")
    
    # 답변 정보
    if "final_answer" in state:
        answer = state["final_answer"][:100] + "..." if len(state["final_answer"]) > 100 else state["final_answer"]
        table.add_row("final_answer", answer)
    
    # 에러 정보
    if "error" in state:
        table.add_row("error", state["error"], style="red")
    
    console.print(table)


def print_metadata(state: Dict[str, Any]):
    """메타데이터 출력"""
    
    if "metadata" not in state:
        return
    
    metadata = state["metadata"]
    
    for key, value in metadata.items():
        if isinstance(value, dict):
            rprint(Panel(f"[bold]{key.upper()} Metadata[/bold]"))
            for k, v in value.items():
                if isinstance(v, list) and len(v) > 3:
                    rprint(f"  {k}: {type(v).__name__} ({len(v)} items)")
                else:
                    rprint(f"  {k}: {v}")


async def test_basic_query():
    """기본 쿼리 테스트"""
    
    console.print("\n[bold yellow]Test 1: Basic Query[/bold yellow]")
    console.print("=" * 60)
    
    # 워크플로우 생성
    workflow = MVPWorkflowGraph()
    
    # 테스트 쿼리
    query = "엔진 오일 교체 방법을 알려주세요"
    
    console.print(f"Query: {query}")
    console.print("Running workflow...")
    
    # 실행
    try:
        final_state = workflow.run(query)
        
        # 결과 출력
        print_state_summary(final_state, "Final State")
        print_metadata(final_state)
        
        # 성공 여부 확인
        if final_state.get("workflow_status") == "completed" or final_state.get("final_answer"):
            console.print("[green]✅ Test PASSED[/green]")
            return True
        else:
            console.print("[red]❌ Test FAILED[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


async def test_complex_query():
    """복잡한 쿼리 테스트"""
    
    console.print("\n[bold yellow]Test 2: Complex Query[/bold yellow]")
    console.print("=" * 60)
    
    # 워크플로우 생성
    workflow = MVPWorkflowGraph()
    
    # 복잡한 쿼리
    query = "GV80의 안전 기능과 연비 성능, 그리고 정기 점검 주기에 대해 자세히 설명해주세요"
    
    console.print(f"Query: {query}")
    console.print("Running workflow...")
    
    # 실행
    try:
        final_state = workflow.run(query)
        
        # 결과 출력
        print_state_summary(final_state, "Final State")
        
        # 서브태스크 확인
        if "subtasks" in final_state:
            console.print(f"\n[cyan]Generated {len(final_state['subtasks'])} subtasks[/cyan]")
            for idx, task in enumerate(final_state["subtasks"]):
                console.print(f"  {idx+1}. {task['query']}")
        
        # 성공 여부 확인
        if final_state.get("final_answer"):
            console.print("[green]✅ Test PASSED[/green]")
            return True
        else:
            console.print("[red]❌ Test FAILED[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


async def test_error_handling():
    """에러 처리 테스트"""
    
    console.print("\n[bold yellow]Test 3: Error Handling[/bold yellow]")
    console.print("=" * 60)
    
    # 워크플로우 생성
    workflow = MVPWorkflowGraph()
    
    # 빈 쿼리로 에러 유발
    query = ""
    
    console.print(f"Query: '{query}' (empty)")
    console.print("Running workflow...")
    
    # 실행
    try:
        final_state = workflow.run(query)
        
        # 결과 출력
        print_state_summary(final_state, "Final State")
        
        # 에러 처리 확인
        if final_state.get("error") or final_state.get("workflow_status") == "failed":
            console.print("[green]✅ Error handled properly[/green]")
            return True
        else:
            console.print("[yellow]⚠️ No error detected for empty query[/yellow]")
            return False
            
    except Exception as e:
        console.print(f"[green]✅ Exception caught: {e}[/green]")
        return True


async def test_streaming():
    """스트리밍 테스트"""
    
    console.print("\n[bold yellow]Test 4: Streaming[/bold yellow]")
    console.print("=" * 60)
    
    # 워크플로우 생성
    workflow = MVPWorkflowGraph()
    
    # 테스트 쿼리
    query = "타이어 공기압 확인 방법"
    
    console.print(f"Query: {query}")
    console.print("Streaming workflow events...")
    
    # 스트리밍 실행
    try:
        event_count = 0
        for event in workflow.stream(query):
            event_count += 1
            # 노드 이름 출력
            if event:
                node_name = list(event.keys())[0] if event else "unknown"
                console.print(f"  Event {event_count}: [cyan]{node_name}[/cyan]")
        
        console.print(f"Total events: {event_count}")
        
        if event_count > 0:
            console.print("[green]✅ Streaming test PASSED[/green]")
            return True
        else:
            console.print("[red]❌ No events received[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


async def main():
    """메인 테스트 함수"""
    
    console.print("\n[bold magenta]MVP Workflow Test Suite[/bold magenta]")
    console.print("=" * 60)
    
    # DB 연결 확인
    required_env = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME", "OPENAI_API_KEY"]
    missing = [key for key in required_env if not os.getenv(key)]
    
    if missing:
        console.print(f"[red]Missing environment variables: {missing}[/red]")
        console.print("Please check your .env file")
        return
    
    # 테스트 실행
    results = []
    
    # 기본 쿼리 테스트
    results.append(("Basic Query", await test_basic_query()))
    
    # 복잡한 쿼리 테스트
    results.append(("Complex Query", await test_complex_query()))
    
    # 에러 처리 테스트
    results.append(("Error Handling", await test_error_handling()))
    
    # 스트리밍 테스트
    results.append(("Streaming", await test_streaming()))
    
    # 결과 요약
    console.print("\n" + "=" * 60)
    console.print("[bold magenta]Test Results Summary[/bold magenta]")
    console.print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[green]PASSED[/green]" if result else "[red]FAILED[/red]"
        console.print(f"{test_name:20} {status}")
    
    console.print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        console.print("[bold green]🎉 All tests passed![/bold green]")
    else:
        console.print(f"[bold yellow]⚠️ {total - passed} tests failed[/bold yellow]")


if __name__ == "__main__":
    asyncio.run(main())