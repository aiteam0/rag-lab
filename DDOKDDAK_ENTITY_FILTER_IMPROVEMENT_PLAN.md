# 똑딱이 Entity Filter 문제 분석 및 개선 계획

## 문제 요약
`'똑딱이 문서에 대해 알려줘'` 쿼리가 올바르게 작동하지 않는 문제 발생

### 증상
- Entity type은 '똑딱이'로 정확히 추출됨
- 그러나 entity filter가 생성되지 않음
- 시스템이 semantic search로 fallback하여 관련 없는 자동차 문서를 반환

## 근본 원인 분석

### 1. 실행 흐름 추적
```
Query → SubtaskExecutorNode._extract_query_info() → entity_type = '똑딱이' ✅
     → SubtaskExecutorNode._generate_filter() → entity filter = None ❌
     → Fallback to semantic search → Wrong results
```

### 2. 핵심 문제점 발견

**DDUFilterGeneration 모델 정의** (`workflow/nodes/subtask_executor.py` Line 62):
```python
class DDUFilterGeneration(BaseModel):
    """DDU 필터 생성 결과"""
    # ...
    entity: Optional[Dict[str, Any]] = Field(
        None, 
        description="Entity filter (type must be 'image' or 'table')"  # ❌ 문제!
    )
```

**문제**: Pydantic 모델의 entity 필드 설명이 `"type must be 'image' or 'table'"`로 제한되어 있음

### 3. 충돌하는 컴포넌트들

#### ✅ 올바르게 설정된 부분들:
1. **filter_prompt** (Line 139-153): '똑딱이' 예시 포함
   ```
   "Looking for embedded docs: "삽입객체" or "참조문서" → entity: {"type": "똑딱이"}"
   ```

2. **_extract_query_info()** (Line 228-232): '똑딱이' 키워드 매핑 존재
   ```python
   '똑딱이', '똑딱이 타입', '똑딱이 문서', '참조문서', 'reference', 'appendix', '삽입객체' → '똑딱이'
   ```

3. **Metadata** (확인 완료): entity_types에 '똑딱이' 포함
   ```
   Entity types in metadata: ['똑딱이', 'image', 'table']
   ```

#### ❌ 문제가 있는 부분:
- **DDUFilterGeneration.entity 필드 설명**: '똑딱이'를 허용하지 않음

### 4. 문제 메커니즘
1. LLM이 structured output을 생성할 때 Pydantic 필드 description을 엄격히 따름
2. Description이 "type must be 'image' or 'table'"로 제한됨
3. LLM이 '똑딱이' type의 entity filter를 생성하려 해도 schema 제약으로 거부됨
4. 결과적으로 entity 필드가 None으로 남음

## 개선 계획

### 즉시 수정 필요 (1줄 변경)

**파일**: `workflow/nodes/subtask_executor.py`  
**위치**: Line 62  
**현재**:
```python
entity: Optional[Dict[str, Any]] = Field(
    None, 
    description="Entity filter (type must be 'image' or 'table')"
)
```

**수정**:
```python
entity: Optional[Dict[str, Any]] = Field(
    None, 
    description="Entity filter (type must be 'image', 'table', or '똑딱이')"
)
```

### 추가 개선 사항 (선택적)

1. **동적 Description 생성** (더 견고한 해결책):
   - Metadata에서 entity_types를 동적으로 가져와 description 생성
   - 하지만 Pydantic 모델은 클래스 정의 시점에 고정되므로 구현 복잡

2. **Validation 로직 개선**:
   - _generate_filter() 메서드의 검증 로직은 이미 올바름 (Line 398-401)
   - metadata의 entity_types와 대조하여 유효성 검사

3. **테스트 케이스 추가**:
   - '똑딱이' entity filter 생성 테스트
   - 다양한 '똑딱이' 관련 쿼리 테스트

## 예상 효과

### 수정 전:
- `'똑딱이 문서에 대해 알려줘'` → No filter → Semantic search → 자동차 관련 문서 (❌)

### 수정 후:
- `'똑딱이 문서에 대해 알려줘'` → entity: {"type": "똑딱이"} → 18개 PPT 삽입 문서 검색 (✅)

## 검증 방법

1. **단위 테스트**:
```python
# DDUFilterGeneration이 '똑딱이' entity를 생성하는지 확인
filter_result = _generate_filter(
    "똑딱이 문서에 대해 알려줘",
    QueryExtraction(entity_type="똑딱이"),
    metadata={"entity_types": ["똑딱이", "image", "table"]}
)
assert filter_result.entity == {"type": "똑딱이"}
```

2. **통합 테스트**:
```bash
python scripts/test_ddokddak_query_debug.py
# Filter Applied 섹션에서 entity: {"type": "똑딱이"} 확인
```

3. **End-to-End 테스트**:
```python
workflow = MVPWorkflowGraph()
result = workflow.run("똑딱이 문서에 대해 알려줘")
# 결과에서 PPT 삽입 문서 관련 내용 확인
```

## 결론

문제는 단순한 설정 불일치였음:
- **Prompt**: '똑딱이' 허용 (✅)
- **Logic**: '똑딱이' 처리 (✅)
- **Metadata**: '똑딱이' 포함 (✅)
- **Schema Description**: '똑딱이' 미포함 (❌) ← 유일한 문제점

1줄 수정으로 즉시 해결 가능하며, 이는 시스템 전체의 '똑딱이' entity 지원을 완성시킬 것임.