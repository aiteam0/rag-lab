#!/usr/bin/env python3
"""
Check if 똑딱이 documents exist in database
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from ingest.database import DatabaseManager
import json

def check_ddokddak_documents():
    """Check for 똑딱이 documents in database"""
    
    db = DatabaseManager()
    db.initialize()  # Initialize the connection pool
    
    # 1. Count all documents with entity type = '똑딱이'
    print("\n1. Checking documents with entity->>'type' = '똑딱이'...")
    
    query1 = """
    SELECT COUNT(*) as count
    FROM mvp_ddu_documents
    WHERE entity->>'type' = '똑딱이'
    """
    
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query1)
            result = cur.fetchone()
            count = result[0] if result else 0
            print(f"   Found {count} documents with entity type '똑딱이'")
    
    # 2. Get sample 똑딱이 documents
    if count > 0:
        print("\n2. Sample 똑딱이 documents:")
        query2 = """
        SELECT id, source, page, category, 
               SUBSTRING(page_content, 1, 100) as content_preview,
               entity
        FROM mvp_ddu_documents
        WHERE entity->>'type' = '똑딱이'
        LIMIT 5
        """
        
        with db.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query2)
                results = cur.fetchall()
                
                for i, (id, source, page, category, content, entity_json) in enumerate(results, 1):
                    print(f"\n   [{i}] ID: {id}")
                    print(f"       Source: {source}")
                    print(f"       Page: {page}, Category: {category}")
                    print(f"       Content: {content}...")
                    if entity_json:
                        entity = json.loads(entity_json) if isinstance(entity_json, str) else entity_json
                        print(f"       Entity: {entity}")
    
    # 3. Check documents with category in entity search categories
    print("\n3. Checking documents by category with entity filter...")
    categories = ["figure", "table", "paragraph", "heading1", "heading2", "heading3"]
    
    query3 = """
    SELECT category, COUNT(*) as count
    FROM mvp_ddu_documents
    WHERE category = ANY(%(categories)s) 
      AND entity->>'type' = '똑딱이'
    GROUP BY category
    """
    
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query3, {'categories': categories})
            results = cur.fetchall()
            
            if results:
                print("   Documents with entity type '똑딱이' by category:")
                for category, count in results:
                    print(f"     {category}: {count}")
            else:
                print("   No documents found with those categories and entity type '똑딱이'")
    
    # 4. Check what entity types exist
    print("\n4. All unique entity types in database:")
    query4 = """
    SELECT DISTINCT entity->>'type' as entity_type, COUNT(*) as count
    FROM mvp_ddu_documents
    WHERE entity IS NOT NULL
    GROUP BY entity->>'type'
    ORDER BY count DESC
    """
    
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query4)
            results = cur.fetchall()
            
            for entity_type, count in results:
                print(f"   {entity_type}: {count} documents")

if __name__ == "__main__":
    check_ddokddak_documents()