#!/usr/bin/env python3
"""
Query Routing 테스트 스크립트
3가지 쿼리 타입을 테스트하고 라우팅이 제대로 작동하는지 확인
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import track
from rich import print as rprint
from langchain_core.messages import HumanMessage, AIMessage

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

console = Console()

# 테스트 케이스 정의
TEST_CASES = [
    # 1. Simple queries (일반 지식으로 답변 가능)
    {
        "category": "simple",
        "queries": [
            "안녕하세요",
            "오늘 날씨가 어때요?",
            "What is 2 + 2?",
            "자동차의 일반적인 수명은 얼마나 되나요?",
            "전기차와 가솔린차의 일반적인 차이점은?",
        ],
        "expected_route": "direct_response",
        "color": "green"
    },
    
    # 2. RAG required queries (문서 검색 필요)
    {
        "category": "rag_required",
        "queries": [
            "GV80 엔진 오일 교체 주기는?",
            "전기차 배터리 생산 공정을 설명해줘",
            "자동차 조립 라인의 품질 검사 프로세스는?",
            "표로 정리된 엔진 사양을 보여줘",
            "6페이지에 있는 안전벨트 착용 방법",
        ],
        "expected_route": "planning",
        "color": "blue"
    },
    
    # 3. History required queries (이전 대화 참조)
    {
        "category": "history_required",
        "queries": [
            ("GV80의 엔진 사양을 알려줘", "방금 말한 엔진의 최대 출력은?"),
            ("배터리 생산 공정의 효율성은?", "그것의 작년 대비 개선율은?"),
            ("브레이크 시스템 점검 방법", "거기에 필요한 도구는 뭐야?"),
            ("엔진 오일 교체 비용", "아까 말한 것을 표로 정리해줘"),
            ("차량 안전 기능 목록", "이전에 언급한 기능들 중 가장 중요한 건?"),
        ],
        "expected_route": "context_enhancement",
        "color": "yellow"
    }
]


def print_test_header(category: str, color: str):
    """테스트 카테고리 헤더 출력"""
    console.print(f"\n[{color}]{'='*60}[/{color}]")
    console.print(f"[{color}]Testing {category.upper()} Queries[/{color}]")
    console.print(f"[{color}]{'='*60}[/{color}]\n")


def print_query_result(query: str, result: Dict[str, Any], expected_route: str):
    """쿼리 결과 출력"""
    # 쿼리 타입과 라우팅 결과 확인
    query_type = result.get("query_type", "unknown")
    current_node = result.get("current_node", "unknown")
    
    # 성공/실패 판단
    if query_type == "simple" and expected_route == "direct_response":
        status = "✅ PASS"
        status_color = "green"
    elif query_type == "rag_required" and expected_route == "planning":
        status = "✅ PASS"
        status_color = "green"
    elif query_type == "history_required" and expected_route == "context_enhancement":
        status = "✅ PASS"
        status_color = "green"
    else:
        status = "❌ FAIL"
        status_color = "red"
    
    # 결과 테이블 생성
    table = Table(title=f"Query: {query[:50]}...", show_header=True)
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", width=60)
    
    table.add_row("Status", f"[{status_color}]{status}[/{status_color}]")
    table.add_row("Query Type", query_type)
    table.add_row("Expected Route", expected_route)
    table.add_row("Current Node", current_node)
    
    # 메타데이터 정보
    metadata = result.get("metadata", {})
    if "query_classification" in metadata:
        classification = metadata["query_classification"]
        table.add_row("Confidence", f"{classification.get('confidence', 0):.2f}")
        table.add_row("Reasoning", classification.get("reasoning", "")[:100])
    
    # enhanced_query가 있으면 표시
    if "enhanced_query" in result:
        table.add_row("Enhanced Query", result["enhanced_query"][:100])
    
    # 최종 답변 또는 에러
    if "final_answer" in result:
        table.add_row("Response", result["final_answer"][:200] + "...")
    elif "error" in result:
        table.add_row("Error", f"[red]{result['error']}[/red]")
    
    console.print(table)
    console.print()
    
    return status == "✅ PASS"


async def test_simple_queries(workflow: MVPWorkflowGraph, test_case: Dict):
    """Simple 쿼리 테스트"""
    print_test_header(test_case["category"], test_case["color"])
    
    results = []
    for query in test_case["queries"]:
        console.print(f"[cyan]Testing:[/cyan] {query}")
        
        try:
            # 워크플로우 실행 (첫 노드만 실행하고 확인)
            config = {"recursion_limit": 5}  # 빠른 테스트를 위해 제한
            
            # 스트리밍으로 첫 몇 개 노드만 실행
            events = []
            for event in workflow.stream(query, config=config):
                events.append(event)
                # query_router와 direct_response 노드까지만 실행
                if len(events) >= 2:
                    break
            
            # 모든 이벤트에서 상태 추출 및 병합
            if events:
                merged_state = {}
                for event in events:
                    for node_name, state in event.items():
                        # 각 노드의 상태를 병합
                        merged_state.update(state)
                
                # 결과 출력
                passed = print_query_result(query, merged_state, test_case["expected_route"])
                results.append(passed)
            else:
                console.print(f"[red]No events received for query: {query}[/red]")
                results.append(False)
                
        except Exception as e:
            console.print(f"[red]Error testing query '{query}': {str(e)}[/red]")
            results.append(False)
    
    return results


async def test_rag_queries(workflow: MVPWorkflowGraph, test_case: Dict):
    """RAG required 쿼리 테스트"""
    print_test_header(test_case["category"], test_case["color"])
    
    results = []
    for query in test_case["queries"]:
        console.print(f"[cyan]Testing:[/cyan] {query}")
        
        try:
            # 워크플로우 실행 (planning 노드까지만)
            config = {"recursion_limit": 5}
            
            events = []
            for event in workflow.stream(query, config=config):
                events.append(event)
                # query_router와 planning 노드까지만 실행
                if len(events) >= 2:
                    break
            
            # 마지막 이벤트에서 상태 추출
            if events:
                # 모든 이벤트의 상태를 병합
                merged_state = {}
                for event in events:
                    for node_name, state in event.items():
                        merged_state.update(state)
                
                # 결과 출력
                passed = print_query_result(query, merged_state, test_case["expected_route"])
                results.append(passed)
            else:
                console.print(f"[red]No events received for query: {query}[/red]")
                results.append(False)
                
        except Exception as e:
            console.print(f"[red]Error testing query '{query}': {str(e)}[/red]")
            results.append(False)
    
    return results


async def test_history_queries(workflow: MVPWorkflowGraph, test_case: Dict):
    """History required 쿼리 테스트"""
    print_test_header(test_case["category"], test_case["color"])
    
    results = []
    for query_pair in test_case["queries"]:
        first_query, follow_up = query_pair
        console.print(f"[cyan]Testing:[/cyan]")
        console.print(f"  First: {first_query}")
        console.print(f"  Follow-up: {follow_up}")
        
        try:
            # 첫 번째 쿼리 실행 (컨텍스트 생성)
            config = {"recursion_limit": 5}
            
            # 대화 히스토리를 시뮬레이션
            initial_state = {
                "query": follow_up,
                "messages": [
                    HumanMessage(content=first_query),
                    AIMessage(content=f"Here's information about: {first_query}")
                ],
                "workflow_status": "started",
                "metadata": {}
            }
            
            events = []
            for event in workflow.app.stream(initial_state, config=config):
                events.append(event)
                # query_router와 context_enhancement 노드까지만
                if len(events) >= 2:
                    break
            
            # 상태 병합
            if events:
                merged_state = {}
                for event in events:
                    for node_name, state in event.items():
                        merged_state.update(state)
                
                # 결과 출력
                passed = print_query_result(follow_up, merged_state, test_case["expected_route"])
                results.append(passed)
            else:
                console.print(f"[red]No events received[/red]")
                results.append(False)
                
        except Exception as e:
            console.print(f"[red]Error testing query pair: {str(e)}[/red]")
            results.append(False)
    
    return results


async def main():
    """메인 테스트 함수"""
    console.print("\n[bold cyan]Query Routing Test Suite[/bold cyan]")
    console.print(f"[dim]Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")
    
    # 워크플로우 생성
    console.print("[yellow]Initializing workflow...[/yellow]")
    workflow = MVPWorkflowGraph()
    
    # Query Routing 활성화 확인
    if not workflow.enable_routing:
        console.print("[red]❌ Query Routing is DISABLED![/red]")
        console.print("Please set ENABLE_QUERY_ROUTING=true in .env file")
        return
    
    console.print("[green]✅ Query Routing is ENABLED[/green]\n")
    
    # 전체 결과 저장
    all_results = {}
    
    # 각 카테고리별 테스트 실행
    for test_case in TEST_CASES:
        category = test_case["category"]
        
        if category == "simple":
            results = await test_simple_queries(workflow, test_case)
        elif category == "rag_required":
            results = await test_rag_queries(workflow, test_case)
        elif category == "history_required":
            results = await test_history_queries(workflow, test_case)
        else:
            continue
        
        all_results[category] = results
    
    # 최종 결과 요약
    console.print("\n[bold cyan]Test Summary[/bold cyan]")
    console.print("="*60)
    
    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Category", style="cyan", width=20)
    summary_table.add_column("Total", justify="center", width=10)
    summary_table.add_column("Passed", justify="center", width=10)
    summary_table.add_column("Failed", justify="center", width=10)
    summary_table.add_column("Success Rate", justify="center", width=15)
    
    total_tests = 0
    total_passed = 0
    
    for category, results in all_results.items():
        passed = sum(results)
        total = len(results)
        total_tests += total
        total_passed += passed
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        # 색상 결정
        if success_rate >= 80:
            rate_color = "green"
        elif success_rate >= 60:
            rate_color = "yellow"
        else:
            rate_color = "red"
        
        summary_table.add_row(
            category.upper(),
            str(total),
            f"[green]{passed}[/green]",
            f"[red]{total - passed}[/red]",
            f"[{rate_color}]{success_rate:.1f}%[/{rate_color}]"
        )
    
    # 전체 결과
    overall_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    summary_table.add_row(
        "[bold]OVERALL[/bold]",
        f"[bold]{total_tests}[/bold]",
        f"[bold green]{total_passed}[/bold green]",
        f"[bold red]{total_tests - total_passed}[/bold red]",
        f"[bold]{'%.1f' % overall_rate}%[/bold]"
    )
    
    console.print(summary_table)
    
    # 최종 판정
    console.print("\n" + "="*60)
    if overall_rate >= 80:
        console.print("[bold green]✅ TEST SUITE PASSED[/bold green]")
    else:
        console.print("[bold red]❌ TEST SUITE FAILED[/bold red]")
    
    console.print(f"\n[dim]Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())