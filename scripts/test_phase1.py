"""
Phase 1 Components Test Script
Verifies that all Phase 1 modules are working correctly
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

# .env 파일 로드
load_dotenv()


async def test_phase1_components():
    """Phase 1 구성 요소 테스트"""
    
    print("=" * 60)
    print("MVP RAG System - Phase 1 Components Test")
    print("=" * 60)
    
    results = {}
    
    # 1. Database Module Test
    print("\n📌 Testing Database Module...")
    try:
        from ingest.database import DatabaseManager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # 연결 테스트
        async with db_manager.pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            print(f"  ✅ PostgreSQL connected: {version[:30]}...")
        
        await db_manager.close()
        results['Database'] = "✅ PASS"
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        results['Database'] = "❌ FAIL"
    
    # 2. Models Module Test
    print("\n📌 Testing Models Module...")
    try:
        from ingest.models import DDUDocument, DDU_CATEGORIES
        
        # 테스트 문서 생성
        test_doc = DDUDocument(
            source="test.pdf",
            page=1,
            category="paragraph",
            page_content="테스트 콘텐츠",
            translation_text="Test content"
        )
        
        # 변환 테스트
        langchain_doc = test_doc.to_langchain_document()
        db_dict = test_doc.to_db_dict()
        
        print(f"  ✅ DDU Categories: {len(DDU_CATEGORIES)} types")
        print(f"  ✅ Document conversion successful")
        results['Models'] = "✅ PASS"
    except Exception as e:
        print(f"  ❌ Models test failed: {e}")
        results['Models'] = "❌ FAIL"
    
    # 3. Embeddings Module Test
    print("\n📌 Testing Embeddings Module...")
    try:
        from ingest.embeddings import DualLanguageEmbeddings
        
        embeddings = DualLanguageEmbeddings()
        
        # 테스트 임베딩 생성
        test_doc = {
            "page_content": "테스트",
            "translation_text": "test"
        }
        
        korean_emb, english_emb = await embeddings.embed_document(test_doc)
        
        print(f"  ✅ Korean embedding: {len(korean_emb) if korean_emb else 0} dims")
        print(f"  ✅ English embedding: {len(english_emb) if english_emb else 0} dims")
        results['Embeddings'] = "✅ PASS"
    except Exception as e:
        print(f"  ❌ Embeddings test failed: {e}")
        results['Embeddings'] = "❌ FAIL"
    
    # 4. Loader Module Test
    print("\n📌 Testing Loader Module...")
    try:
        from ingest.loader import DDUPickleLoader
        
        pickle_path = "/mnt/e/MyProject2/multimodal-rag-wsl-v2/data/gv80_owners_manual_TEST6P_documents.pkl"
        
        if os.path.exists(pickle_path):
            # 검증
            is_valid = DDUPickleLoader.validate_pickle_file(pickle_path)
            print(f"  ✅ Pickle validation: {is_valid}")
            
            if is_valid:
                loader = DDUPickleLoader(pickle_path)
                stats = loader.get_statistics()
                print(f"  ✅ Loaded {stats['total_documents']} documents")
            
            results['Loader'] = "✅ PASS"
        else:
            print(f"  ⚠️  Pickle file not found: {pickle_path}")
            results['Loader'] = "⚠️  SKIP"
    except Exception as e:
        print(f"  ❌ Loader test failed: {e}")
        results['Loader'] = "❌ FAIL"
    
    # 5. SearchFilter Module Test
    print("\n📌 Testing SearchFilter Module...")
    try:
        from retrieval.search_filter import MVPSearchFilter
        
        # 테스트 필터 생성
        test_filter = MVPSearchFilter(
            categories=["paragraph", "table"],
            pages=[1, 2, 3],
            caption="엔진"
        )
        
        # SQL 변환 테스트
        where_clause, params = test_filter.to_sql_where()
        
        print(f"  ✅ Filter created with {len(params)} parameters")
        print(f"  ✅ SQL WHERE clause generated")
        results['SearchFilter'] = "✅ PASS"
    except Exception as e:
        print(f"  ❌ SearchFilter test failed: {e}")
        results['SearchFilter'] = "❌ FAIL"
    
    # 6. HybridSearch Module Test
    print("\n📌 Testing HybridSearch Module...")
    try:
        from retrieval.hybrid_search import HybridSearch
        from kiwipiepy import Kiwi
        
        # Kiwi 테스트
        kiwi = Kiwi()
        test_text = "GV80의 엔진 성능은 어떻게 되나요?"
        result = kiwi.tokenize(test_text)
        
        print(f"  ✅ Kiwi tokenizer initialized")
        print(f"  ✅ Korean text tokenized: {len(result[0][0])} tokens")
        results['HybridSearch'] = "✅ PASS"
    except Exception as e:
        print(f"  ❌ HybridSearch test failed: {e}")
        results['HybridSearch'] = "❌ FAIL"
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for module, result in results.items():
        print(f"{module:15} {result}")
    
    # 전체 결과
    passed = sum(1 for r in results.values() if "PASS" in r)
    failed = sum(1 for r in results.values() if "FAIL" in r)
    skipped = sum(1 for r in results.values() if "SKIP" in r)
    
    print(f"\n📈 Results: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n✅ Phase 1 components are ready!")
    else:
        print("\n⚠️  Some components need attention")
    
    return failed == 0


async def test_database_connection():
    """데이터베이스 연결 상세 테스트"""
    
    print("\n" + "=" * 60)
    print("Database Connection Detailed Test")
    print("=" * 60)
    
    try:
        from ingest.database import DatabaseManager
        
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        async with db_manager.pool.acquire() as conn:
            # PostgreSQL 버전
            version = await conn.fetchval("SELECT version()")
            print(f"\nPostgreSQL Version:\n{version}")
            
            # pgvector 확장
            extensions = await conn.fetch("""
                SELECT extname, extversion 
                FROM pg_extension 
                WHERE extname = 'vector'
            """)
            
            if extensions:
                print(f"\npgvector Extension:")
                for ext in extensions:
                    print(f"  - {ext['extname']} v{ext['extversion']}")
            
            # 테이블 존재 확인
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'mvp_ddu_documents'
            """)
            
            if tables:
                print(f"\n✅ MVP table exists")
                
                # 인덱스 확인
                indexes = await conn.fetch("""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename = 'mvp_ddu_documents'
                """)
                
                print(f"\nIndexes ({len(indexes)}):")
                for idx in indexes:
                    print(f"  - {idx['indexname']}")
        
        await db_manager.close()
        
    except Exception as e:
        print(f"\n❌ Database test error: {e}")


def main():
    """메인 실행 함수"""
    
    print("\nMVP RAG System - Phase 1 Test Suite")
    print("=" * 60)
    print("\nOptions:")
    print("1. Test all Phase 1 components")
    print("2. Test database connection (detailed)")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ")
    
    if choice == "1":
        asyncio.run(test_phase1_components())
    elif choice == "2":
        asyncio.run(test_database_connection())
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid option")


if __name__ == "__main__":
    # 환경 변수 체크
    required_env = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [var for var in required_env if not os.getenv(var)]
    
    if missing:
        print(f"⚠️  Missing environment variables: {', '.join(missing)}")
        print("Some tests may fail without proper configuration")
    
    main()