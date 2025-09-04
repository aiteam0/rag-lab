#!/usr/bin/env python3
"""
Quick test to verify the DDUFilterGeneration fix for '똑딱이' entity type
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.subtask_executor import SubtaskExecutorNode, QueryExtraction
from rich.console import Console
from rich import print as rprint
import os
from dotenv import load_dotenv
import json

# 환경변수 로드
load_dotenv()

console = Console()

def test_ddokddak_filter_generation():
    """Test if '똑딱이' entity filter is generated correctly"""
    console.print("\n[bold yellow]Testing '똑딱이' Entity Filter Generation[/bold yellow]")
    console.print("=" * 60)
    
    try:
        # SubtaskExecutorNode 초기화
        executor = SubtaskExecutorNode()
        
        # Metadata 가져오기
        metadata = executor._get_metadata_sync()
        console.print(f"✅ Metadata loaded with entity types: {metadata.get('entity_types', [])}")
        
        # Test queries
        test_queries = [
            "똑딱이 문서에 대해 알려줘",
            "PPT에 있는 참조문서 보여줘",
            "삽입객체 문서 목록",
            "똑딱이 타입 문서의 내용",
        ]
        
        for query in test_queries:
            console.print(f"\n[bold cyan]Testing query: '{query}'[/bold cyan]")
            
            # Step 1: Extract query info
            extraction = executor._extract_query_info(query, metadata)
            console.print(f"  Entity type extracted: [yellow]{extraction.entity_type}[/yellow]")
            
            # Step 2: Generate filter
            filter_obj = executor._generate_filter(query, extraction, metadata)
            
            if filter_obj and filter_obj.entity:
                entity_filter = filter_obj.entity
                console.print(f"  ✅ Entity filter generated: [green]{json.dumps(entity_filter, ensure_ascii=False)}[/green]")
                
                if entity_filter.get('type') == '똑딱이':
                    console.print("  [bold green]SUCCESS: '똑딱이' filter created correctly![/bold green]")
                else:
                    console.print(f"  [red]WARNING: Wrong entity type: {entity_filter.get('type')}[/red]")
            else:
                console.print("  [red]❌ No entity filter generated![/red]")
                if filter_obj:
                    console.print(f"  Other filters: categories={filter_obj.categories}, pages={filter_obj.pages}")
        
        console.print("\n[bold green]✅ Test completed![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ddokddak_filter_generation()
    sys.exit(0 if success else 1)