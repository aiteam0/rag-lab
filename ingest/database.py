"""
Database Manager for MVP RAG System
Handles PostgreSQL + pgvector operations
"""

import asyncpg
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class DatabaseManager:
    """MVP 데이터베이스 관리자"""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Args:
            connection_string: PostgreSQL 연결 문자열
        """
        if connection_string:
            self.connection_string = connection_string
        else:
            # .env에서 연결 정보 구성
            self.connection_string = (
                f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
                f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            )
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """데이터베이스 연결 풀 초기화"""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=5,
            max_size=int(os.getenv("PERF_MAX_CONCURRENT_CONNECTIONS", "10")),
            command_timeout=60
        )
        self.table_name = os.getenv("DB_TABLE_NAME", "mvp_ddu_documents")
    
    async def close(self):
        """연결 풀 종료"""
        if self.pool:
            await self.pool.close()
    
    async def setup_database(self):
        """MVP 데이터베이스 스키마 설정"""
        async with self.pool.acquire() as conn:
            # pgvector 확장 활성화
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # MVP 테이블 생성
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mvp_ddu_documents (
                    -- 기본 식별자
                    id SERIAL PRIMARY KEY,
                    
                    -- 핵심 메타데이터 (검색 필터용)
                    source TEXT NOT NULL,
                    page INTEGER,
                    category TEXT NOT NULL,
                    
                    -- 콘텐츠 필드
                    page_content TEXT,
                    translation_text TEXT,
                    contextualize_text TEXT,
                    caption TEXT,
                    
                    -- 구조화 데이터
                    entity JSONB,
                    image_path TEXT,
                    
                    -- 추가 정보
                    human_feedback TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- 벡터 임베딩 (OpenAI text-embedding-3-small)
                    embedding_korean vector(1536),
                    embedding_english vector(1536),
                    
                    -- 전문 검색 인덱스
                    search_vector_korean tsvector,
                    search_vector_english tsvector
                )
            """)
            
            # 벡터 검색 인덱스 (IVFFlat)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_korean_embedding 
                ON mvp_ddu_documents 
                USING ivfflat (embedding_korean vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_english_embedding 
                ON mvp_ddu_documents 
                USING ivfflat (embedding_english vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            # 전문 검색 인덱스 (GIN)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_korean_fts 
                ON mvp_ddu_documents 
                USING gin(search_vector_korean)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_english_fts 
                ON mvp_ddu_documents 
                USING gin(search_vector_english)
            """)
            
            # 메타데이터 인덱스
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source 
                ON mvp_ddu_documents(source)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_category 
                ON mvp_ddu_documents(category)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_page 
                ON mvp_ddu_documents(page)
            """)
            
            print("✅ 데이터베이스 스키마 설정 완료")
    
    async def clear_table(self):
        """테이블 데이터 초기화 (테스트용)"""
        async with self.pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE mvp_ddu_documents RESTART IDENTITY")
            print("✅ 테이블 데이터 초기화 완료")
    
    async def get_table_stats(self) -> dict:
        """테이블 통계 조회"""
        async with self.pool.acquire() as conn:
            # 전체 문서 수
            total_count = await conn.fetchval(
                "SELECT COUNT(*) FROM mvp_ddu_documents"
            )
            
            # 카테고리별 분포
            category_stats = await conn.fetch("""
                SELECT category, COUNT(*) as count 
                FROM mvp_ddu_documents 
                GROUP BY category 
                ORDER BY count DESC
            """)
            
            # 소스별 분포
            source_stats = await conn.fetch("""
                SELECT source, COUNT(*) as count 
                FROM mvp_ddu_documents 
                GROUP BY source 
                ORDER BY count DESC
            """)
            
            # 페이지 범위
            page_range = await conn.fetchrow("""
                SELECT MIN(page) as min_page, MAX(page) as max_page 
                FROM mvp_ddu_documents
            """)
            
            return {
                "total_documents": total_count,
                "categories": {row['category']: row['count'] for row in category_stats},
                "sources": {row['source']: row['count'] for row in source_stats},
                "page_range": {
                    "min": page_range['min_page'],
                    "max": page_range['max_page']
                }
            }