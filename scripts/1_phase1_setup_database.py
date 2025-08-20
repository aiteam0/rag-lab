"""
Database Setup Script for MVP RAG System
초기 데이터베이스 설정 및 테이블 생성
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from ingest.database import DatabaseManager

# .env 파일 로드
load_dotenv()


async def setup_database():
    """MVP 데이터베이스 초기화"""
    
    print("=" * 60)
    print("MVP RAG System - Database Setup")
    print("=" * 60)
    
    # 데이터베이스 매니저 초기화
    db_manager = DatabaseManager()
    
    try:
        # 연결 풀 초기화
        print("\n📌 Initializing database connection...")
        await db_manager.initialize()
        print("✅ Connection pool created")
        
        # 데이터베이스 스키마 설정
        print("\n📌 Setting up database schema...")
        await db_manager.setup_database()
        
        # 테이블 통계 조회
        print("\n📊 Database Statistics:")
        stats = await db_manager.get_table_stats()
        print(f"  - Total Documents: {stats['total_documents']}")
        print(f"  - Categories: {len(stats['categories'])} types")
        print(f"  - Sources: {len(stats['sources'])} files")
        
        if stats['page_range']['min'] and stats['page_range']['max']:
            print(f"  - Page Range: {stats['page_range']['min']} - {stats['page_range']['max']}")
        
        # 테이블 초기화 옵션
        if stats['total_documents'] > 0:
            print(f"\n⚠️  Table contains {stats['total_documents']} documents")
            response = input("Clear existing data? (y/N): ")
            if response.lower() == 'y':
                await db_manager.clear_table()
                print("✅ Table data cleared")
        
        print("\n✅ Database setup completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during database setup: {e}")
        raise
    
    finally:
        # 연결 종료
        await db_manager.close()
        print("\n📌 Database connection closed")


async def test_connection():
    """데이터베이스 연결 테스트"""
    
    print("\n" + "=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    db_manager = DatabaseManager()
    
    try:
        await db_manager.initialize()
        
        # 간단한 쿼리 실행
        async with db_manager.pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            print(f"\n✅ PostgreSQL Version: {version}")
            
            # pgvector 확장 확인
            extensions = await conn.fetch("""
                SELECT extname, extversion 
                FROM pg_extension 
                WHERE extname = 'vector'
            """)
            
            if extensions:
                for ext in extensions:
                    print(f"✅ Extension '{ext['extname']}' version {ext['extversion']} is installed")
            else:
                print("⚠️  pgvector extension not found")
        
        print("\n✅ Connection test successful!")
        
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        raise
    
    finally:
        await db_manager.close()


def main():
    """메인 실행 함수"""
    
    print("\nMVP RAG System - Database Setup Utility")
    print("=" * 60)
    print("\nOptions:")
    print("1. Setup database (create tables and indexes)")
    print("2. Test connection only")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ")
    
    if choice == "1":
        asyncio.run(setup_database())
    elif choice == "2":
        asyncio.run(test_connection())
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid option")


if __name__ == "__main__":
    # 환경 변수 체크
    required_env = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [var for var in required_env if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please create a .env file with the required variables")
        print("\nExample .env file:")
        print("DB_HOST=localhost")
        print("DB_PORT=5432")
        print("DB_NAME=multimodal_rag_mvp")
        print("DB_USER=your_user")
        print("DB_PASSWORD=your_password")
        sys.exit(1)
    
    main()