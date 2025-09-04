#!/usr/bin/env python3
"""
Analyze entity types and their relationships with DDU categories
"""

import psycopg
from psycopg.rows import dict_row
import json
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()


def analyze_entity_types():
    """Analyze entity types in the database"""
    
    # Database connection
    conn_params = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "dbname": os.getenv("DB_NAME", "multimodal_rag"),
        "user": os.getenv("DB_USER", "multimodal_user"),
        "password": os.getenv("DB_PASSWORD", "multimodal_pass123"),
    }
    
    print("=" * 80)
    print("ENTITY TYPE ANALYSIS")
    print("=" * 80)
    
    with psycopg.connect(**conn_params, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            
            # 1. Check all unique entity types
            print("\n1. UNIQUE ENTITY TYPES")
            print("-" * 40)
            
            cur.execute("""
                SELECT DISTINCT entity->>'type' as entity_type, COUNT(*) as count
                FROM mvp_ddu_documents
                WHERE entity IS NOT NULL
                AND entity->>'type' IS NOT NULL
                GROUP BY entity->>'type'
                ORDER BY count DESC
            """)
            
            entity_types = cur.fetchall()
            
            if entity_types:
                print(f"Found {len(entity_types)} unique entity types:\n")
                for et in entity_types:
                    print(f"  • {et['entity_type']}: {et['count']} documents")
            else:
                print("  No entity types found in database")
            
            # 2. Categories with entities
            print("\n2. CATEGORIES WITH ENTITIES")
            print("-" * 40)
            
            cur.execute("""
                SELECT category, 
                       COUNT(*) as total_docs,
                       COUNT(CASE WHEN entity IS NOT NULL 
                                  AND entity::text != 'null' 
                                  AND entity::text != '{}' 
                                  AND entity->>'type' IS NOT NULL THEN 1 END) as docs_with_entity,
                       ROUND(100.0 * COUNT(CASE WHEN entity IS NOT NULL 
                                                AND entity::text != 'null' 
                                                AND entity::text != '{}' 
                                                AND entity->>'type' IS NOT NULL THEN 1 END) / COUNT(*), 1) as entity_percentage
                FROM mvp_ddu_documents
                GROUP BY category
                ORDER BY docs_with_entity DESC
            """)
            
            category_entity_stats = cur.fetchall()
            
            print(f"{'Category':<15} | {'Total':<8} | {'With Entity':<12} | {'Percentage'}")
            print("-" * 60)
            for stat in category_entity_stats:
                print(f"{stat['category']:<15} | {stat['total_docs']:<8} | {stat['docs_with_entity']:<12} | {stat['entity_percentage']}%")
            
            # 3. Category-Entity Type Mapping
            print("\n3. CATEGORY TO ENTITY TYPE MAPPING")
            print("-" * 40)
            
            cur.execute("""
                SELECT category, entity->>'type' as entity_type, COUNT(*) as count
                FROM mvp_ddu_documents
                WHERE entity IS NOT NULL
                AND entity->>'type' IS NOT NULL
                GROUP BY category, entity->>'type'
                ORDER BY category, count DESC
            """)
            
            mappings = cur.fetchall()
            
            # Group by category
            category_type_map = defaultdict(list)
            for mapping in mappings:
                category_type_map[mapping['category']].append({
                    'type': mapping['entity_type'],
                    'count': mapping['count']
                })
            
            for category, types in category_type_map.items():
                print(f"\n  {category}:")
                for type_info in types:
                    print(f"    → entity type '{type_info['type']}': {type_info['count']} documents")
            
            # 4. Sample entities by type
            print("\n4. SAMPLE ENTITIES BY TYPE")
            print("-" * 40)
            
            # Get unique entity types
            cur.execute("""
                SELECT DISTINCT entity->>'type' as entity_type
                FROM mvp_ddu_documents
                WHERE entity IS NOT NULL
                AND entity->>'type' IS NOT NULL
            """)
            
            unique_types = [row['entity_type'] for row in cur.fetchall()]
            
            for entity_type in unique_types:
                print(f"\n  Entity Type: '{entity_type}'")
                print("  " + "-" * 35)
                
                # Get a sample document for this type
                cur.execute("""
                    SELECT id, category, entity, page_content
                    FROM mvp_ddu_documents
                    WHERE entity->>'type' = %(type)s
                    LIMIT 1
                """, {"type": entity_type})
                
                sample = cur.fetchone()
                if sample:
                    print(f"    Document ID: {sample['id']}")
                    print(f"    Category: {sample['category']}")
                    print(f"    Entity structure:")
                    entity_str = json.dumps(sample['entity'], ensure_ascii=False, indent=6)
                    # Limit entity display
                    if len(entity_str) > 500:
                        entity_str = entity_str[:500] + "..."
                    print(entity_str)
            
            # 5. Categories without entities
            print("\n5. CATEGORIES WITHOUT ENTITIES")
            print("-" * 40)
            
            cur.execute("""
                SELECT category, COUNT(*) as count
                FROM mvp_ddu_documents
                WHERE entity IS NULL
                OR entity::text = 'null'
                OR entity::text = '{}'
                GROUP BY category
                ORDER BY count DESC
            """)
            
            no_entity_categories = cur.fetchall()
            
            for cat in no_entity_categories:
                print(f"  • {cat['category']}: {cat['count']} documents without entity")
            
            # 6. Entity field analysis
            print("\n6. ENTITY FIELD ANALYSIS")
            print("-" * 40)
            
            # Get all unique keys from entities
            cur.execute("""
                SELECT DISTINCT jsonb_object_keys(entity) as entity_key
                FROM mvp_ddu_documents
                WHERE entity IS NOT NULL
                AND entity::text != 'null'
                AND entity::text != '{}'
                ORDER BY entity_key
            """)
            
            entity_keys = cur.fetchall()
            
            print(f"Found {len(entity_keys)} unique fields in entity objects:\n")
            for key in entity_keys:
                print(f"  • {key['entity_key']}")
                
                # Count how many documents have this key
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM mvp_ddu_documents
                    WHERE entity ? %(key)s
                """, {"key": key['entity_key']})
                
                count = cur.fetchone()['count']
                print(f"    Used in {count} documents")
            
            # 7. Source-based entity distribution
            print("\n7. ENTITY DISTRIBUTION BY SOURCE")
            print("-" * 40)
            
            cur.execute("""
                SELECT source,
                       COUNT(*) as total_docs,
                       COUNT(CASE WHEN entity IS NOT NULL 
                                  AND entity::text != 'null' 
                                  AND entity::text != '{}' 
                                  AND entity->>'type' IS NOT NULL THEN 1 END) as docs_with_entity,
                       ROUND(100.0 * COUNT(CASE WHEN entity IS NOT NULL 
                                                AND entity::text != 'null' 
                                                AND entity::text != '{}' 
                                                AND entity->>'type' IS NOT NULL THEN 1 END) / COUNT(*), 1) as entity_percentage
                FROM mvp_ddu_documents
                GROUP BY source
                ORDER BY source
            """)
            
            source_entity_stats = cur.fetchall()
            
            for stat in source_entity_stats:
                source_name = stat['source'].split('/')[-1] if stat['source'] else 'Unknown'
                print(f"\n  Source: {source_name}")
                print(f"    Total documents: {stat['total_docs']}")
                print(f"    Documents with entity: {stat['docs_with_entity']} ({stat['entity_percentage']}%)")
                
                # Get category breakdown for this source
                cur.execute("""
                    SELECT category, 
                           COUNT(*) as total,
                           COUNT(CASE WHEN entity IS NOT NULL 
                                      AND entity::text != 'null' 
                                      AND entity::text != '{}' 
                                      AND entity->>'type' IS NOT NULL THEN 1 END) as with_entity
                    FROM mvp_ddu_documents
                    WHERE source = %(source)s
                    GROUP BY category
                    ORDER BY category
                """, {"source": stat['source']})
                
                category_breakdown = cur.fetchall()
                print(f"    Category breakdown:")
                for cat in category_breakdown:
                    if cat['with_entity'] > 0:
                        print(f"      • {cat['category']}: {cat['with_entity']}/{cat['total']} have entity")
            
            # 8. Check if entity type always matches category
            print("\n8. ENTITY TYPE vs CATEGORY CONSISTENCY")
            print("-" * 40)
            
            # Check for mismatches
            cur.execute("""
                SELECT category, entity->>'type' as entity_type, COUNT(*) as count
                FROM mvp_ddu_documents
                WHERE entity IS NOT NULL
                AND entity->>'type' IS NOT NULL
                AND (
                    (category = 'table' AND entity->>'type' != 'table') OR
                    (category = 'figure' AND entity->>'type' != 'image') OR
                    (category != 'table' AND category != 'figure' AND entity->>'type' IS NOT NULL)
                )
                GROUP BY category, entity->>'type'
            """)
            
            mismatches = cur.fetchall()
            
            if mismatches:
                print("Found inconsistencies:")
                for mm in mismatches:
                    print(f"  Category '{mm['category']}' has entity type '{mm['entity_type']}': {mm['count']} documents")
            else:
                print("  ✅ Entity types are consistent with categories")


if __name__ == "__main__":
    analyze_entity_types()