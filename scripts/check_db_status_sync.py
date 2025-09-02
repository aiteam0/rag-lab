#!/usr/bin/env python3
"""Check database schema and data status (sync version using psycopg3)"""

import psycopg
from psycopg.rows import dict_row
import json
from typing import Dict, Any
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


def check_database_status():
    """Check database schema and data status"""
    
    # Database connection parameters
    conn_params = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "dbname": os.getenv("DB_NAME", "multimodal_rag"),
        "user": os.getenv("DB_USER", "multimodal_user"),
        "password": os.getenv("DB_PASSWORD", "multimodal_pass123"),
    }
    
    print("=" * 80)
    print("DATABASE STATUS CHECK (SYNC)")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Connecting to: {conn_params['host']}:{conn_params['port']}/{conn_params['dbname']}")
    print()
    
    try:
        # Create connection
        with psycopg.connect(**conn_params, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                
                # 1. Check if table exists
                print("1. TABLE EXISTENCE CHECK")
                print("-" * 40)
                table_name = os.getenv("DB_TABLE_NAME", "mvp_ddu_documents")
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %(table_name)s
                    )
                    """,
                    {"table_name": table_name}
                )
                table_exists = cur.fetchone()['exists']
                print(f"Table '{table_name}' exists: {table_exists}")
                print()
                
                if table_exists:
                    # 2. Get table schema
                    print("2. TABLE SCHEMA")
                    print("-" * 40)
                    cur.execute(
                        """
                        SELECT 
                            column_name,
                            data_type,
                            character_maximum_length,
                            is_nullable,
                            column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'public' 
                        AND table_name = %(table_name)s
                        ORDER BY ordinal_position
                        """,
                        {"table_name": table_name}
                    )
                    columns = cur.fetchall()
                    
                    for col in columns:
                        col_type = col['data_type']
                        if col['character_maximum_length']:
                            col_type += f"({col['character_maximum_length']})"
                        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                        default = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
                        print(f"  {col['column_name']:<30} {col_type:<20} {nullable:<10} {default}")
                    print()
                    
                    # 3. Get indexes
                    print("3. INDEXES")
                    print("-" * 40)
                    cur.execute(
                        """
                        SELECT 
                            indexname,
                            indexdef
                        FROM pg_indexes
                        WHERE schemaname = 'public' 
                        AND tablename = %(table_name)s
                        """,
                        {"table_name": table_name}
                    )
                    indexes = cur.fetchall()
                    
                    for idx in indexes:
                        print(f"  {idx['indexname']}:")
                        print(f"    {idx['indexdef']}")
                    print()
                    
                    # 4. Data statistics
                    print("4. DATA STATISTICS")
                    print("-" * 40)
                    
                    # Total count
                    cur.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    total_count = cur.fetchone()['count']
                    print(f"  Total documents: {total_count:,}")
                    
                    # Category distribution
                    cur.execute(
                        f"""
                        SELECT 
                            category,
                            COUNT(*) as count
                        FROM {table_name}
                        GROUP BY category
                        ORDER BY count DESC
                        """
                    )
                    category_stats = cur.fetchall()
                    
                    if category_stats:
                        print("\n  Category Distribution:")
                        for stat in category_stats:
                            print(f"    {stat['category']:<20} {stat['count']:>8,} documents")
                    
                    # Source distribution
                    cur.execute(
                        f"""
                        SELECT 
                            source,
                            COUNT(*) as count
                        FROM {table_name}
                        GROUP BY source
                        ORDER BY count DESC
                        LIMIT 10
                        """
                    )
                    source_stats = cur.fetchall()
                    
                    if source_stats:
                        print("\n  Source Distribution (Top 10):")
                        for stat in source_stats:
                            source = stat['source'] or 'N/A'
                            # Truncate long paths
                            if len(source) > 50:
                                source = "..." + source[-47:]
                            print(f"    {source:<50} {stat['count']:>8,} documents")
                    
                    # Page distribution
                    cur.execute(
                        f"""
                        SELECT 
                            MIN(page) as min_page,
                            MAX(page) as max_page,
                            COUNT(DISTINCT page) as unique_pages
                        FROM {table_name}
                        WHERE page IS NOT NULL
                        """
                    )
                    page_stats = cur.fetchone()
                    
                    if page_stats and page_stats['min_page']:
                        print(f"\n  Page Range: {page_stats['min_page']} - {page_stats['max_page']} ({page_stats['unique_pages']} unique pages)")
                    
                    # Entity statistics
                    cur.execute(
                        f"""
                        SELECT COUNT(*) as count
                        FROM {table_name}
                        WHERE entity IS NOT NULL 
                        AND entity::text != 'null'
                        AND entity::text != '{{}}'
                        """
                    )
                    entity_count = cur.fetchone()['count']
                    print(f"\n  Documents with entities: {entity_count:,}")
                    
                    # Sample 5 documents
                    print("\n5. SAMPLE DATA (5 documents)")
                    print("-" * 40)
                    cur.execute(
                        f"""
                        SELECT 
                            id,
                            page_content,
                            source,
                            category,
                            page,
                            entity,
                            caption
                        FROM {table_name}
                        LIMIT 5
                        """
                    )
                    samples = cur.fetchall()
                    
                    for i, sample in enumerate(samples, 1):
                        print(f"\n  Document {i}:")
                        print(f"    ID: {sample['id']}")
                        content_preview = sample['page_content'][:100] if sample['page_content'] else 'N/A'
                        if len(sample['page_content'] or '') > 100:
                            content_preview += "..."
                        print(f"    Content: {content_preview}")
                        print(f"    Category: {sample['category']}")
                        print(f"    Page: {sample['page']}")
                        print(f"    Source: {sample['source']}")
                        if sample['caption']:
                            print(f"    Caption: {sample['caption'][:100]}")
                        if sample['entity']:
                            print(f"    Has Entity: Yes")
                    
                    # Check embedding dimension
                    print("\n6. EMBEDDING ANALYSIS")
                    print("-" * 40)
                    cur.execute(
                        f"""
                        SELECT embedding_korean
                        FROM {table_name}
                        WHERE embedding_korean IS NOT NULL
                        LIMIT 1
                        """
                    )
                    first_embedding_korean_row = cur.fetchone()
                    
                    cur.execute(
                        f"""
                        SELECT embedding_english
                        FROM {table_name}
                        WHERE embedding_english IS NOT NULL
                        LIMIT 1
                        """
                    )
                    first_embedding_english_row = cur.fetchone()
                    
                    if first_embedding_korean_row:
                        # Parse the embedding string
                        embedding_str = first_embedding_korean_row['embedding_korean']
                        if embedding_str.startswith('[') and embedding_str.endswith(']'):
                            embedding_values = embedding_str[1:-1].split(',')
                            print(f"  Korean embedding dimension: {len(embedding_values)}")
                        else:
                            print(f"  Korean embedding format unexpected")
                    else:
                        print(f"  No Korean embeddings found")
                        
                    if first_embedding_english_row:
                        # Parse the embedding string
                        embedding_str = first_embedding_english_row['embedding_english']
                        if embedding_str.startswith('[') and embedding_str.endswith(']'):
                            embedding_values = embedding_str[1:-1].split(',')
                            print(f"  English embedding dimension: {len(embedding_values)}")
                        else:
                            print(f"  English embedding format unexpected")
                    else:
                        print(f"  No English embeddings found")
                        
                    print(f"  Expected dimension: {os.getenv('OPENAI_EMBEDDING_DIMENSIONS', 1536)}")
                        
                else:
                    print("Table does not exist. Please run the setup script first.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_database_status()