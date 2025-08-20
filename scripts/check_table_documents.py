#!/usr/bin/env python3
"""
Check if there are actual table documents in the database
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_table_documents():
    """Check table documents in DB"""
    
    # DB connection
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    try:
        # Count documents by category
        print("\n📊 Document count by category:")
        print("-" * 40)
        
        categories = await conn.fetch("""
            SELECT category, COUNT(*) as count
            FROM mvp_ddu_documents
            GROUP BY category
            ORDER BY count DESC
        """)
        
        for row in categories:
            print(f"  {row['category']:15} : {row['count']:5} documents")
        
        # Check table documents specifically
        print("\n📋 Table documents analysis:")
        print("-" * 40)
        
        table_count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM mvp_ddu_documents 
            WHERE category = 'table'
        """)
        
        print(f"  Total table documents: {table_count}")
        
        # Check table documents with entity type
        table_with_entity = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM mvp_ddu_documents 
            WHERE category = 'table' 
            AND entity IS NOT NULL
            AND entity->>'type' = 'table'
        """)
        
        print(f"  Tables with entity type 'table': {table_with_entity}")
        
        # Sample table documents
        print("\n📄 Sample table documents (first 3):")
        print("-" * 40)
        
        tables = await conn.fetch("""
            SELECT id, source, page, caption, 
                   substring(page_content, 1, 100) as content_preview
            FROM mvp_ddu_documents 
            WHERE category = 'table'
            LIMIT 3
        """)
        
        for i, row in enumerate(tables, 1):
            print(f"\n  Table {i}:")
            print(f"    ID: {row['id']}")
            print(f"    Source: {row['source']}")
            print(f"    Page: {row['page']}")
            print(f"    Caption: {row['caption'] or 'No caption'}")
            print(f"    Content: {row['content_preview']}...")
        
        # Check if keyword search would find tables
        print("\n🔍 Keyword search test for '표':")
        print("-" * 40)
        
        keyword_results = await conn.fetch("""
            SELECT COUNT(*) as count
            FROM mvp_ddu_documents
            WHERE category = 'table'
            AND (
                page_content ILIKE '%표%' OR
                translation_text ILIKE '%표%' OR
                contextualize_text ILIKE '%표%'
            )
        """)
        
        if keyword_results:
            print(f"  Tables containing '표': {keyword_results[0]['count']}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Checking Table Documents in Database")
    print("=" * 60)
    
    asyncio.run(check_table_documents())
    
    print("\n" + "=" * 60)
    print("✅ Analysis complete")
    print("=" * 60)