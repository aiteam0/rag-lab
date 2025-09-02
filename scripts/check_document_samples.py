#!/usr/bin/env python3
"""
Check document samples from database to understand the data structure
"""

import psycopg
from psycopg.rows import dict_row
import json
import os
from dotenv import load_dotenv

load_dotenv()


def check_document_samples():
    """Check various document samples from database"""
    
    # Database connection
    conn_params = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "dbname": os.getenv("DB_NAME", "multimodal_rag"),
        "user": os.getenv("DB_USER", "multimodal_user"),
        "password": os.getenv("DB_PASSWORD", "multimodal_pass123"),
    }
    
    print("=" * 80)
    print("DOCUMENT SAMPLES BY CATEGORY")
    print("=" * 80)
    
    with psycopg.connect(**conn_params, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            
            # Get one sample per category
            categories = ['paragraph', 'heading1', 'table', 'figure', 'list', 'caption']
            
            for category in categories:
                print(f"\n{'='*60}")
                print(f"CATEGORY: {category.upper()}")
                print('='*60)
                
                # Get a sample with all fields populated if possible
                cur.execute("""
                    SELECT *
                    FROM mvp_ddu_documents
                    WHERE category = %(category)s
                    AND page_content IS NOT NULL
                    ORDER BY 
                        CASE WHEN entity IS NOT NULL THEN 0 ELSE 1 END,
                        CASE WHEN caption IS NOT NULL THEN 0 ELSE 1 END,
                        CASE WHEN contextualize_text IS NOT NULL THEN 0 ELSE 1 END
                    LIMIT 1
                """, {"category": category})
                
                doc = cur.fetchone()
                
                if doc:
                    print(f"\n📄 Document ID: {doc['id']}")
                    print(f"📁 Source: {doc['source']}")
                    print(f"📃 Page: {doc['page']}")
                    print(f"🏷️ Category: {doc['category']}")
                    
                    print(f"\n📝 Page Content ({len(doc['page_content'] or '')} chars):")
                    if doc['page_content']:
                        print(f"   {doc['page_content'][:200]}...")
                    
                    print(f"\n🔄 Translation Text ({len(doc['translation_text'] or '')} chars):")
                    if doc['translation_text']:
                        print(f"   {doc['translation_text'][:200]}...")
                    
                    print(f"\n🎯 Contextualize Text ({len(doc['contextualize_text'] or '')} chars):")
                    if doc['contextualize_text']:
                        print(f"   {doc['contextualize_text'][:200]}...")
                    
                    print(f"\n💬 Caption ({len(doc['caption'] or '')} chars):")
                    if doc['caption']:
                        print(f"   {doc['caption'][:200]}...")
                    
                    print(f"\n🔷 Entity (JSONB):")
                    if doc['entity']:
                        print(f"   {json.dumps(doc['entity'], ensure_ascii=False, indent=2)[:500]}...")
                    else:
                        print("   None")
                    
                    print(f"\n🖼️ Image Path:")
                    print(f"   {doc['image_path'] or 'None'}")
                    
                    print(f"\n👤 Human Feedback:")
                    print(f"   {doc['human_feedback'] or 'Empty string (default)'}")
                    
                    # Check embeddings
                    print(f"\n🔢 Embeddings:")
                    if doc['embedding_korean']:
                        emb_str = doc['embedding_korean']
                        print(f"   Korean: {emb_str[:50]}... (vector)")
                    if doc['embedding_english']:
                        emb_str = doc['embedding_english']
                        print(f"   English: {emb_str[:50]}... (vector)")
            
            # Get documents with entities
            print(f"\n{'='*60}")
            print("DOCUMENTS WITH ENTITIES")
            print('='*60)
            
            cur.execute("""
                SELECT id, category, entity
                FROM mvp_ddu_documents
                WHERE entity IS NOT NULL
                AND entity::text != 'null'
                AND entity::text != '{}'
                LIMIT 5
            """)
            
            entity_docs = cur.fetchall()
            for doc in entity_docs:
                print(f"\nDoc {doc['id']} ({doc['category']}):")
                print(json.dumps(doc['entity'], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    check_document_samples()