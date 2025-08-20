"""
Entity 필터 전용 테스트
entity 필터만 사용했을 때의 검색 동작 확인
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich import print as rprint

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from ingest.database import DatabaseManager
from retrieval.search_filter import MVPSearchFilter

# .env 파일 로드
load_dotenv()

console = Console()


async def test_entity_filter():
    """Entity 필터만 사용한 검색 테스트"""
    
    # 데이터베이스 매니저 초기화
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    console.print("\n[bold cyan]Entity Filter Only Test[/bold cyan]")
    console.print("=" * 60)
    
    # 다양한 entity 필터 테스트 케이스
    test_cases = [
        {
            "filter": MVPSearchFilter(entity={"type": "image"}),
            "description": "Only entity type=image filter (no category filter)"
        },
        {
            "filter": MVPSearchFilter(entity={"type": "table"}),
            "description": "Only entity type=table filter"
        },
        {
            "filter": MVPSearchFilter(entity={"keywords": ["안전벨트"]}),
            "description": "Only entity keywords filter"
        },
        {
            "filter": MVPSearchFilter(entity={"title": "안전"}),
            "description": "Only entity title filter"
        },
        {
            "filter": MVPSearchFilter(
                categories=["figure"],
                entity={"type": "image"}
            ),
            "description": "Combined: figure category + image entity"
        },
        {
            "filter": MVPSearchFilter(entity={}),
            "description": "Empty entity filter (should return all with entity)"
        }
    ]
    
    for test in test_cases:
        console.print(f"\n[yellow]Test: {test['description']}[/yellow]")
        
        # asyncpg용 SQL 생성
        where_clause, params = test["filter"].to_sql_where_asyncpg()
        
        console.print(f"  SQL WHERE: {where_clause}")
        console.print(f"  Parameters: {params}")
        
        async with db_manager.pool.acquire() as conn:
            # 검색 실행
            results = await conn.fetch(f"""
                SELECT id, source, page, category, entity
                FROM mvp_ddu_documents
                WHERE {where_clause}
                ORDER BY id
                LIMIT 20
            """, *params)
            
            console.print(f"  Results: [green]{len(results)} documents found[/green]")
            
            if results:
                # 카테고리 분포
                categories = {}
                entity_types = {}
                
                for r in results:
                    # 카테고리 집계
                    cat = r['category']
                    categories[cat] = categories.get(cat, 0) + 1
                    
                    # Entity 타입 집계
                    if r['entity']:
                        try:
                            entity_data = json.loads(r['entity']) if isinstance(r['entity'], str) else r['entity']
                            if entity_data and 'type' in entity_data:
                                etype = entity_data['type']
                                entity_types[etype] = entity_types.get(etype, 0) + 1
                        except:
                            pass
                
                console.print(f"  Categories: {categories}")
                console.print(f"  Entity types: {entity_types}")
                
                # 상위 3개 결과 상세 출력
                console.print("\n  [cyan]Sample Results:[/cyan]")
                for i, r in enumerate(results[:3], 1):
                    console.print(f"\n  Result {i}:")
                    console.print(f"    ID: {r['id']}")
                    console.print(f"    Category: {r['category']}")
                    console.print(f"    Page: {r['page']}")
                    
                    if r['entity']:
                        try:
                            entity_data = json.loads(r['entity']) if isinstance(r['entity'], str) else r['entity']
                            console.print(f"    Entity Type: {entity_data.get('type', 'N/A')}")
                            if entity_data.get('title'):
                                console.print(f"    Entity Title: {entity_data.get('title')[:50]}...")
                            if entity_data.get('keywords'):
                                console.print(f"    Entity Keywords: {entity_data.get('keywords')[:3]}")
                        except Exception as e:
                            console.print(f"    Entity Error: {e}")
            else:
                console.print("  [red]No results found![/red]")
        
        console.print("-" * 60)
    
    # Entity가 있는 모든 문서 통계
    console.print("\n[bold]Overall Entity Statistics:[/bold]")
    
    async with db_manager.pool.acquire() as conn:
        # Entity가 null이 아닌 모든 문서
        total_with_entity = await conn.fetchval("""
            SELECT COUNT(*) FROM mvp_ddu_documents
            WHERE entity IS NOT NULL
        """)
        
        # Entity type별 통계
        entity_stats = await conn.fetch("""
            SELECT entity->>'type' as entity_type, COUNT(*) as count
            FROM mvp_ddu_documents
            WHERE entity IS NOT NULL
            GROUP BY entity->>'type'
            ORDER BY count DESC
        """)
        
        console.print(f"  Total documents with entity: {total_with_entity}")
        console.print("\n  Entity type distribution:")
        for stat in entity_stats:
            console.print(f"    {stat['entity_type'] or 'NULL'}: {stat['count']} documents")
    
    await db_manager.close()


async def main():
    """메인 실행 함수"""
    await test_entity_filter()
    console.print("\n[green]✅ Test completed[/green]")


if __name__ == "__main__":
    # 환경 변수 체크
    required_env = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [var for var in required_env if not os.getenv(var)]
    
    if missing:
        console.print(f"[red]❌ Missing environment variables: {', '.join(missing)}[/red]")
        sys.exit(1)
    
    asyncio.run(main())