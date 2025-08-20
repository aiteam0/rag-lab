# Refined Fix Plan v3.0 - User Feedback Incorporated

## 📋 사용자 피드백 반영 사항

### ✅ 승인된 수정
- Phase 1: 메타데이터 전달 (전체)
- Phase 2: 잘못된 예시 수정, 실제 DB 소스 사용
- Phase 4: Web search 성공 시 error 클리어

### ❌ 거부된 수정 (이유 포함)
- GV80 특정 언급 → 다른 차량 모델도 처리해야 함
- Validation 로직 → LLM이 메타데이터로 충분히 처리 가능
- Retrieval non-fatal → 0개는 명확한 에러, raise 유지
- OR 연산자 → 정확도 저하, AND 유지

## 🎯 핵심 수정 전략

### 원칙
1. **메타데이터 신뢰**: LLM에 정확한 정보를 제공하면 올바른 판단
2. **보수적 추출**: 문서가 명시적으로 언급될 때만 source 추출
3. **일반화된 규칙**: 특정 차량 모델이 아닌 패턴 기반
4. **정확도 우선**: AND 연산자와 strict error handling 유지

## 📝 최종 수정 계획

### Phase 1: 메타데이터 전달 (CRITICAL) ✅

#### 1.1 extraction_prompt 수정
```python
# workflow/nodes/subtask_executor.py
# Line 170-171, ADD:
Available Categories: {categories}
Available Entity Types: {entity_types}
Available Sources: {sources}  # ← ADD THIS!

# Line 243-245, ADD:
sources_str = ", ".join(metadata.get("available_sources", []))

# Line 247-251, UPDATE invoke parameters:
result = await structured_llm.ainvoke(
    self.extraction_prompt.format_messages(
        query=query,
        categories=categories_str,
        entity_types=entity_types_str,
        sources=sources_str  # ← ADD THIS!
    )
)
```

#### 1.2 filter_prompt 수정
```python
# Line 214, ADD:
Available entity types: {entity_types}
Available sources: {sources}  # ← ADD THIS!

# Line 279, ADD:
sources_str = ", ".join(metadata.get("available_sources", []))

# Line 281-286, UPDATE invoke parameters:
result = await structured_llm.ainvoke(
    self.filter_prompt.format_messages(
        query=query,
        extraction=extraction.model_dump(),
        entity_types=entity_types_str,
        sources=sources_str  # ← ADD THIS!
    )
)
```

### Phase 2: 프롬프트 개선 ✅

#### 2.1 Source Extraction 규칙 명확화
```python
# Line 166, UPDATE:
3. Source: ONLY if specific document name is mentioned
   Rule: Extract source ONLY when document/manual/guide is explicitly mentioned
   Examples:
   - "엔진 오일 교체" → NO source (just a topic)
   - "매뉴얼에서 오일 교체" → YES source (document mentioned)
   - "사용 설명서 50페이지" → YES source (document mentioned)
   - "안전 기능" → NO source (just a feature)
   
   Document indicators: "매뉴얼", "manual", "guide", "설명서", "문서", "handbook"
```

#### 2.2 잘못된 예시 수정
```python
# Line 195-211, UPDATE EXAMPLES:

# REMOVE this bad example:
Query: "GV80 매뉴얼에서 안전벨트 관련 그림 찾아줘"
Extraction: {source_mentioned: "GV80", ...}  # WRONG!
Filter: {sources: ["gv80_manual.pdf"], ...}  # WRONG!

# REPLACE with correct example:
Query: "매뉴얼에서 안전벨트 관련 그림 찾아줘"
Extraction: {source_mentioned: "manual", entity_type: "image", keywords: ["안전벨트"]}
Filter: {entity: {"type": "image"}}  # Let search use all sources or match from available_sources

Query: "엔진 오일 교체 주기"
Extraction: {keywords: ["엔진", "오일", "교체", "주기"]}
Filter: {}  # EMPTY - no document mentioned, search all

Query: "owner's manual page 50"
Extraction: {source_mentioned: "owner's manual", page_numbers: [50]}
Filter: {pages: [50]}  # Source will be matched from available_sources list
```

#### 2.3 프롬프트에 Available Sources 활용 지시
```python
# Add to filter_prompt:
IMPORTANT: If source is mentioned, select ONLY from Available sources list.
Do not create new source names. If no exact match, leave sources empty.

Available sources: {sources}
```

### Phase 3: ~~Validation 추가~~ (제거됨) ❌
- 메타데이터를 제공받은 LLM이 올바른 선택을 할 것으로 신뢰
- 추가 validation 로직 불필요

### Phase 4: 에러 복구 (부분적) ✅

#### 4.1 Web Search 성공 시 Error 클리어
```python
# workflow/graph.py
# In _web_search_node method, after line 453:
if len(web_documents) > 0:
    result["error"] = None  # Clear any previous errors
    result["workflow_status"] = "continuing"
    logger.info(f"[WEB_SEARCH] Cleared previous errors after finding {len(web_documents)} documents")
```

#### 4.2 ~~Retrieval Non-Fatal~~ (거부됨) ❌
- Retrieval 0개는 명확한 에러
- Error raise 유지 (현재 동작 유지)

### Phase 5: ~~검색 개선~~ (제거됨) ❌
- AND 연산자 유지 (정확도 우선)
- 현재 검색 로직 유지

## 🧪 검증 계획

### Test Cases
```python
test_queries = [
    # Case 1: 차량 모델만 언급 (source 필터 없어야 함)
    {
        "query": "GV80 엔진 오일 교체 주기",
        "expected_source_filter": None,
        "expected_results": "> 0 documents"
    },
    
    # Case 2: 문서 명시적 언급 (source 필터 있어야 함)
    {
        "query": "GV80 매뉴얼에서 오일 교체 방법",
        "expected_source_filter": ["data/gv80_owners_manual_TEST6P.pdf"],
        "expected_results": "> 0 documents"
    },
    
    # Case 3: 일반 쿼리 (source 필터 없어야 함)
    {
        "query": "엔진 오일 권장 사양",
        "expected_source_filter": None,
        "expected_results": "> 0 documents"
    }
]
```

### Expected Behavior After Fix

1. **Query**: "GV80 엔진 오일 교체 주기"
   - Before: source filter = "gv80_manual.pdf" → 0 results ❌
   - After: NO source filter → searches all → finds results ✅

2. **Error Recovery**:
   - Before: Error persists after web search → workflow fails ❌
   - After: Error cleared on web search success → workflow continues ✅

3. **Search Quality**:
   - AND operator maintained for precision ✅
   - Fatal errors maintained for clear failures ✅

## 📊 구현 우선순위

### Must Fix (Critical):
1. **Phase 1**: 메타데이터 전달 - 근본 원인 해결
2. **Phase 2.2**: 잘못된 예시 수정 - LLM 학습 교정
3. **Phase 4.1**: Error 클리어 - 워크플로우 연속성

### Should Fix (Important):
1. **Phase 2.1**: Source extraction 규칙 명확화
2. **Phase 2.3**: Available sources 활용 지시

### Won't Fix (By Design):
1. ❌ Validation 로직 - LLM 신뢰
2. ❌ OR 연산자 - 정확도 유지
3. ❌ Non-fatal retrieval - 에러 명확성

## 🎯 기대 효과

이 수정으로:
1. **정확한 소스 선택**: LLM이 실제 DB 소스 목록에서 선택
2. **불필요한 필터 제거**: 차량 모델만으로는 필터 생성 안함
3. **워크플로우 연속성**: Web search 후 정상 진행
4. **정확도 유지**: AND 연산자와 strict error handling 유지

## 📝 구현 노트

### 주의사항
- 차량 모델을 특정하지 않고 일반적인 패턴 사용
- 메타데이터를 신뢰하고 과도한 validation 피함
- 정확도를 위해 strict 모드 유지

### 핵심 원칙
> "LLM에게 정확한 정보(메타데이터)를 제공하면, 올바른 판단을 한다"

이것이 최소한의 변경으로 최대 효과를 얻는 접근법입니다.