#!/usr/bin/env python3
"""
DirectResponseNode가 모든 쿼리에 대해 상세한 DB 정보를 포함하는지 검증
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow.nodes.direct_response import DirectResponseNode
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import re

console = Console()

def extract_db_info(response: str) -> Dict[str, Any]:
    """응답에서 DB 정보 추출"""
    info = {
        "has_total_docs": False,
        "has_sources": False,
        "has_categories": False,
        "has_language": False,
        "has_system_type": False,
        "total_docs_num": None,
        "source_count": None,
        "category_count": None
    }
    
    # 숫자 패턴 추출
    total_docs_patterns = [
        r'(\d+)\s*(?:개의\s*)?문서',
        r'(\d+)\s*documents?',
        r'Total Documents[:\s]+(\d+)',
        r'총\s*(\d+)개'
    ]
    
    for pattern in total_docs_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            info["has_total_docs"] = True
            info["total_docs_num"] = int(match.group(1))
            break
    
    # 소스 정보 확인
    if any(word in response.lower() for word in ['source', '소스', 'file', '파일', '.pdf', '.pkl']):
        info["has_sources"] = True
        source_match = re.search(r'(\d+)\s*(?:files?|개의?\s*파일)', response, re.IGNORECASE)
        if source_match:
            info["source_count"] = int(source_match.group(1))
    
    # 카테고리 정보 확인
    if any(word in response.lower() for word in ['category', 'categories', '카테고리', 'type', '타입', 'paragraph', 'heading', 'figure', 'table']):
        info["has_categories"] = True
        cat_match = re.search(r'(\d+)\s*(?:different\s*)?(?:types?|categories|카테고리)', response, re.IGNORECASE)
        if cat_match:
            info["category_count"] = int(cat_match.group(1))
    
    # 언어 지원 정보 확인
    if any(word in response.lower() for word in ['korean', 'english', '한국어', '영어', 'embedding', '임베딩', 'language']):
        info["has_language"] = True
    
    # 시스템 타입 정보 확인
    if any(word in response.lower() for word in ['rag', 'retrieval', 'multimodal', 'hybrid', 'search']):
        info["has_system_type"] = True
    
    return info

def test_various_queries():
    """다양한 쿼리에 대해 DB 정보 포함 테스트"""
    
    # DirectResponseNode 초기화
    console.print("\n[bold cyan]Initializing DirectResponseNode...[/bold cyan]")
    direct_node = DirectResponseNode()
    
    # 테스트 쿼리들
    test_queries = [
        {"query": "안녕하세요", "type": "greeting", "lang": "ko"},
        {"query": "Hello", "type": "greeting", "lang": "en"},
        {"query": "오늘 날씨가 어때?", "type": "weather", "lang": "ko"},
        {"query": "What is 2+2?", "type": "math", "lang": "en"},
        {"query": "파이썬이 뭐야?", "type": "knowledge", "lang": "ko"},
        {"query": "Tell me a joke", "type": "entertainment", "lang": "en"},
        {"query": "너가 관리하는 문서는 뭐야?", "type": "system_query", "lang": "ko"},
        {"query": "How many documents do you have?", "type": "system_query", "lang": "en"}
    ]
    
    # 결과 테이블
    table = Table(title="DB Information Inclusion Test Results", box=box.ROUNDED)
    table.add_column("Query", style="cyan", width=25)
    table.add_column("Type", style="magenta", width=12)
    table.add_column("Total", style="green", width=8, justify="center")
    table.add_column("Sources", style="green", width=8, justify="center")
    table.add_column("Categories", style="green", width=10, justify="center")
    table.add_column("Language", style="green", width=8, justify="center")
    table.add_column("System", style="green", width=8, justify="center")
    table.add_column("Score", style="bold yellow", width=8, justify="center")
    
    all_scores = []
    
    for i, test_case in enumerate(test_queries, 1):
        console.print(f"\n[bold blue]Test {i}/{len(test_queries)}:[/bold blue] {test_case['query']}")
        
        # State 생성
        state = {
            "query": test_case["query"],
            "messages": [],
            "metadata": {}
        }
        
        try:
            # DirectResponseNode 실행
            result = direct_node(state)
            response = result.get("final_answer", "")
            
            # DB 정보 추출
            db_info = extract_db_info(response)
            
            # 점수 계산 (5개 항목 각 20점)
            score = sum([
                20 if db_info["has_total_docs"] else 0,
                20 if db_info["has_sources"] else 0,
                20 if db_info["has_categories"] else 0,
                20 if db_info["has_language"] else 0,
                20 if db_info["has_system_type"] else 0
            ])
            all_scores.append(score)
            
            # 테이블에 추가
            table.add_row(
                test_case["query"][:25],
                test_case["type"],
                "✅" if db_info["has_total_docs"] else "❌",
                "✅" if db_info["has_sources"] else "❌",
                "✅" if db_info["has_categories"] else "❌",
                "✅" if db_info["has_language"] else "❌",
                "✅" if db_info["has_system_type"] else "❌",
                f"{score}%"
            )
            
            # 응답 샘플 표시
            console.print(Panel(
                response[:400] + ("..." if len(response) > 400 else ""),
                title=f"Response Sample - {test_case['type']} ({test_case['lang']})",
                border_style="dim"
            ))
            
            # 추출된 정보 표시
            if db_info["total_docs_num"]:
                console.print(f"  [dim]• Extracted: {db_info['total_docs_num']} total documents[/dim]")
            if db_info["source_count"]:
                console.print(f"  [dim]• Extracted: {db_info['source_count']} sources[/dim]")
            if db_info["category_count"]:
                console.print(f"  [dim]• Extracted: {db_info['category_count']} categories[/dim]")
                
        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            table.add_row(
                test_case["query"][:25],
                test_case["type"],
                "⚠️", "⚠️", "⚠️", "⚠️", "⚠️",
                "ERROR"
            )
    
    # 결과 테이블 출력
    console.print("\n")
    console.print(table)
    
    # 요약 통계
    if all_scores:
        avg_score = sum(all_scores) / len(all_scores)
        console.print(f"\n[bold yellow]Summary Statistics:[/bold yellow]")
        console.print(f"• Average Score: {avg_score:.1f}%")
        console.print(f"• Perfect Scores (100%): {all_scores.count(100)}/{len(all_scores)}")
        console.print(f"• Failed (0%): {all_scores.count(0)}/{len(all_scores)}")
        
        if avg_score >= 80:
            console.print("\n[bold green]✅ SUCCESS: DB information is consistently included![/bold green]")
        elif avg_score >= 60:
            console.print("\n[bold yellow]⚠️ PARTIAL: DB information is sometimes included[/bold yellow]")
        else:
            console.print("\n[bold red]❌ FAILURE: DB information is rarely included[/bold red]")

def main():
    """메인 실행 함수"""
    console.print("\n[bold magenta]═══════════════════════════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]     Testing DirectResponse DB Information Inclusion           [/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════════════════════════[/bold magenta]")
    
    console.print("\n[dim]This test verifies that DirectResponseNode includes detailed[/dim]")
    console.print("[dim]database information in ALL responses, regardless of query type.[/dim]")
    
    test_various_queries()
    
    console.print("\n[bold cyan]Test completed![/bold cyan]\n")

if __name__ == "__main__":
    main()