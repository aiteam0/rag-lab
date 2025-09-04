# 똑딱이 Entity Filter 생성 문제 분석 및 개선 계획 V2

## 문제 상황
`'똑딱이 문서에 대해 알려줘'` 쿼리 실행 시 자동차 매뉴얼 내용이 반환되는 문제

### 실제 결과 (잘못된 응답)
- 자동차 안전벨트, 사고기록장치, 제작결함 안내 등 차량 매뉴얼 내용 반환
- gv80_owners_manual_TEST6P.pdf 문서만 참조
- PPT 삽입 문서(똑딱이) 관련 내용 전혀 없음

## 근본 원인 분석 (workflow_20250903_173648.log)

### 1. 쿼리 처리 흐름
```
원본 쿼리: "똑딱이 문서에 대해 알려줘"
↓
Subtask 1: "똑딱이 문서의 정의"
Subtask 2: "똑딱이 문서의 사용 예시"  
Subtask 3: "똑딱이 문서의 장단점"
```

### 2. Entity Type 추출 (✅ 정상)
```
[SUBTASK_EXECUTOR] Extracted info:
  - entity_type: 똑딱이  ✅
  - keywords: ['똑딱이', '문서']
```

### 3. Filter 생성 실패 (❌ 문제점)
```
[FILTER_DEBUG] Query: 똑딱이 문서의 정의
[FILTER_DEBUG] Extraction entity_type: 똑딱이
[FILTER_DEBUG] Valid entity_types: 똑딱이, image, table
[FILTER_DEBUG] Generated result.entity: None  ❌
[FILTER_DEBUG] Generated result.categories: []
```

### 4. 결과: 필터 없는 Semantic Search
- 필터가 없어서 전체 문서 대상 semantic search 수행
- "똑딱이 문서의 정의"와 의미적으로 유사한 gv80 매뉴얼 문서들이 검색됨
- Retrieved documents: gv80_owners_manual 문서들

## 문제 원인 상세 분석

### Filter Prompt의 Conservative 정책
현재 filter_prompt의 핵심 지시사항:
```
"You are a CONSERVATIVE filter generator"
"LESS IS MORE. Empty filter is better than wrong filter"
```

### LLM의 해석 차이
- **예시**: `"똑딱이 문서 알려줘"` → entity filter 생성
- **실제**: `"똑딱이 문서의 정의"` → filter 생성 안 함
- **원인**: "정의"라는 단어를 보고 설명/정의를 원하는 것으로 해석

### Entity Type과 Filter 생성의 불일치
- entity_type은 '똑딱이'로 올바르게 추출됨
- 하지만 LLM이 conservative 정책에 따라 filter 생성을 거부

## 개선 방안

### 방안 1: 강제 Entity Filter 생성 (권장) ⭐
**_generate_filter() 메서드 수정**

```python
def _generate_filter(self, query: str, extraction: QueryExtraction, metadata: Dict[str, Any]) -> Optional[MVPSearchFilter]:
    # ... 기존 코드 ...
    
    # 똑딱이 entity_type이 추출되면 무조건 filter 생성
    if extraction.entity_type == '똑딱이':
        logger.info("[FILTER_OVERRIDE] '똑딱이' entity_type detected, forcing entity filter")
        return MVPSearchFilter(
            entity={'type': '똑딱이'}
        )
    
    # 기존 LLM 기반 filter 생성 로직
    structured_llm = self.llm.with_structured_output(...)
    # ...
```

### 방안 2: Filter Prompt 수정
**DO CREATE FILTER 규칙 강화**

```python
DO CREATE FILTER when:
# 기존 규칙들...
- Looking for embedded docs: "똑딱이" mentioned anywhere → entity: {{"type": "똑딱이"}}
- ANY query with entity_type='똑딱이' → entity: {{"type": "똑딱이"}} ALWAYS
```

**예시 추가**
```
Query: "똑딱이 문서의 정의"
Extraction: {{entity_type: "똑딱이", keywords: ["똑딱이", "문서", "정의"]}}
Filter: {{entity: {{"type": "똑딱이"}}}} (Always filter when entity_type is 똑딱이)

Query: "똑딱이 문서의 사용 예시"
Extraction: {{entity_type: "똑딱이", keywords: ["똑딱이", "문서", "사용", "예시"]}}
Filter: {{entity: {{"type": "똑딱이"}}}} (Always filter when entity_type is 똑딱이)
```

### 방안 3: Hybrid Approach (가장 안정적) ⭐⭐
**두 가지 방안 모두 적용**

1. extraction.entity_type이 '똑딱이'면 무조건 filter 생성 (방안 1)
2. Filter prompt도 개선하여 LLM이 더 적극적으로 filter 생성 (방안 2)

## 구현 예시 (방안 3)

**파일**: `workflow/nodes/subtask_executor.py`

**수정 1**: Line 397 이후 (filter 생성 전 체크)
```python
# 똑딱이 entity_type 강제 필터 생성
if extraction.entity_type == '똑딱이' and '똑딱이' in metadata.get("entity_types", []):
    logger.info(f"[FILTER_OVERRIDE] Forcing '똑딱이' entity filter for query: {query}")
    return MVPSearchFilter(
        categories=None,
        pages=None,
        sources=None,
        caption=None,
        entity={'type': '똑딱이'}
    )
```

**수정 2**: Filter prompt의 DO CREATE FILTER 섹션
```python
DO CREATE FILTER when:
- ... 기존 규칙들 ...
- Entity type is '똑딱이': ALWAYS create entity: {{"type": "똑딱이"}} filter
```

## 예상 효과

### 수정 전
- `"똑딱이 문서의 정의"` → No filter → 전체 문서 검색 → 자동차 매뉴얼 반환 ❌

### 수정 후  
- `"똑딱이 문서의 정의"` → entity: {"type": "똑딱이"} → 18개 PPT 삽입 문서 검색 ✅

## 테스트 방법

```python
# 테스트 쿼리들
test_queries = [
    "똑딱이 문서에 대해 알려줘",
    "똑딱이 문서의 정의",
    "똑딱이 문서의 사용 예시",
    "똑딱이 문서의 장단점"
]

# 각 쿼리에 대해 entity filter가 생성되는지 확인
# metadata에서 filter_applied 확인
# 검색된 문서의 entity.type이 '똑딱이'인지 확인
```

## 결론

현재 시스템은 entity_type 추출은 정확하게 하지만, Conservative filter 생성 정책 때문에 필터를 만들지 않아 문제가 발생합니다. 

**즉각 적용 가능한 해결책**: extraction.entity_type이 '똑딱이'일 때 무조건 entity filter를 생성하도록 강제하는 로직 추가 (5줄 코드 추가)

이렇게 하면 '똑딱이' 관련 모든 쿼리가 올바르게 PPT 삽입 문서를 검색할 수 있게 됩니다.