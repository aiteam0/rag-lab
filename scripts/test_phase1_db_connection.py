#!/usr/bin/env python3
"""
Test database connection and table existence
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def test_db_connection():
    """Test database connection and check table"""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    # Get connection parameters
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "multimodal_rag"),
        "user": os.getenv("DB_USER", "multimodal_user"),
        "password": os.getenv("DB_PASSWORD", "multimodal_pass123")
    }
    
    print("\n1. Connection parameters:")
    for key, value in db_config.items():
        if key == "password":
            print(f"   {key}: {'*' * len(value)}")
        else:
            print(f"   {key}: {value}")
    
    try:
        # Try to connect
        print("\n2. Attempting to connect to database...")
        conn = await asyncpg.connect(**db_config)
        print("   ✅ Connected successfully!")
        
        try:
            # Check if table exists
            print("\n3. Checking table 'mvp_ddu_documents'...")
            result = await conn.fetchval(
                """SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mvp_ddu_documents'
                )"""
            )
            
            if result:
                print("   ✅ Table exists!")
                
                # Count documents
                count = await conn.fetchval("SELECT COUNT(*) FROM mvp_ddu_documents")
                print(f"   📊 Document count: {count}")
                
                # Check sample categories
                categories = await conn.fetch(
                    "SELECT DISTINCT category FROM mvp_ddu_documents LIMIT 5"
                )
                if categories:
                    print("   📋 Sample categories:")
                    for row in categories:
                        print(f"      - {row['category']}")
            else:
                print("   ❌ Table 'mvp_ddu_documents' does not exist!")
                print("   💡 Run: uv run scripts/1_setup_database.py")
                return False
                
        finally:
            await conn.close()
            print("\n4. Connection closed.")
            
        return True
        
    except asyncpg.PostgresConnectionError as e:
        print(f"   ❌ Connection failed: {e}")
        print("\n   Possible issues:")
        print("   - PostgreSQL service not running")
        print("   - Database 'multimodal_rag' does not exist")
        print("   - Wrong credentials")
        print("\n   💡 Try running:")
        print("   - sudo service postgresql start")
        print("   - createdb -h localhost -U postgres multimodal_rag")
        return False
        
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_db_connection())
    exit(0 if success else 1)