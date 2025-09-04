# 똑딱이 Entity Type 언급 개선 계획

## 현황 분석

### 발견된 문제
- **문제**: entity type이 "똑딱이"인 문서가 검색되지만 답변에서 언급되지 않음
- **영향**: 사용자가 PPT 삽입 문서 정보를 인지하지 못함

### 기술적 분석 결과

#### 1. 데이터베이스 현황
- 총 18개의 "똑딱이" type 문서 존재
- 주로 "디지털정부혁신_추진계획.pdf"의 page 3에 분포
- 모두 정상적으로 entity 정보 포함

#### 2. 코드 분석
- `synthesis.py`의 `_format_entity_info()` 메서드에 이미 "똑딱이" 처리 로직 존재 (182-198번 줄)
- 포맷: "PPT Embedded Document (똑딱이)"로 표시
- title, details, keywords, hypothetical_questions 정보 포함

#### 3. 문제점 식별
- **핵심 문제**: synthesis 프롬프트에서 "똑딱이" type을 명시적으로 언급하지 않음
- 현재 프롬프트는 "tables/figures"만 예시로 언급
- LLM이 "똑딱이" type의 중요성을 인지하지 못함

## 수정 계획

### Phase 1: Synthesis Node 프롬프트 개선

#### 1. 우선순위 계층에 "똑딱이" 추가
```python
# 현재 (synthesis.py 50-53번 줄)
CRITICAL - Information Priority Hierarchy:
1. **HIGHEST PRIORITY - Human Verified Content**: ...
2. **HIGH PRIORITY - Structured Entity Data**: Table and Figure information...
3. **STANDARD PRIORITY - Document Content**: ...

# 수정 후
CRITICAL - Information Priority Hierarchy:
1. **HIGHEST PRIORITY - Human Verified Content**: ...
2. **HIGH PRIORITY - Structured Entity Data**: 
   - **PPT Embedded Documents (똑딱이)**: Special document type with structured metadata
   - **Tables**: Structured tabular data with titles and keywords
   - **Figures**: Visual information with descriptions
3. **STANDARD PRIORITY - Document Content**: ...
```

#### 2. Guidelines에 "똑딱이" 언급 규칙 추가
```python
# synthesis.py 55-71번 줄에 추가
Guidelines:
...
3. When entity information exists (tables/figures/똑딱이), use the structured data to provide precise details
...
NEW:
11. **CRITICAL - 똑딱이 Entity Mention**: 
    - When a document has entity type "똑딱이", ALWAYS mention it's a "PPT 삽입 문서" or "PPT Embedded Document"
    - Include the document title from entity metadata
    - Mention that this is a specially structured document from PPT
    - Example: "이 정보는 'PPT 삽입 문서(똑딱이)'인 [제목]에서 확인할 수 있습니다"
```

### Phase 2: Document Formatter 개선

#### 문서 포맷터에서 "똑딱이" 강조
```python
# synthesis.py _format_documents 메서드 수정
# entity_info 출력 부분에서 "똑딱이"를 더 명확하게 표시

formatted_doc = self.document_formatter_prompt.format(
    ...
    entity_info=entity_info_text,  # 이미 "PPT Embedded Document (똑딱이)" 포함
    ...
)

# entity_info가 "똑딱이"인 경우 추가 강조
if "똑딱이" in entity_info_text:
    formatted_doc = formatted_doc.replace(
        "- PPT Embedded Document (똑딱이):",
        "- **[SPECIAL] PPT Embedded Document (똑딱이)**:"
    )
```

### Phase 3: Hallucination Check 개선

#### Entity Type 검증 추가
```python
# hallucination.py에 entity type 검증 로직 추가
def _check_entity_mentions(self, answer: str, documents: List[Document]) -> bool:
    """
    답변에서 중요한 entity type들이 언급되었는지 확인
    """
    has_ddokddak = any(
        doc.metadata.get("entity", {}).get("type") == "똑딱이" 
        for doc in documents
    )
    
    if has_ddokddak:
        # 답변에서 "똑딱이", "PPT", "삽입 문서" 중 하나라도 언급했는지 확인
        mentioned = any(
            keyword in answer 
            for keyword in ["똑딱이", "PPT", "삽입 문서", "embedded"]
        )
        
        if not mentioned:
            logger.warning("[HALLUCINATION] 똑딱이 entity가 있지만 언급되지 않음")
            # 경고만 하고 hallucination으로 처리하지는 않음 (soft check)
    
    return True
```

### Phase 4: 검증 및 테스트

#### 테스트 스크립트 작성
```python
# test_ddokddak_entity_mention.py
def test_ddokddak_mention():
    """
    똑딱이 entity가 포함된 쿼리 테스트
    """
    queries = [
        "디지털 정부혁신 추진계획에 대해 알려줘",
        "디지털 정부혁신의 개요를 설명해줘",
        "page 3에 있는 내용을 요약해줘"
    ]
    
    for query in queries:
        # 워크플로우 실행
        result = run_workflow(query)
        
        # 답변에 "똑딱이" 또는 관련 키워드 포함 확인
        assert any(
            keyword in result.answer 
            for keyword in ["똑딱이", "PPT", "삽입 문서"]
        ), f"Query '{query}'에서 똑딱이 언급 실패"
```

## 구현 우선순위

1. **즉시 적용 (High Priority)**
   - Synthesis 프롬프트 수정 (Phase 1)
   - 영향도: 높음, 구현 난이도: 낮음

2. **단기 적용 (Medium Priority)**
   - Document Formatter 개선 (Phase 2)
   - Hallucination Check 개선 (Phase 3)
   - 영향도: 중간, 구현 난이도: 중간

3. **검증 단계**
   - 테스트 스크립트 작성 및 실행 (Phase 4)
   - 실제 쿼리로 검증

## 예상 효과

1. **사용자 경험 개선**
   - PPT 삽입 문서임을 명확히 인지
   - 문서의 특별한 구조와 중요성 파악

2. **정보 투명성 향상**
   - 문서 출처와 유형 명확화
   - 메타데이터 활용도 증가

3. **답변 품질 향상**
   - 더 구체적이고 정확한 답변 생성
   - 문서 유형별 맞춤 설명 제공

## 위험 요소

1. **과도한 언급**: 모든 답변에서 "똑딱이"를 반복적으로 언급할 수 있음
   - 완화 방안: 처음 언급할 때만 상세 설명, 이후는 간단히 참조

2. **프롬프트 복잡도 증가**: 너무 많은 규칙으로 인한 성능 저하
   - 완화 방안: 핵심 규칙만 추가, 나머지는 예시로 제공

## 구현 일정

- **Day 1**: Synthesis 프롬프트 수정 및 테스트
- **Day 2**: Document Formatter 및 Hallucination Check 개선
- **Day 3**: 통합 테스트 및 검증
- **Day 4**: 프로덕션 배포 및 모니터링