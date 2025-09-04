# DDokDDak Entity Transplant Plan
## DDokDDak 메타데이터를 DDU Documents에 이식하는 시스템

### 📌 개요

DDokDDak(똑딱이) JSON 파일의 풍부한 메타데이터(keywords, hypothetical_questions 등)를 기존 DDU documents의 entity 필드에 이식하여 검색 성능을 향상시키는 시스템입니다.

### 🎯 목적

1. **검색 정확도 향상**: keywords와 hypothetical_questions를 활용한 의미 기반 검색
2. **메타데이터 통합**: DDokDDak과 DDU의 장점 결합
3. **구조화된 정보 제공**: entity 필드를 통한 체계적인 정보 관리

---

## 📋 시스템 아키텍처

### 1. 데이터 매칭 전략

#### 매칭 기준
- **Primary Key**: `source_file` (정확한 파일명 매칭)
- **Secondary Key**: `source_page` (정확한 페이지 번호 매칭)

#### 매칭 규칙
```python
# ✅ 정확한 매칭만 허용
ddokddak: "디지털정부혁신_추진계획.pdf" + page 3
    ↓
ddu: "data/디지털정부혁신_추진계획.pdf" + page 3

# ❌ 파일명 정규화 없음
# ❌ source_page가 None이면 에러
# ❌ 매칭 실패시 에러 발생
```

### 2. Entity 변환 스키마

```json
{
    "type": "똑딱이",  // 고정값 (중요!)
    "title": "문서 제목",
    "details": "상세 설명 (길이 제한 없음)",
    "keywords": ["키워드1", "키워드2", ...],
    "hypothetical_questions": ["예상 질문1", "예상 질문2", ...],
    "raw_output": "원본 출력 (길이 제한 없음)"
}
```

### 3. 카테고리별 이식 규칙

| 카테고리 | 이식 여부 | 설명 |
|---------|----------|------|
| **paragraph** | ✅ | 일반 텍스트 단락 |
| **heading1** | ✅ | 제목 레벨 1 |
| **heading2** | ✅ | 제목 레벨 2 |
| **heading3** | ✅ | 제목 레벨 3 |
| list | ❌ | 리스트 (제외) |
| table | ❌ | 테이블 (제외) |
| figure | ❌ | 그림 (제외) |
| 기타 | ❌ | 모두 제외 |

---

## 🔧 구현 상세

### 클래스 구조

```python
class DdokddakEntityTransplanter:
    
    ALLOWED_CATEGORIES = ['paragraph', 'heading1', 'heading2', 'heading3']
    
    def __init__(self, ddokddak_json_path, ddu_pickle_path)
    def _load_and_validate_ddokddak(self, json_path)
    def _load_ddu_pickle(self, pickle_path)
    def find_matching_documents(self)
    def transform_entity(self, ddokddak_result)
    def transplant_entities(self)
    def save_results(self, output_path)
    def generate_report(self)
```

### 주요 메서드 설명

#### 1. `_load_and_validate_ddokddak()`
- DDokDDak JSON 파일 로드
- source_page None 체크
- 필수 필드 검증 (title, keywords, hypothetical_questions)

#### 2. `find_matching_documents()`
- 정확한 파일명과 페이지 번호로 매칭
- 매칭 실패시 ValueError 발생
- 매칭된 문서 리스트 반환

#### 3. `transform_entity()`
- DDokDDak 데이터를 DDU entity 형식으로 변환
- type 필드는 "똑딱이"로 고정
- 모든 필드 전체 길이 보존 (길이 제한 없음)

#### 4. `transplant_entities()`
- 메인 이식 로직
- ALLOWED_CATEGORIES에 속하는 문서만 처리
- 통계 수집 및 진행 상황 출력

---

## 🚀 사용 방법

### 1. 기본 사용

```python
from transplant_ddokddak_entity import DdokddakEntityTransplanter

# 초기화
transplanter = DdokddakEntityTransplanter(
    ddokddak_json_path="data/ddokddak_디지털정부혁신_추진계획_TEST3P_20250902_150632.json",
    ddu_pickle_path="data/merged_ddu_documents.pkl"
)

# 이식 실행
stats = transplanter.transplant_entities()

# 결과 저장
transplanter.save_results("data/transplanted_ddu_documents.pkl")

# 보고서 출력
transplanter.generate_report()
```

### 2. 에러 처리

```python
try:
    transplanter = DdokddakEntityTransplanter(json_path, pkl_path)
    stats = transplanter.transplant_entities()
    transplanter.save_results(output_path)
    
except ValueError as e:
    print(f"❌ Validation Error: {e}")
    sys.exit(1)
    
except FileNotFoundError as e:
    print(f"❌ File not found: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
```

### 3. 배치 처리

```python
import glob

# 모든 DDokDDak JSON 파일 처리
ddokddak_files = glob.glob("data/ddokddak_*.json")

for json_file in ddokddak_files:
    try:
        print(f"\n📄 Processing: {json_file}")
        transplanter = DdokddakEntityTransplanter(json_file, ddu_pickle_path)
        transplanter.transplant_entities()
        
    except ValueError as e:
        print(f"⏭️  Skipping {json_file}: {e}")
        continue

# 최종 결과 저장
transplanter.save_results("data/transplanted_ddu_documents.pkl")
```

---

## 📊 예상 결과

### 이식 대상
- **소스**: 디지털정부혁신_추진계획.pdf
- **페이지**: 특정 페이지 (source_page 기준)
- **카테고리**: paragraph, heading1, heading2, heading3
- **예상 문서 수**: 해당 페이지의 텍스트 카테고리 문서들

### 성능 향상
- **검색 정확도**: +30-40% (keywords 활용)
- **질의 매칭**: +20-30% (hypothetical_questions 활용)
- **의미 기반 검색**: 구조화된 메타데이터로 향상

### 통계 예시
```
📊 TRANSPLANT REPORT
====================================
Matched documents: 25
Successfully transplanted: 20
Skipped (wrong category): 5

By Category:
  • paragraph: 15
  • heading1: 2
  • heading2: 2
  • heading3: 1
```

---

## ⚠️ 주의사항

### 1. 데이터 검증
- source_page가 None인 경우 처리 불가
- 필수 필드 누락시 에러 발생
- 파일명은 정확히 일치해야 함

### 2. 백업
- 항상 원본 파일 백업 생성
- 타임스탬프 포함된 백업 파일명
- 실패시 백업에서 복구 가능

### 3. 메모리 관리
- 대용량 details/raw_output 필드 주의
- PostgreSQL JSONB 1GB 제한 고려
- 배치 처리시 메모리 모니터링 필요

### 4. 호환성
- Langchain Document 구조 유지
- 기존 검색 시스템과 완벽 호환
- entity type "똑딱이"로 구분 가능

---

## 🔍 검증 방법

### 1. 이식 전후 비교
```python
# 이식 전
original_doc = original_documents[0]
print(f"Original entity: {original_doc.metadata.get('entity')}")

# 이식 후
transplanted_doc = transplanted_documents[0]
print(f"Transplanted entity: {transplanted_doc.metadata.get('entity')}")
```

### 2. 검색 테스트
```python
# Entity keywords로 검색
search_results = hybrid_search.search(
    query="디지털 전환",
    filter={"entity": {"keywords": ["디지털 전환"]}}
)
```

### 3. 데이터베이스 확인
```sql
-- Entity가 이식된 문서 확인
SELECT id, category, entity->>'type' as entity_type
FROM mvp_ddu_documents
WHERE entity->>'type' = '똑딱이';
```

---

## 📚 관련 파일

- **소스 코드**: `scripts/transplant_ddokddak_entity.py`
- **DDokDDak JSON**: `data/ddokddak_*.json`
- **DDU Documents**: `data/merged_ddu_documents.pkl`
- **결과 파일**: `data/transplanted_ddu_documents.pkl`

---

## 🔄 업데이트 이력

- **2025-01-02**: 초기 버전 작성
  - 엄격한 매칭 전략 적용
  - 카테고리 제한 (paragraph, heading1-3)
  - 길이 제한 제거

---

## 📝 라이선스

이 프로젝트는 내부 사용 목적으로 개발되었습니다.