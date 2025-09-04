#!/usr/bin/env python3
"""
Debug script for testing '똑딱이 문서에 대해 알려줘' query
"""

import sys
import json
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

console = Console()


def check_ddokddak_in_database():
    """데이터베이스에서 '똑딱이' 관련 문서 확인"""
    console.print("\n[bold yellow]1. Database Check[/bold yellow]")
    console.print("=" * 60)
    
    try:
        conn = psycopg.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "pgvector_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            row_factory=dict_row
        )
        
        with conn.cursor() as cur:
            # 1. '똑딱이' entity type 문서 수
            cur.execute("""
                SELECT COUNT(*) as count
                FROM mvp_ddu_documents
                WHERE entity->>'type' = '똑딱이'
            """)
            ddokddak_count = cur.fetchone()['count']
            console.print(f"🔍 Documents with '똑딱이' entity type: [bold red]{ddokddak_count}[/bold red]")
            
            # 2. '똑딱이' 키워드를 포함한 문서
            cur.execute("""
                SELECT COUNT(*) as count
                FROM mvp_ddu_documents
                WHERE page_content ILIKE '%똑딱이%' 
                   OR contextualize_text ILIKE '%똑딱이%'
                   OR translation_text ILIKE '%똑딱이%'
            """)
            keyword_count = cur.fetchone()['count']
            console.print(f"🔍 Documents containing '똑딱이' keyword: [bold red]{keyword_count}[/bold red]")
            
            # 3. 전체 entity types
            cur.execute("""
                SELECT DISTINCT entity->>'type' as entity_type, COUNT(*) as count
                FROM mvp_ddu_documents
                WHERE entity IS NOT NULL
                AND entity->>'type' IS NOT NULL
                GROUP BY entity->>'type'
                ORDER BY count DESC
            """)
            
            entity_types = cur.fetchall()
            if entity_types:
                table = Table(title="Available Entity Types")
                table.add_column("Entity Type", style="cyan")
                table.add_column("Count", justify="right", style="green")
                
                for row in entity_types:
                    table.add_row(row['entity_type'], str(row['count']))
                
                console.print(table)
            
        conn.close()
        return ddokddak_count > 0
        
    except Exception as e:
        console.print(f"[red]❌ Database check failed: {e}[/red]")
        return False


def test_query_with_enhanced_logging():
    """'똑딱이 문서에 대해 알려줘' 쿼리 테스트 with enhanced logging"""
    console.print("\n[bold yellow]2. Query Execution Test[/bold yellow]")
    console.print("=" * 60)
    
    query = "똑딱이 문서에 대해 알려줘"
    console.print(f"📝 Query: '[bold]{query}[/bold]'")
    
    try:
        workflow = MVPWorkflowGraph()
        result = workflow.run(query)
        
        # 1. Basic Status
        console.print("\n[bold cyan]Workflow Status:[/bold cyan]")
        console.print(f"  Status: {result.get('workflow_status', 'unknown')}")
        console.print(f"  Error: {result.get('error', 'None')}")
        
        # 2. Subtasks Analysis
        subtasks = result.get('subtasks', [])
        if subtasks:
            console.print(f"\n[bold cyan]Subtasks ({len(subtasks)}):[/bold cyan]")
            for i, subtask in enumerate(subtasks, 1):
                console.print(f"  {i}. {subtask.get('description', 'N/A')}")
                console.print(f"     Priority: {subtask.get('priority', 'N/A')}")
                console.print(f"     Language: {subtask.get('expected_language', 'N/A')}")
        
        # 3. Metadata Analysis
        metadata = result.get('metadata', {})
        console.print("\n[bold cyan]Metadata Analysis:[/bold cyan]")
        
        # Check each subtask's metadata
        for key in metadata:
            if key.startswith('subtask_'):
                subtask_meta = metadata[key]
                console.print(f"\n  [bold]{key}:[/bold]")
                
                # Query variations
                variations = subtask_meta.get('query_variations', [])
                if variations:
                    console.print(f"    Query Variations: {len(variations)}")
                
                # Entity extraction
                entity_type = subtask_meta.get('entity_type')
                console.print(f"    Entity Type Extracted: [yellow]{entity_type}[/yellow]")
                
                # Filter applied
                filter_applied = subtask_meta.get('filter_applied')
                if filter_applied:
                    console.print(f"    Filter Applied: {json.dumps(filter_applied, ensure_ascii=False)}")
                else:
                    console.print(f"    Filter Applied: [red]None[/red]")
                
                # Documents retrieved
                docs = subtask_meta.get('documents', [])
                console.print(f"    Documents Retrieved: {len(docs)}")
        
        # 4. Documents Analysis
        documents = result.get('documents', [])
        console.print(f"\n[bold cyan]Total Documents Retrieved: {len(documents)}[/bold cyan]")
        
        # Group documents by entity type
        entity_types = {}
        for doc in documents:
            entity = doc.metadata.get('entity')
            if entity and isinstance(entity, dict):
                entity_type = entity.get('type', 'unknown')
                if entity_type not in entity_types:
                    entity_types[entity_type] = []
                entity_types[entity_type].append(doc)
        
        if entity_types:
            console.print("\n[bold cyan]Documents by Entity Type:[/bold cyan]")
            for entity_type, docs in entity_types.items():
                console.print(f"  {entity_type}: {len(docs)} documents")
                
                # Show sample for '똑딱이' type
                if entity_type == '똑딱이' and docs:
                    console.print(f"\n  [bold green]Sample '똑딱이' Documents:[/bold green]")
                    for i, doc in enumerate(docs[:3], 1):
                        entity = doc.metadata['entity']
                        console.print(f"    {i}. Category: {doc.metadata.get('category')}")
                        console.print(f"       Title: {entity.get('title', 'N/A')}")
                        if entity.get('keywords'):
                            console.print(f"       Keywords: {', '.join(entity['keywords'][:3])}...")
        
        # 5. Final Answer Analysis
        final_answer = result.get('final_answer', '')
        if final_answer:
            console.print("\n[bold cyan]Final Answer Analysis:[/bold cyan]")
            console.print(f"  Answer Length: {len(final_answer)} chars")
            
            # Check if answer mentions '똑딱이'
            ddokddak_mentions = final_answer.count('똑딱이')
            ppt_mentions = final_answer.count('PPT')
            embedded_mentions = final_answer.count('삽입')
            
            console.print(f"  '똑딱이' mentions: [yellow]{ddokddak_mentions}[/yellow]")
            console.print(f"  'PPT' mentions: [yellow]{ppt_mentions}[/yellow]")
            console.print(f"  '삽입' mentions: [yellow]{embedded_mentions}[/yellow]")
            
            # Show first 500 chars of answer
            console.print("\n  [bold]Answer Preview (first 500 chars):[/bold]")
            preview = final_answer[:500] + "..." if len(final_answer) > 500 else final_answer
            console.print(f"  {preview}")
            
            # Check if answer is about cars (wrong content)
            car_keywords = ['자동차', '차량', '엔진', '안전벨트', '제작결함', '사고기록']
            car_mentions = sum(final_answer.count(kw) for kw in car_keywords)
            
            if car_mentions > 0:
                console.print(f"\n  [bold red]⚠️ Warning: Answer contains {car_mentions} car-related keywords![/bold red]")
                console.print("  This suggests the system is not finding '똑딱이' documents correctly.")
        
        # 6. Synthesis Metadata
        if 'synthesis' in metadata:
            synthesis_meta = metadata['synthesis']
            console.print("\n[bold cyan]Synthesis Metadata:[/bold cyan]")
            console.print(f"  Confidence: {synthesis_meta.get('confidence', 0)}")
            console.print(f"  Sources Used: {len(synthesis_meta.get('sources', []))}")
            console.print(f"  Key Points: {len(synthesis_meta.get('key_points', []))}")
        
        return result
        
    except Exception as e:
        console.print(f"[red]❌ Query test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def analyze_issues():
    """분석된 문제점 정리"""
    console.print("\n[bold yellow]3. Issue Analysis[/bold yellow]")
    console.print("=" * 60)
    
    issues = []
    
    # Check if '똑딱이' entities exist in DB
    has_ddokddak = check_ddokddak_in_database()
    
    if not has_ddokddak:
        issues.append({
            "issue": "No '똑딱이' entities in database",
            "impact": "System cannot retrieve '똑딱이' documents",
            "solution": "Run transplant_ddokddak_entity.py to add '똑딱이' entities"
        })
    
    # Run test query
    result = test_query_with_enhanced_logging()
    
    if result:
        final_answer = result.get('final_answer', '')
        
        # Check if answer is about wrong topic
        if '자동차' in final_answer or '안전벨트' in final_answer:
            issues.append({
                "issue": "Answer contains car-related content instead of '똑딱이' information",
                "impact": "Users get wrong information",
                "solution": "Ensure entity filter is properly applied and fallback behavior is correct"
            })
        
        # Check if '똑딱이' is mentioned
        if '똑딱이' not in final_answer:
            issues.append({
                "issue": "Answer doesn't mention '똑딱이' at all",
                "impact": "Answer is not relevant to the query",
                "solution": "Check if query router is correctly identifying the query type"
            })
        
        # Check document retrieval
        documents = result.get('documents', [])
        ddokddak_docs = [d for d in documents if d.metadata.get('entity', {}).get('type') == '똑딱이']
        
        if len(ddokddak_docs) == 0 and len(documents) > 0:
            issues.append({
                "issue": "Retrieved documents but none have '똑딱이' entity type",
                "impact": "System is falling back to general search",
                "solution": "Check entity filter generation and application"
            })
    
    # Display issues
    if issues:
        console.print("\n[bold red]Issues Found:[/bold red]")
        for i, issue in enumerate(issues, 1):
            console.print(f"\n{i}. [bold]{issue['issue']}[/bold]")
            console.print(f"   Impact: {issue['impact']}")
            console.print(f"   Solution: [green]{issue['solution']}[/green]")
    else:
        console.print("\n[bold green]No major issues found![/bold green]")
    
    return issues


def main():
    """메인 실행"""
    console.print("\n" + "=" * 80)
    console.print("[bold magenta]🔍 '똑딱이 문서에 대해 알려줘' Query Debug Tool[/bold magenta]")
    console.print("=" * 80)
    
    # Analyze issues
    issues = analyze_issues()
    
    # Improvement plan
    console.print("\n[bold yellow]4. Improvement Plan[/bold yellow]")
    console.print("=" * 60)
    
    if issues:
        console.print("\n[bold]Priority Actions:[/bold]")
        console.print("1. [red]IMMEDIATE[/red]: Add '똑딱이' entities to database")
        console.print("   Run: python scripts/transplant_ddokddak_entity.py")
        
        console.print("\n2. [yellow]SHORT-TERM[/yellow]: Enhance entity filter handling")
        console.print("   - Add fallback message when no '똑딱이' documents found")
        console.print("   - Improve query router to better identify '똑딱이' queries")
        
        console.print("\n3. [green]LONG-TERM[/green]: System improvements")
        console.print("   - Add explicit '똑딱이' explanation in system prompts")
        console.print("   - Create dedicated '똑딱이' search strategy")
        console.print("   - Add monitoring for entity type coverage")
    else:
        console.print("[green]System is working correctly for '똑딱이' queries![/green]")


if __name__ == "__main__":
    main()