"""
Database Manager for MVP RAG System
Handles PostgreSQL + pgvector operations
"""

import os
from typing import Optional
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

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
        self.pool: Optional[ConnectionPool] = None
    
    def initialize(self):
        """데이터베이스 연결 풀 초기화"""
        self.pool = ConnectionPool(
            conninfo=self.connection_string,
            min_size=5,
            max_size=int(os.getenv("PERF_MAX_CONCURRENT_CONNECTIONS", "10")),
            timeout=60,
            configure=self._configure_connection,
            open=True  # 즉시 연결 시작
        )
        self.table_name = os.getenv("DB_TABLE_NAME", "mvp_ddu_documents")
    
    def _configure_connection(self, conn):
        """연결 설정 (session-level 설정)"""
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '30000'")
        conn.commit()  # 트랜잭션 커밋하여 INTRANS 상태 방지
    
    
    def close(self):
        """연결 풀 종료"""
        if self.pool:
            self.pool.close()
    
    
    def setup_database(self):
        """MVP 데이터베이스 스키마 설정"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                # pgvector 확장 활성화
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
                # MVP 테이블 생성
                cur.execute("""
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
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_korean_embedding 
                    ON mvp_ddu_documents 
                    USING ivfflat (embedding_korean vector_cosine_ops)
                    WITH (lists = 100)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_english_embedding 
                    ON mvp_ddu_documents 
                    USING ivfflat (embedding_english vector_cosine_ops)
                    WITH (lists = 100)
                """)
                
                # 전문 검색 인덱스 (GIN)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_korean_fts 
                    ON mvp_ddu_documents 
                    USING gin(search_vector_korean)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_english_fts 
                    ON mvp_ddu_documents 
                    USING gin(search_vector_english)
                """)
                
                # 메타데이터 인덱스
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_source 
                    ON mvp_ddu_documents(source)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_category 
                    ON mvp_ddu_documents(category)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_page 
                    ON mvp_ddu_documents(page)
                """)
                
                # 커밋을 수동으로 호출
                conn.commit()
            
        print("✅ 데이터베이스 스키마 설정 완료")
    
    def clear_table(self):
        """테이블 데이터 초기화 (테스트용)"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE mvp_ddu_documents RESTART IDENTITY")
                conn.commit()
        print("✅ 테이블 데이터 초기화 완료")
    
    def get_table_stats(self) -> dict:
        """테이블 통계 조회"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                # 전체 문서 수
                cur.execute("SELECT COUNT(*) FROM mvp_ddu_documents")
                total_count = cur.fetchone()[0]
                
                # 카테고리별 분포
                cur.execute("""
                    SELECT category, COUNT(*) as count 
                    FROM mvp_ddu_documents 
                    GROUP BY category 
                    ORDER BY count DESC
                """)
                category_stats = cur.fetchall()
                
                # 소스별 분포
                cur.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM mvp_ddu_documents 
                    GROUP BY source 
                    ORDER BY count DESC
                """)
                source_stats = cur.fetchall()
                
                # 페이지 범위
                cur.execute("""
                    SELECT MIN(page) as min_page, MAX(page) as max_page 
                    FROM mvp_ddu_documents
                """)
                page_range = cur.fetchone()
                
                return {
                    "total_documents": total_count,
                    "categories": {row[0]: row[1] for row in category_stats},
                    "sources": {row[0]: row[1] for row in source_stats},
                    "page_range": {
                        "min": page_range[0],
                        "max": page_range[1]
                    }
                }