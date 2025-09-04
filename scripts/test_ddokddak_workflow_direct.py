#!/usr/bin/env python3
"""
Direct workflow test for '똑딱이' query processing
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import json

console = Console()

def test_ddokddak_workflow():
    """Test '똑딱이' query through the workflow"""
    console.print("\n[bold magenta]Testing '똑딱이' Query Workflow[/bold magenta]")
    console.print("=" * 60)
    
    workflow = MVPWorkflowGraph()
    query = "똑딱이 문서 목록을 보여줘"
    
    console.print(f"🔍 Query: [bold]'{query}'[/bold]\n")
    
    try:
        # Run workflow
        result = workflow.run(query)
        
        # Check results
        console.print("[bold cyan]Workflow Results:[/bold cyan]")
        console.print(f"  Status: {result.get('workflow_status', 'unknown')}")
        
        # Check subtasks
        subtasks = result.get('subtasks', [])
        if subtasks:
            console.print(f"\n[bold]Subtasks ({len(subtasks)}):[/bold]")
            for i, subtask in enumerate(subtasks, 1):
                console.print(f"  {i}. {subtask.get('description', subtask.get('query', 'N/A'))}")
        
        # Check metadata for filters
        metadata = result.get('metadata', {})
        console.print(f"\n[bold]Filter Analysis:[/bold]")
        
        found_ddokddak_filter = False
        for key in metadata:
            if key.startswith('subtask_'):
                subtask_meta = metadata[key]
                filter_applied = subtask_meta.get('filter_applied')
                if filter_applied and 'entity' in filter_applied:
                    entity = filter_applied['entity']
                    console.print(f"  {key}: entity = {json.dumps(entity, ensure_ascii=False)}")
                    if entity.get('type') == '똑딱이':
                        console.print(f"    [green]✅ '똑딱이' filter found![/green]")
                        found_ddokddak_filter = True
        
        if not found_ddokddak_filter:
            console.print("  [red]❌ No '똑딱이' filter found in any subtask![/red]")
        
        # Check documents
        documents = result.get('documents', [])
        console.print(f"\n[bold]Documents Retrieved: {len(documents)}[/bold]")
        
        # Count by entity type
        entity_counts = {}
        for doc in documents:
            if doc.metadata.get('entity'):
                entity_type = doc.metadata['entity'].get('type', 'unknown')
                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        if entity_counts:
            table = Table(title="Documents by Entity Type")
            table.add_column("Entity Type", style="cyan")
            table.add_column("Count", justify="right", style="green")
            
            for entity_type, count in entity_counts.items():
                table.add_row(entity_type, str(count))
            
            console.print(table)
            
            if '똑딱이' in entity_counts:
                console.print(f"\n[bold green]✅ SUCCESS: Retrieved {entity_counts['똑딱이']} '똑딱이' documents![/bold green]")
                
                # Show sample
                ddokddak_docs = [d for d in documents if d.metadata.get('entity', {}).get('type') == '똑딱이']
                if ddokddak_docs:
                    console.print("\n[bold]Sample '똑딱이' Documents:[/bold]")
                    for i, doc in enumerate(ddokddak_docs[:3], 1):
                        entity = doc.metadata['entity']
                        console.print(f"  {i}. {entity.get('title', 'N/A')}")
                        if entity.get('keywords'):
                            console.print(f"     Keywords: {', '.join(entity['keywords'][:3])}")
            else:
                console.print("\n[red]❌ No '똑딱이' documents found![/red]")
        else:
            console.print("  [yellow]No entity information in retrieved documents[/yellow]")
        
        # Check final answer
        if result.get('final_answer'):
            answer = result['final_answer']
            if '똑딱이' in answer or 'PPT' in answer or '삽입' in answer:
                console.print("\n[green]✅ Final answer mentions '똑딱이' related content[/green]")
            else:
                console.print("\n[yellow]⚠️ Final answer doesn't mention '똑딱이'[/yellow]")
            
            # Show preview
            preview = answer[:300] + "..." if len(answer) > 300 else answer
            console.print(f"\nAnswer Preview:\n{preview}")
        
        return found_ddokddak_filter
        
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ddokddak_workflow()
    sys.exit(0 if success else 1)