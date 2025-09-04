#!/usr/bin/env python3
"""Database inspection script for understanding current data state and schema."""

import os
import sys
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

console = Console()

def get_db_connection():
    """Create database connection."""
    return psycopg.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        row_factory=dict_row
    )

def inspect_schema():
    """Inspect database schema."""
    console.print("\n[bold cyan]📊 Database Schema Inspection[/bold cyan]\n")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get column information
            cur.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (os.getenv('DB_TABLE_NAME'),))
            
            columns = cur.fetchall()
            
            table = Table(title="Table Schema: mvp_ddu_documents", box=box.ROUNDED)
            table.add_column("Column", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta")
            table.add_column("Max Length", style="yellow")
            table.add_column("Nullable", style="green")
            table.add_column("Default", style="blue")
            
            for col in columns:
                table.add_row(
                    col['column_name'],
                    col['data_type'],
                    str(col['character_maximum_length']) if col['character_maximum_length'] else "-",
                    col['is_nullable'],
                    str(col['column_default'])[:30] if col['column_default'] else "-"
                )
            
            console.print(table)
            
            # Get index information
            cur.execute("""
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = %s
            """, (os.getenv('DB_TABLE_NAME'),))
            
            indexes = cur.fetchall()
            
            console.print("\n[bold cyan]🔍 Indexes[/bold cyan]")
            for idx in indexes:
                console.print(f"  • [yellow]{idx['indexname']}[/yellow]: {idx['indexdef'][:100]}...")

def analyze_data():
    """Analyze current data in database."""
    console.print("\n[bold cyan]📈 Data Analysis[/bold cyan]\n")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Total document count
            cur.execute(f"SELECT COUNT(*) as count FROM {os.getenv('DB_TABLE_NAME')}")
            total_docs = cur.fetchone()['count']
            console.print(f"[green]Total Documents:[/green] {total_docs}")
            
            # Category distribution
            cur.execute(f"""
                SELECT 
                    category,
                    COUNT(*) as count
                FROM {os.getenv('DB_TABLE_NAME')}
                GROUP BY category
                ORDER BY count DESC
            """)
            categories = cur.fetchall()
            
            console.print("\n[bold]Category Distribution:[/bold]")
            cat_table = Table(box=box.SIMPLE)
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Count", style="yellow", justify="right")
            cat_table.add_column("Percentage", style="green", justify="right")
            
            for cat in categories:
                percentage = (cat['count'] / total_docs * 100) if total_docs > 0 else 0
                cat_table.add_row(
                    cat['category'],
                    str(cat['count']),
                    f"{percentage:.1f}%"
                )
            console.print(cat_table)
            
            # Source distribution
            cur.execute(f"""
                SELECT 
                    source,
                    COUNT(*) as count,
                    MIN(page) as min_page,
                    MAX(page) as max_page
                FROM {os.getenv('DB_TABLE_NAME')}
                GROUP BY source
            """)
            sources = cur.fetchall()
            
            console.print("\n[bold]Source Documents:[/bold]")
            for src in sources:
                console.print(f"  • [yellow]{src['source']}[/yellow]: {src['count']} documents (pages {src['min_page']}-{src['max_page']})")
            
            # Entity analysis
            cur.execute(f"""
                SELECT COUNT(*) as count
                FROM {os.getenv('DB_TABLE_NAME')}
                WHERE entity IS NOT NULL 
                AND entity::text != 'null'
                AND entity::text != '{{}}'
            """)
            entity_count = cur.fetchone()['count']
            console.print(f"\n[green]Documents with Entity data:[/green] {entity_count}")
            
            # Human feedback analysis
            cur.execute(f"""
                SELECT COUNT(*) as count
                FROM {os.getenv('DB_TABLE_NAME')}
                WHERE human_feedback IS NOT NULL 
                AND human_feedback != ''
            """)
            feedback_count = cur.fetchone()['count']
            console.print(f"[green]Documents with Human Feedback:[/green] {feedback_count}")
            
            # Sample entity structure
            cur.execute(f"""
                SELECT 
                    id,
                    category,
                    entity
                FROM {os.getenv('DB_TABLE_NAME')}
                WHERE entity IS NOT NULL 
                AND entity::text != 'null'
                AND entity::text != '{{}}'
                LIMIT 2
            """)
            sample_entities = cur.fetchall()
            
            if sample_entities:
                console.print("\n[bold]Sample Entity Structure:[/bold]")
                for ent in sample_entities:
                    console.print(f"\n[yellow]ID:[/yellow] {ent['id']} ([cyan]{ent['category']}[/cyan])")
                    console.print(json.dumps(ent['entity'], indent=2, ensure_ascii=False))
            
            # Embedding status
            cur.execute(f"""
                SELECT 
                    COUNT(*) FILTER (WHERE embedding_english IS NOT NULL) as with_embedding,
                    COUNT(*) FILTER (WHERE embedding_english IS NULL) as without_embedding,
                    COUNT(*) FILTER (WHERE embedding_korean IS NOT NULL) as with_embedding_ko,
                    COUNT(*) FILTER (WHERE embedding_korean IS NULL) as without_embedding_ko
                FROM {os.getenv('DB_TABLE_NAME')}
            """)
            embed_stats = cur.fetchone()
            
            console.print("\n[bold]Embedding Status:[/bold]")
            console.print(f"  • English embeddings: {embed_stats['with_embedding']} / {total_docs}")
            console.print(f"  • Korean embeddings: {embed_stats['with_embedding_ko']} / {total_docs}")
            
            # Sample documents
            cur.execute(f"""
                SELECT 
                    id,
                    source,
                    page,
                    category,
                    SUBSTRING(page_content, 1, 200) as content_preview
                FROM {os.getenv('DB_TABLE_NAME')}
                WHERE category IN ('heading1', 'paragraph')
                LIMIT 3
            """)
            samples = cur.fetchall()
            
            console.print("\n[bold]Sample Documents:[/bold]")
            for sample in samples:
                console.print(f"\n[yellow]ID:[/yellow] {sample['id']}")
                console.print(f"[cyan]Category:[/cyan] {sample['category']} | [cyan]Page:[/cyan] {sample['page']}")
                console.print(f"[cyan]Source:[/cyan] {sample['source']}")
                console.print(f"[dim]{sample['content_preview'][:100]}...[/dim]")

def inspect_workflow_state():
    """Analyze workflow state structure."""
    console.print("\n[bold cyan]🔄 Workflow State Analysis[/bold cyan]\n")
    
    # Read the state definition
    state_file = project_root / "workflow" / "state.py"
    if state_file.exists():
        with open(state_file) as f:
            content = f.read()
            
        # Extract state fields
        import re
        fields = re.findall(r'(\w+):\s*(?:Optional\[)?(\w+(?:\[.*?\])?)', content)
        
        console.print(f"[green]Total State Fields:[/green] {len(fields)}")
        
        # Categorize fields
        categories = {
            'Query Processing': ['query', 'enhanced_query', 'query_type', 'language'],
            'Planning': ['subtasks', 'current_subtask', 'execution_plan'],
            'Execution': ['multi_queries', 'search_filters', 'subtask_results'],
            'Documents': ['documents', 'filtered_documents', 'ranked_documents'],
            'Validation': ['hallucination_checks', 'answer_grades', 'is_grounded'],
            'Output': ['final_answer', 'synthesis', 'structured_output'],
            'Control Flow': ['current_node', 'next_node', 'should_continue'],
            'Metadata': ['errors', 'warnings', 'metrics', 'debug_info']
        }
        
        for category, keywords in categories.items():
            matching = [f for f in fields if any(k in f[0].lower() for k in keywords)]
            if matching:
                console.print(f"\n[bold]{category}:[/bold]")
                for field_name, field_type in matching[:5]:  # Show first 5
                    console.print(f"  • {field_name}: {field_type}")

if __name__ == "__main__":
    try:
        console.print(Panel.fit(
            "[bold magenta]Multimodal RAG Database & Workflow Inspector[/bold magenta]",
            border_style="bright_blue"
        ))
        
        inspect_schema()
        analyze_data()
        inspect_workflow_state()
        
        console.print("\n[bold green]✅ Inspection Complete![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()