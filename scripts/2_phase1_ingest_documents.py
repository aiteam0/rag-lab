"""
Document Ingestion Script for MVP RAG System
Pickle 파일에서 문서를 로드하고 데이터베이스에 저장
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from tqdm.asyncio import tqdm
import time

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from ingest.database import DatabaseManager
from ingest.loader import DDUPickleLoader
from ingest.embeddings import DualLanguageEmbeddings
from ingest.models import DDUDocument

# .env 파일 로드
load_dotenv()


async def ingest_documents(pickle_path: str, batch_size: int = 10):
    """
    DDU 문서 인제스트
    
    Args:
        pickle_path: Pickle 파일 경로
        batch_size: 배치 크기
    """
    print("=" * 60)
    print("MVP RAG System - Document Ingestion")
    print("=" * 60)
    
    # Pickle 파일 검증
    print(f"\n📁 Loading pickle file: {pickle_path}")
    if not DDUPickleLoader.validate_pickle_file(pickle_path):
        print("❌ Invalid pickle file format")
        return
    
    # 로더 초기화
    loader = DDUPickleLoader(pickle_path)
    
    # 통계 출력
    print("\n📊 Document Statistics:")
    stats = loader.get_statistics()
    print(f"  - Total Documents: {stats['total_documents']}")
    print(f"  - Categories: {stats['categories']}")
    print(f"  - Sources: {list(stats['sources'].keys())[:3]}...")
    print(f"  - Page Range: {stats['page_range']['min']} - {stats['page_range']['max']}")
    print(f"  - Has Translation: {stats['has_translation']} docs")
    print(f"  - Has Contextualize: {stats['has_contextualize']} docs")
    
    # 사용자 확인
    response = input(f"\nProceed with ingestion of {stats['total_documents']} documents? (y/N): ")
    if response.lower() != 'y':
        print("Ingestion cancelled")
        return
    
    # 문서 로드
    print("\n📌 Loading documents...")
    documents = loader.load_documents()
    print(f"✅ Loaded {len(documents)} documents")
    
    # 데이터베이스 매니저 초기화
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # 임베딩 생성기 초기화
    embeddings = DualLanguageEmbeddings()
    
    # 배치 처리
    print(f"\n📌 Starting ingestion (batch size: {batch_size})...")
    start_time = time.time()
    
    success_count = 0
    error_count = 0
    
    # tqdm으로 진행 상황 표시
    for i in tqdm(range(0, len(documents), batch_size), desc="Ingesting"):
        batch = documents[i:i+batch_size]
        
        for doc in batch:
            try:
                # 문서를 딕셔너리로 변환
                doc_dict = doc.to_db_dict()
                
                # 임베딩 생성
                korean_emb, english_emb = await embeddings.embed_document(doc_dict)
                
                # entity 필드를 JSON 문자열로 변환
                entity_json = None
                if doc_dict.get("entity") is not None:
                    entity_json = json.dumps(doc_dict.get("entity"), ensure_ascii=False)
                
                # 벡터를 문자열로 변환 (pgvector 형식)
                korean_emb_str = None
                if korean_emb:
                    korean_emb_str = f"[{','.join(map(str, korean_emb))}]"
                
                english_emb_str = None  
                if english_emb:
                    english_emb_str = f"[{','.join(map(str, english_emb))}]"
                
                # DB 저장
                async with db_manager.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO mvp_ddu_documents (
                            source, page, category, page_content,
                            translation_text, contextualize_text, caption,
                            entity, image_path, human_feedback,
                            embedding_korean, embedding_english,
                            search_vector_korean, search_vector_english
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10,
                                 $11::vector, $12::vector,
                                 to_tsvector('simple', COALESCE($13, '')),
                                 to_tsvector('english', COALESCE($14, '')))
                    """,
                        doc_dict.get("source"),
                        doc_dict.get("page"),
                        doc_dict.get("category"),
                        doc_dict.get("page_content"),
                        doc_dict.get("translation_text"),
                        doc_dict.get("contextualize_text"),
                        doc_dict.get("caption"),
                        entity_json,  # JSON 문자열로 변환된 entity
                        doc_dict.get("image_path"),
                        doc_dict.get("human_feedback", ""),
                        korean_emb_str,  # 문자열로 변환된 벡터
                        english_emb_str,  # 문자열로 변환된 벡터
                        # 한국어 검색 텍스트
                        (doc_dict.get("contextualize_text", "") + " " + 
                         doc_dict.get("page_content", "") + " " +
                         doc_dict.get("caption", "")),
                        # 영어 검색 텍스트
                        doc_dict.get("translation_text", "")
                    )
                
                success_count += 1
                
            except Exception as e:
                print(f"\n⚠️  Error ingesting document {doc.source} (page {doc.page}): {e}")
                error_count += 1
    
    # 처리 시간 계산
    elapsed_time = time.time() - start_time
    
    # 최종 통계 출력
    print("\n" + "=" * 60)
    print("Ingestion Summary")
    print("=" * 60)
    print(f"✅ Successfully ingested: {success_count} documents")
    if error_count > 0:
        print(f"❌ Failed: {error_count} documents")
    print(f"⏱️  Total time: {elapsed_time:.2f} seconds")
    print(f"📈 Average: {elapsed_time/len(documents):.3f} seconds per document")
    
    # DB 통계 확인
    print("\n📊 Final Database Statistics:")
    stats = await db_manager.get_table_stats()
    print(f"  - Total Documents: {stats['total_documents']}")
    for category, count in list(stats['categories'].items())[:5]:
        print(f"  - {category}: {count} docs")
    
    # 연결 종료
    await db_manager.close()
    print("\n✅ Ingestion completed successfully!")


async def test_ingestion(pickle_path: str, limit: int = 5):
    """
    소수의 문서로 인제스트 테스트
    
    Args:
        pickle_path: Pickle 파일 경로
        limit: 테스트할 문서 수
    """
    print(f"\n🧪 Test Mode: Ingesting first {limit} documents")
    
    # 로더 초기화
    loader = DDUPickleLoader(pickle_path)
    documents = loader.load_documents()[:limit]
    
    # 데이터베이스 매니저 초기화
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # 임베딩 생성기 초기화
    embeddings = DualLanguageEmbeddings()
    
    for i, doc in enumerate(documents, 1):
        print(f"\n📄 Document {i}/{limit}")
        print(f"  - Source: {doc.source}")
        print(f"  - Page: {doc.page}")
        print(f"  - Category: {doc.category}")
        print(f"  - Content Length: {len(doc.page_content or '')} chars")
        
        # 임베딩 생성
        doc_dict = doc.to_db_dict()
        korean_emb, english_emb = await embeddings.embed_document(doc_dict)
        
        print(f"  - Korean Embedding: {'✅' if korean_emb else '❌'}")
        print(f"  - English Embedding: {'✅' if english_emb else '❌'}")
    
    await db_manager.close()
    print("\n✅ Test completed!")


def main():
    """메인 실행 함수"""
    
    print("\nMVP RAG System - Document Ingestion Utility")
    print("=" * 60)
    
    # 기본 pickle 파일 경로
    default_pickle = "/mnt/e/MyProject2/multimodal-rag-wsl-v2/data/gv80_owners_manual_TEST6P_documents.pkl"
    
    # Pickle 파일 선택
    if os.path.exists(default_pickle):
        print(f"\nDefault pickle file found: {default_pickle}")
        use_default = input("Use default file? (Y/n): ")
        if use_default.lower() != 'n':
            pickle_path = default_pickle
        else:
            pickle_path = input("Enter pickle file path: ")
    else:
        pickle_path = input("Enter pickle file path: ")
    
    # 파일 존재 확인
    if not os.path.exists(pickle_path):
        print(f"❌ File not found: {pickle_path}")
        return
    
    print("\nOptions:")
    print("1. Full ingestion")
    print("2. Test ingestion (first 5 documents)")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ")
    
    if choice == "1":
        batch_size = input("Batch size (default 10): ")
        batch_size = int(batch_size) if batch_size else 10
        asyncio.run(ingest_documents(pickle_path, batch_size))
    elif choice == "2":
        asyncio.run(test_ingestion(pickle_path))
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid option")


if __name__ == "__main__":
    # 환경 변수 체크
    required_env = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", 
                    "OPENAI_API_KEY", "OPENAI_EMBEDDING_MODEL"]
    missing = [var for var in required_env if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please create a .env file with the required variables")
        sys.exit(1)
    
    main()