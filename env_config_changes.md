# .env 기반 설정 관리 개선 사항

## 📋 개요
하드코딩된 설정값들을 `.env` 파일로 통합 관리하도록 Phase 1 소스코드를 수정했습니다.

## 🔧 수정된 파일

### 1. `.env` 파일 (확장)
```bash
# 새로 추가된 설정값들
OPENAI_EMBEDDING_DIMENSIONS=1536         # 임베딩 차원 수
DB_TABLE_NAME=mvp_ddu_documents         # 테이블명

# Search Configuration
SEARCH_RRF_K=60                         # RRF 병합 파라미터
SEARCH_DEFAULT_TOP_K=10                 # 기본 검색 결과 수
SEARCH_DEFAULT_SEMANTIC_WEIGHT=0.5      # 시맨틱 검색 기본 가중치
SEARCH_DEFAULT_KEYWORD_WEIGHT=0.5       # 키워드 검색 기본 가중치
SEARCH_MAX_RESULTS=20                   # 최대 검색 결과 수

# Ingestion Configuration
INGEST_BATCH_SIZE=10                    # 인제스트 배치 크기
INGEST_DEFAULT_PICKLE_PATH=data/gv80_owners_manual_TEST6P_documents.pkl

# Performance Thresholds
PERF_QUERY_TIMEOUT_MS=500               # 쿼리 타임아웃 (밀리초)
PERF_MAX_CONCURRENT_CONNECTIONS=10      # 최대 동시 DB 연결 수

# Phase 2 설정 (미래 대비)
LANGGRAPH_MAX_ITERATIONS=10
LANGGRAPH_RECURSION_LIMIT=5
LANGGRAPH_PLANNING_MAX_SUBTASKS=5
CRAG_HALLUCINATION_THRESHOLD=0.7
CRAG_ANSWER_GRADE_THRESHOLD=0.8
CRAG_MAX_RETRIES=3
```

### 2. `retrieval/hybrid_search.py`
**변경 전:**
```python
self.k = 60  # 하드코딩
top_k: int = 10,
semantic_weight: float = 0.5,
keyword_weight: float = 0.5
```

**변경 후:**
```python
self.k = int(os.getenv("SEARCH_RRF_K", "60"))
self.table_name = os.getenv("DB_TABLE_NAME", "mvp_ddu_documents")

# 함수 파라미터 기본값을 None으로 변경
top_k: int = None,
semantic_weight: float = None,
keyword_weight: float = None

# 함수 내부에서 .env 값 사용
if top_k is None:
    top_k = int(os.getenv("SEARCH_DEFAULT_TOP_K", "10"))
if semantic_weight is None:
    semantic_weight = float(os.getenv("SEARCH_DEFAULT_SEMANTIC_WEIGHT", "0.5"))
if keyword_weight is None:
    keyword_weight = float(os.getenv("SEARCH_DEFAULT_KEYWORD_WEIGHT", "0.5"))
```

### 3. `ingest/embeddings.py`
**변경 전:**
```python
dimensions=1536  # 하드코딩
```

**변경 후:**
```python
dimensions=int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
```

### 4. `ingest/database.py`
**변경 전:**
```python
max_size=20,  # 하드코딩
```

**변경 후:**
```python
max_size=int(os.getenv("PERF_MAX_CONCURRENT_CONNECTIONS", "10")),
self.table_name = os.getenv("DB_TABLE_NAME", "mvp_ddu_documents")
```

## 🎯 개선 효과

### 1. 중앙 집중식 설정 관리
- 모든 설정이 `.env` 파일 하나에서 관리됨
- 환경별 설정 변경이 용이 (개발/테스트/운영)

### 2. 유연성 향상
- 코드 수정 없이 설정값 변경 가능
- 성능 튜닝이 간편해짐

### 3. 보안 강화
- 민감한 정보가 코드에서 분리됨
- `.env.example` 파일로 설정 구조 공유

### 4. 확장성
- Phase 2 설정도 미리 준비
- 새로운 설정 추가가 체계적

## 📝 사용 방법

### 기본 사용
```python
# 기존처럼 사용 - 자동으로 .env 값 사용
search_results = await hybrid_search.search(
    query="안전벨트",
    filter=filter
)
```

### 커스텀 값 사용
```python
# 특정 검색에서 다른 값 사용하고 싶을 때
search_results = await hybrid_search.search(
    query="안전벨트", 
    filter=filter,
    top_k=20,  # .env 값 대신 20 사용
    semantic_weight=0.7  # .env 값 대신 0.7 사용
)
```

## ⚠️ 주의사항

1. **`.env` 파일 보안**
   - `.env` 파일은 절대 git에 커밋하지 마세요
   - `.env.example`을 참고하여 `.env` 생성

2. **타입 변환**
   - 환경변수는 문자열이므로 적절한 타입 변환 필요
   - `int()`, `float()` 등 사용

3. **기본값 설정**
   - 환경변수가 없을 때를 대비한 기본값 항상 제공
   - `os.getenv("KEY", "default")`

## 🔄 마이그레이션 가이드

기존 시스템에서 업그레이드하는 경우:

1. 새로운 `.env` 설정값 추가
2. 소스코드 업데이트 (위 수정사항 적용)
3. 테스트 실행으로 정상 작동 확인

```bash
# .env 파일 업데이트
cp .env.example .env
# 필요한 값들 수정

# 테스트 실행
uv run python scripts/test_phase1.py
```

## 📊 설정값 참조표

| 설정명 | 기본값 | 설명 | 사용처 |
|--------|--------|------|--------|
| SEARCH_RRF_K | 60 | RRF 병합 k 파라미터 | HybridSearch |
| SEARCH_DEFAULT_TOP_K | 10 | 기본 검색 결과 수 | HybridSearch.search() |
| SEARCH_DEFAULT_SEMANTIC_WEIGHT | 0.5 | 시맨틱 검색 가중치 | HybridSearch.search() |
| SEARCH_DEFAULT_KEYWORD_WEIGHT | 0.5 | 키워드 검색 가중치 | HybridSearch.search() |
| OPENAI_EMBEDDING_DIMENSIONS | 1536 | 임베딩 벡터 차원 | DualLanguageEmbeddings |
| DB_TABLE_NAME | mvp_ddu_documents | 데이터베이스 테이블명 | 모든 DB 작업 |
| PERF_MAX_CONCURRENT_CONNECTIONS | 10 | 최대 DB 연결 수 | DatabaseManager |
| INGEST_BATCH_SIZE | 10 | 인제스트 배치 크기 | 문서 인제스트 |

---

이제 모든 설정이 `.env` 파일에서 관리되어 더욱 유연하고 관리하기 쉬운 시스템이 되었습니다.