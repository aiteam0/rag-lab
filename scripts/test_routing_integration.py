#!/usr/bin/env python3
"""
Query Routing 통합 테스트
전체 워크플로우를 실행하여 각 쿼리 타입이 올바르게 처리되는지 확인
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from langchain_core.messages import HumanMessage, AIMessage

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
from dotenv import load_dotenv

load_dotenv()

console = Console()

# 테스트 시나리오
TEST_SCENARIOS = [
    {
        "name": "Simple Query Test",
        "description": "일반적인 인사나 간단한 질문",
        "query": "안녕하세요! 오늘 기분이 어떠세요?",
        "expected": {
            "query_type": "simple",
            "should_have": ["final_answer"],
            "should_not_have": ["subtasks", "documents"]
        }
    },
    {
        "name": "RAG Required Test",
        "description": "자동차 제조 문서가 필요한 질문",
        "query": "GV80 엔진 오일 교체 주기와 권장 오일 사양을 알려주세요",
        "expected": {
            "query_type": "rag_required",
            "should_have": ["subtasks", "documents", "final_answer"],
            "should_not_have": []
        }
    },
    {
        "name": "History Reference Test", 
        "description": "이전 대화를 참조하는 질문",
        "query": "아까 말한 엔진 오일에 대해 더 자세히 설명해줘",
        "history": [
            HumanMessage(content="GV80 엔진 오일은 어떤 걸 써야 하나요?"),
            AIMessage(content="GV80 엔진에는 5W-30 또는 0W-30 규격의 오일을 사용하세요.")
        ],
        "expected": {
            "query_type": "history_required",
            "should_have": ["enhanced_query", "subtasks"],
            "should_not_have": []
        }
    },
    {
        "name": "Complex Multi-part Query",
        "description": "여러 서브태스크로 분해되는 복잡한 질문",
        "query": "전기차 배터리 생산 공정과 품질 검사 절차, 그리고 효율성 개선 방안을 설명해주세요",
        "expected": {
            "query_type": "rag_required",
            "should_have": ["subtasks", "documents"],
            "min_subtasks": 2
        }
    }
]


def analyze_workflow_path(events: list) -> Dict[str, Any]:
    """워크플로우 경로 분석"""
    path = []
    nodes_visited = set()
    
    for event in events:
        for node_name in event.keys():
            if node_name not in nodes_visited:
                path.append(node_name)
                nodes_visited.add(node_name)
    
    return {
        "path": " → ".join(path),
        "nodes_visited": list(nodes_visited),
        "total_events": len(events)
    }


def validate_result(state: Dict[str, Any], expected: Dict[str, Any]) -> tuple[bool, list[str]]:
    """결과 검증"""
    issues = []
    
    # Query type 확인
    actual_type = state.get("query_type")
    expected_type = expected.get("query_type")
    if actual_type != expected_type:
        issues.append(f"Query type mismatch: expected {expected_type}, got {actual_type}")
    
    # 필수 필드 확인
    for field in expected.get("should_have", []):
        if field not in state or not state[field]:
            issues.append(f"Missing required field: {field}")
    
    # 불필요한 필드 확인
    for field in expected.get("should_not_have", []):
        if field in state and state[field]:
            issues.append(f"Unexpected field present: {field}")
    
    # 최소 서브태스크 수 확인
    if "min_subtasks" in expected:
        subtasks = state.get("subtasks", [])
        if len(subtasks) < expected["min_subtasks"]:
            issues.append(f"Not enough subtasks: expected at least {expected['min_subtasks']}, got {len(subtasks)}")
    
    return len(issues) == 0, issues


async def run_test_scenario(workflow: MVPWorkflowGraph, scenario: Dict[str, Any]) -> Dict[str, Any]:
    """단일 테스트 시나리오 실행"""
    console.print(f"\n[bold cyan]Running: {scenario['name']}[/bold cyan]")
    console.print(f"[dim]{scenario['description']}[/dim]")
    console.print(f"Query: [yellow]{scenario['query']}[/yellow]")
    
    # 초기 상태 준비
    initial_state = {
        "query": scenario["query"],
        "workflow_status": "started",
        "metadata": {}
    }
    
    # 히스토리가 있으면 추가
    if "history" in scenario:
        initial_state["messages"] = scenario["history"]
        console.print(f"[dim]With conversation history: {len(scenario['history'])} messages[/dim]")
    
    try:
        # 워크플로우 실행
        start_time = datetime.now()
        events = []
        
        for event in workflow.app.stream(initial_state, config={"recursion_limit": 30}):
            events.append(event)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # 최종 상태 수집
        final_state = {}
        for event in events:
            for node_name, state in event.items():
                final_state.update(state)
        
        # 경로 분석
        path_info = analyze_workflow_path(events)
        
        # 결과 검증
        passed, issues = validate_result(final_state, scenario.get("expected", {}))
        
        # 결과 출력
        result_table = Table(show_header=True)
        result_table.add_column("Metric", style="cyan")
        result_table.add_column("Value")
        
        result_table.add_row("Status", "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]")
        result_table.add_row("Execution Time", f"{elapsed:.2f}s")
        result_table.add_row("Query Type", final_state.get("query_type", "unknown"))
        result_table.add_row("Workflow Path", path_info["path"])
        result_table.add_row("Total Events", str(path_info["total_events"]))
        
        if "enhanced_query" in final_state:
            result_table.add_row("Enhanced Query", final_state["enhanced_query"][:100])
        
        if "subtasks" in final_state:
            result_table.add_row("Subtasks Created", str(len(final_state["subtasks"])))
        
        if "documents" in final_state:
            result_table.add_row("Documents Retrieved", str(len(final_state["documents"])))
        
        if "final_answer" in final_state:
            answer_preview = str(final_state["final_answer"])[:200] + "..."
            result_table.add_row("Answer Preview", answer_preview)
        
        console.print(result_table)
        
        # 이슈가 있으면 출력
        if issues:
            console.print("\n[red]Issues found:[/red]")
            for issue in issues:
                console.print(f"  • {issue}")
        
        return {
            "scenario": scenario["name"],
            "passed": passed,
            "elapsed": elapsed,
            "path": path_info["path"],
            "issues": issues
        }
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return {
            "scenario": scenario["name"],
            "passed": False,
            "elapsed": 0,
            "path": "ERROR",
            "issues": [str(e)]
        }


async def main():
    """메인 테스트 함수"""
    console.print(Panel.fit(
        "[bold cyan]Query Routing Integration Test[/bold cyan]\n" +
        "Full workflow execution test for all query types",
        border_style="cyan"
    ))
    
    # 워크플로우 초기화
    console.print("\n[yellow]Initializing workflow...[/yellow]")
    workflow = MVPWorkflowGraph()
    
    # Query Routing 상태 확인
    routing_status = "ENABLED" if workflow.enable_routing else "DISABLED"
    status_color = "green" if workflow.enable_routing else "red"
    console.print(f"Query Routing: [{status_color}]{routing_status}[/{status_color}]\n")
    
    # 모든 시나리오 실행
    results = []
    for scenario in TEST_SCENARIOS:
        result = await run_test_scenario(workflow, scenario)
        results.append(result)
        await asyncio.sleep(1)  # API rate limiting 방지
    
    # 최종 요약
    console.print("\n" + "="*70)
    console.print("[bold cyan]Test Summary[/bold cyan]")
    
    summary_table = Table(show_header=True)
    summary_table.add_column("Scenario", style="cyan")
    summary_table.add_column("Status", justify="center")
    summary_table.add_column("Time", justify="right")
    summary_table.add_column("Path", style="dim")
    
    total_passed = 0
    total_time = 0
    
    for result in results:
        status = "[green]✅[/green]" if result["passed"] else "[red]❌[/red]"
        summary_table.add_row(
            result["scenario"],
            status,
            f"{result['elapsed']:.2f}s",
            result["path"][:50] + "..." if len(result["path"]) > 50 else result["path"]
        )
        
        if result["passed"]:
            total_passed += 1
        total_time += result["elapsed"]
    
    console.print(summary_table)
    
    # 전체 통계
    success_rate = (total_passed / len(results) * 100) if results else 0
    console.print(f"\n[bold]Overall Success Rate: {success_rate:.1f}%[/bold]")
    console.print(f"[bold]Total Execution Time: {total_time:.2f}s[/bold]")
    
    # 최종 판정
    if success_rate >= 75:
        console.print("\n[bold green]✅ INTEGRATION TEST PASSED[/bold green]")
    else:
        console.print("\n[bold red]❌ INTEGRATION TEST FAILED[/bold red]")
    
    # Query Routing이 비활성화된 경우 경고
    if not workflow.enable_routing:
        console.print("\n[yellow]⚠️  Query Routing is disabled. Enable it by setting ENABLE_QUERY_ROUTING=true in .env[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())