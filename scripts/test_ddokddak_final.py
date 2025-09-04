#!/usr/bin/env python3
"""
Final test for '똑딱이' entity filter fix
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

def test_ddokddak_queries():
    """Test various '똑딱이' related queries"""
    console.print("\n[bold magenta]🧪 Testing '똑딱이' Entity Filter Fix[/bold magenta]")
    console.print("=" * 60)
    
    workflow = MVPWorkflowGraph()
    
    # Test queries
    test_queries = [
        "똑딱이 문서에 대해 알려줘",
        "똑딱이 문서의 정의",
        "PPT에 삽입된 참조문서 목록"
    ]
    
    all_passed = True
    
    for query in test_queries:
        console.print(f"\n[bold cyan]Testing Query: '{query}'[/bold cyan]")
        console.print("-" * 50)
        
        try:
            # Run workflow
            result = workflow.run(query)
            
            # Check workflow status
            status = result.get('workflow_status', 'unknown')
            console.print(f"  Workflow Status: [yellow]{status}[/yellow]")
            
            # Check metadata for filter
            metadata = result.get('metadata', {})
            filter_found = False
            ddokddak_filter = False
            
            for key in metadata:
                if key.startswith('subtask_'):
                    subtask_meta = metadata[key]
                    filter_applied = subtask_meta.get('filter_applied')
                    
                    if filter_applied:
                        filter_found = True
                        console.print(f"\n  [bold]Filter Applied:[/bold]")
                        
                        if 'entity' in filter_applied:
                            entity_filter = filter_applied['entity']
                            console.print(f"    Entity: {json.dumps(entity_filter, ensure_ascii=False)}")
                            
                            if entity_filter.get('type') == '똑딱이':
                                console.print("    [green]✅ '똑딱이' filter correctly generated![/green]")
                                ddokddak_filter = True
                            else:
                                console.print(f"    [red]❌ Wrong entity type: {entity_filter.get('type')}[/red]")
                        
                        if filter_applied.get('categories'):
                            console.print(f"    Categories: {filter_applied['categories']}")
                        
                        if filter_applied.get('pages'):
                            console.print(f"    Pages: {filter_applied['pages']}")
            
            if not filter_found:
                console.print("  [red]❌ No filter was generated![/red]")
                all_passed = False
            elif not ddokddak_filter:
                console.print("  [red]❌ Filter was generated but not for '똑딱이'![/red]")
                all_passed = False
            
            # Check retrieved documents
            documents = result.get('documents', [])
            console.print(f"\n  [bold]Documents Retrieved: {len(documents)}[/bold]")
            
            # Count by entity type
            entity_counts = {}
            for doc in documents:
                entity = doc.metadata.get('entity')
                if entity and isinstance(entity, dict):
                    entity_type = entity.get('type', 'unknown')
                    entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
            
            if entity_counts:
                console.print("  Entity Type Distribution:")
                for entity_type, count in entity_counts.items():
                    emoji = "✅" if entity_type == '똑딱이' else "⚠️"
                    console.print(f"    {emoji} {entity_type}: {count} documents")
                
                if '똑딱이' in entity_counts:
                    console.print(f"\n  [green]✅ Successfully retrieved {entity_counts['똑딱이']} '똑딱이' documents![/green]")
                    
                    # Show sample documents
                    ddokddak_docs = [d for d in documents if d.metadata.get('entity', {}).get('type') == '똑딱이']
                    if ddokddak_docs:
                        console.print("\n  [bold]Sample '똑딱이' Documents:[/bold]")
                        for i, doc in enumerate(ddokddak_docs[:3], 1):
                            entity = doc.metadata['entity']
                            console.print(f"    {i}. {entity.get('title', 'N/A')}")
                            if entity.get('keywords'):
                                console.print(f"       Keywords: {', '.join(entity['keywords'][:3])}")
                else:
                    console.print("\n  [red]❌ No '똑딱이' documents found in results![/red]")
                    all_passed = False
            else:
                console.print("  [yellow]⚠️ No entity information in retrieved documents[/yellow]")
            
            # Check final answer
            final_answer = result.get('final_answer', '')
            if final_answer:
                # Check if answer mentions PPT embedded docs (not car manual)
                car_keywords = ['안전벨트', '엔진 오일', '사고기록장치', '제작결함', 'GV80']
                ddokddak_keywords = ['PPT', '삽입', '참조문서', 'embedded', '똑딱이']
                
                car_mentions = sum(1 for kw in car_keywords if kw in final_answer)
                ddokddak_mentions = sum(1 for kw in ddokddak_keywords if kw in final_answer)
                
                console.print(f"\n  [bold]Answer Analysis:[/bold]")
                console.print(f"    Car manual keywords found: {car_mentions}")
                console.print(f"    PPT/embedded doc keywords found: {ddokddak_mentions}")
                
                if car_mentions > ddokddak_mentions:
                    console.print("    [red]❌ Answer contains car manual content (wrong)![/red]")
                    all_passed = False
                elif ddokddak_mentions > 0:
                    console.print("    [green]✅ Answer correctly mentions PPT embedded documents![/green]")
                else:
                    console.print("    [yellow]⚠️ Answer doesn't clearly indicate document type[/yellow]")
                
                # Show answer preview
                preview = final_answer[:200] + "..." if len(final_answer) > 200 else final_answer
                console.print(f"\n  Answer Preview: {preview}")
                
        except Exception as e:
            console.print(f"  [red]❌ Error: {e}[/red]")
            all_passed = False
    
    # Final verdict
    console.print("\n" + "=" * 60)
    if all_passed:
        console.print("[bold green]✅ ALL TESTS PASSED![/bold green]")
        console.print("\nThe '똑딱이' entity filter is working correctly!")
    else:
        console.print("[bold red]❌ SOME TESTS FAILED[/bold red]")
        console.print("\nThere are still issues with '똑딱이' entity filtering.")
    console.print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = test_ddokddak_queries()
    sys.exit(0 if success else 1)