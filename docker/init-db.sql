-- PostgreSQL + pgvector 초기화 스크립트
-- Docker 컨테이너 첫 실행 시 자동으로 실행됩니다.

-- pgvector 확장 생성 (벡터 임베딩 저장용)
CREATE EXTENSION IF NOT EXISTS vector;

-- 기본 스키마 확인
CREATE SCHEMA IF NOT EXISTS public;

-- 사용자 권한 설정
-- 참고: DB_USER는 docker-compose.yml의 환경변수에서 설정됩니다
-- 이 부분은 선택사항이지만, 명시적으로 권한을 부여합니다
ALTER SCHEMA public OWNER TO multimodal_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO multimodal_user;
GRANT CREATE ON SCHEMA public TO multimodal_user;

-- pgvector 확장 버전 확인 (로그용)
DO $$
DECLARE
    vector_version TEXT;
BEGIN
    SELECT extversion INTO vector_version
    FROM pg_extension
    WHERE extname = 'vector';
    
    IF vector_version IS NOT NULL THEN
        RAISE NOTICE 'pgvector extension version % is installed', vector_version;
    ELSE
        RAISE WARNING 'pgvector extension was not installed properly';
    END IF;
END $$;

-- 시스템 설정 최적화 (선택사항)
-- 벡터 검색 성능 향상을 위한 설정
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET work_mem = '16MB';

-- 설정 적용을 위해 설정 리로드 (Docker 환경에서는 재시작 시 적용)
SELECT pg_reload_conf();

-- 초기화 완료 메시지
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE 'pgvector extension is ready for use.';
    RAISE NOTICE 'Run the setup script to create tables and indexes.';
END $$;
