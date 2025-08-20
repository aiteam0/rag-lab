#!/usr/bin/env python3
"""
Check available sources in database
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_sources():
    """Check unique sources in database"""
    # Database connection
    conn_string = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME')}"
    )
    
    conn = await asyncpg.connect(conn_string)
    
    try:
        # Get unique sources
        sources = await conn.fetch("""
            SELECT DISTINCT source, COUNT(*) as doc_count
            FROM mvp_ddu_documents
            GROUP BY source
            ORDER BY source
        """)
        
        print("\n=== Available Sources in Database ===")
        print(f"Total unique sources: {len(sources)}\n")
        
        for record in sources:
            source = record['source']
            count = record['doc_count']
            print(f"  - {source}: {count} documents")
        
        # Check if any source contains 'gv80' or 'GV80'
        print("\n=== Sources containing 'GV80' ===")
        gv80_sources = await conn.fetch("""
            SELECT DISTINCT source, COUNT(*) as doc_count
            FROM mvp_ddu_documents
            WHERE LOWER(source) LIKE '%gv80%'
            GROUP BY source
            ORDER BY source
        """)
        
        if gv80_sources:
            for record in gv80_sources:
                print(f"  - {record['source']}: {record['doc_count']} documents")
        else:
            print("  No sources containing 'GV80' found")
        
        # Get total document count
        total = await conn.fetchval("SELECT COUNT(*) FROM mvp_ddu_documents")
        print(f"\nTotal documents in database: {total}")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_sources())