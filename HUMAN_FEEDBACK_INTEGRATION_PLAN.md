# Human Feedback & Entity 통합 개선 계획

작성일: 2025-01-18 (Entity 통합 추가됨)
분석 방법: Sequential Thinking + Deep Code Analysis

## 1. 현재 상황 분석

### 1.1 Human Feedback 필드 현황
- **DB 스키마**: `human_feedback TEXT DEFAULT ''` 정의됨
- **현재 데이터**: 0개 문서 (필드는 존재하나 비어있음)
- **데이터 타입**: 텍스트 형식의 사람 검증/수정 정보 저장용

### 1.2 Entity 필드 현황
- **DB 스키마**: `entity JSONB` 정의됨
- **현재 데이터**: 테이블/그림에 구조화된 데이터 존재
- **데이터 구조**:
  ```json
  {
    "title": "제목",
    "details": "상세 설명",
    "keywords": ["키워드1", "키워드2"],
    "hypothetical_questions": ["예상 질문1", "예상 질문2"]
  }
  ```

### 1.3 현재 시스템의 문제점

#### 검색 시스템
- ❌ `search_vector_korean/english` 생성 시 human_feedback 미포함
- ❌ Entity keywords와 hypothetical_questions 미활용
- ❌ 키워드 검색 대상에서 제외
- ⚠️ SQL에서는 가져오지만 활용하지 않음

#### Retrieval 노드
- ❌ Document metadata에 human_feedback 미포함
- ✅ Entity는 metadata에 포함되나 활용 안됨
- ❌ 검색 신뢰도 계산에 미반영

#### Synthesis 노드
- ❌ LLM 프롬프트에 human_feedback 미제공
- ❌ Entity 구조화 정보 미활용 (테이블/그림 설명)
- ❌ 답변 생성 시 오직 5개 필드만 사용 (source, page, category, page_content, caption)

#### 품질 검증 노드
- ❌ HallucinationCheck에서 ground truth로 미활용
- ❌ Entity 구조화 데이터로 사실 확인 미수행
- ❌ AnswerGrader에서 품질 기준으로 미사용

---

## 2. 개선 목표

1. **검색 품질 향상**: Human feedback과 Entity keywords/questions 검색 포함
2. **답변 신뢰도 향상**: Human 검증 정보 > Entity 구조화 정보 > Raw content 우선순위
3. **구조화 정보 활용**: Entity의 테이블/그림 정보를 적절한 형식으로 렌더링
4. **환각 방지 강화**: Human feedback과 Entity를 ground truth로 활용
5. **점진적 통합**: 기존 시스템 안정성 유지하며 단계별 적용

---

## 3. 3단계 구현 계획

### Phase 1: 즉시 구현 가능 (Low Risk) ✅

**목표**: 기존 로직 변경 없이 human_feedback과 entity 정보 노출

#### 1.1 Retrieval 노드 개선
```python
# workflow/nodes/retrieval.py (line 227-237)
# _convert_to_document 메서드 수정

metadata = {
    "source": result.get("source", ""),
    "page": result.get("page", 0),
    "category": result.get("category", ""),
    "id": result.get("id", ""),
    "caption": result.get("caption", ""),
    "entity": result.get("entity"),
    "similarity": result.get("similarity"),
    "rank": result.get("rank"),
    "rrf_score": result.get("rrf_score"),
    "human_feedback": result.get("human_feedback", "")  # ✅ 추가
}
```

#### 1.2 Synthesis 노드 개선 (Entity 중점)
```python
# workflow/nodes/synthesis.py (line 122-131)
# document_formatter_prompt 수정

self.document_formatter_prompt = """
[{idx}] Document Reference:
- Source: {source}
- Page: {page}
- Category: {category}
- Content: {content}
{caption}
{entity_info}      # ✅ Entity 구조화 정보 추가
{human_feedback}   # ✅ Human feedback 추가
---
Note: Use [{idx}] when citing this document in your answer.
"""

# _format_documents 메서드 수정 (line 151-166)
# Entity와 human_feedback 처리 추가
def _format_entity_info(self, metadata: dict) -> str:
    """Entity 정보를 적절한 형식으로 포맷팅"""
    entity = metadata.get("entity")
    if not entity:
        return ""
    
    category = metadata.get("category", "")
    
    # 테이블인 경우: 마크다운 테이블로 렌더링
    if category == "table" and entity:
        entity_text = "- Table: "
        if entity.get("title"):
            entity_text += f"{entity['title']}\n"
        if entity.get("details"):
            entity_text += f"  Details: {entity['details']}\n"
        if entity.get("keywords"):
            entity_text += f"  Keywords: {', '.join(entity['keywords'])}\n"
        return entity_text
    
    # 그림인 경우: 설명 포함
    elif category == "figure" and entity:
        entity_text = "- Figure: "
        if entity.get("title"):
            entity_text += f"{entity['title']}\n"
        if entity.get("details"):
            entity_text += f"  Description: {entity['details']}\n"
        return entity_text
    
    return ""

# 포맷팅 시 entity 정보 포함
human_feedback_text = ""
if metadata.get("human_feedback") and metadata.get("human_feedback").strip():
    human_feedback_text = f"- Human Verified: {metadata['human_feedback']}"

entity_info_text = self._format_entity_info(metadata)  # ✅ Entity 포맷팅

formatted_doc = self.document_formatter_prompt.format(
    idx=idx,
    source=metadata.get("source", "Unknown"),
    page=metadata.get("page", "N/A"),
    category=metadata.get("category", "Unknown"),
    content=content,
    caption=caption_text,
    entity_info=entity_info_text,       # ✅ Entity 정보 추가
    human_feedback=human_feedback_text   # ✅ Human feedback 추가
)
```

**영향도**: 최소 (기존 로직 변경 없음)
**테스트**: human_feedback 없는 경우도 정상 작동

---

### Phase 2: 검색 시스템 개선 (Medium Risk) ⚠️

**목표**: Human feedback과 Entity keywords/questions을 검색 대상에 포함

#### 2.1 데이터 인제스트 수정
```python
# scripts/2_phase1_ingest_documents.py (line 135-140)
# search_vector 생성 시 human_feedback과 entity 포함

# Entity에서 검색 가능한 텍스트 추출
def extract_entity_text(entity):
    """Entity에서 검색 가능한 텍스트 추출"""
    if not entity:
        return ""
    
    entity_texts = []
    if entity.get("title"):
        entity_texts.append(entity["title"])
    if entity.get("details"):
        entity_texts.append(entity["details"])
    if entity.get("keywords"):
        entity_texts.extend(entity["keywords"])
    if entity.get("hypothetical_questions"):
        entity_texts.extend(entity["hypothetical_questions"])
    
    return " ".join(entity_texts)

# 한국어 검색 텍스트
entity_text = extract_entity_text(doc_dict.get("entity"))
korean_search_text = (
    doc_dict.get("contextualize_text", "") + " " + 
    doc_dict.get("page_content", "") + " " +
    doc_dict.get("caption", "") + " " +
    entity_text + " " +                     # ✅ Entity 추가
    doc_dict.get("human_feedback", "")      # ✅ Human feedback 추가
)
```

#### 2.2 인제스트 스크립트 내 Search Vector 생성 수정
```python
# scripts/2_phase1_ingest_documents.py (line 135-140 수정)
# 기존 인제스트 코드에 entity와 human_feedback 포함

# Entity에서 검색 가능한 텍스트 추출 함수 (Python에서 처리)
def extract_entity_text(entity):
    """Entity JSONB에서 검색 가능한 텍스트 추출"""
    if not entity:
        return ""
    
    entity_texts = []
    if isinstance(entity, dict):
        if entity.get("title"):
            entity_texts.append(str(entity["title"]))
        if entity.get("details"):
            entity_texts.append(str(entity["details"]))
        if entity.get("keywords") and isinstance(entity["keywords"], list):
            entity_texts.extend([str(k) for k in entity["keywords"]])
        if entity.get("hypothetical_questions") and isinstance(entity["hypothetical_questions"], list):
            entity_texts.extend([str(q) for q in entity["hypothetical_questions"]])
    
    return " ".join(entity_texts)

# Search vector 생성 시 entity와 human_feedback 포함
entity_text = extract_entity_text(doc_dict.get("entity"))

# 한국어 검색 벡터 생성
korean_search_text = (
    doc_dict.get("contextualize_text", "") + " " + 
    doc_dict.get("page_content", "") + " " +
    doc_dict.get("caption", "") + " " +
    entity_text + " " +                          # ✅ Entity 추가
    doc_dict.get("human_feedback", "")           # ✅ Human feedback 추가
)

# 영어 검색 벡터도 동일하게 수정
english_search_text = (
    doc_dict.get("translation_text", "") + " " +
    entity_text + " " +                          # ✅ Entity 추가  
    doc_dict.get("human_feedback", "")           # ✅ Human feedback 추가
)
```

**참고**: 처음부터 DB를 생성할 때 올바른 search_vector가 생성되도록 인제스트 스크립트 자체를 수정합니다. 별도의 재인덱싱 스크립트는 필요없습니다.

**영향도**: 중간 (재인덱싱 필요)
**테스트**: 검색 결과 비교 테스트 필요

---

### Phase 3: 품질 검증 개선 (Low Risk) 🎯

**목표**: Human feedback과 Entity를 품질 검증의 ground truth로 활용

#### 3.1 HallucinationCheckNode 개선 (기존 로직 강화)
```python
# workflow/nodes/hallucination.py
# 기존 _format_documents_for_checking 메서드를 유지하면서 강화

def _format_documents_for_checking(self, documents: List[Document]) -> str:
    """문서를 검증용 텍스트로 포맷팅 (기존 구조 유지 + entity/human_feedback 추가)"""
    formatted = []
    for idx, doc in enumerate(documents, 1):
        metadata = doc.metadata
        
        # Human feedback 추가 (있는 경우만)
        human_feedback_line = ""
        if metadata.get("human_feedback") and metadata.get("human_feedback").strip():
            human_feedback_line = f"- Human Feedback: {metadata['human_feedback']}\n"
        
        # Entity 정보 추가 (table/figure인 경우만)
        entity_info = ""
        entity = metadata.get("entity")
        if entity and metadata.get("category") in ["table", "figure"]:
            entity_lines = []
            if entity.get("title"):
                entity_lines.append(f"- Entity Title: {entity['title']}")
            if entity.get("details"):
                entity_lines.append(f"- Entity Details: {entity['details']}")
            if entity.get("keywords") and isinstance(entity["keywords"], list):
                entity_lines.append(f"- Entity Keywords: {', '.join(entity['keywords'])}")
            if entity_lines:
                entity_info = "\n".join(entity_lines) + "\n"
        
        # 기존 구조 유지하면서 추가 정보 포함
        formatted.append(f"""
Document {idx}:
- Source: {metadata.get('source', 'Unknown')}
- Page: {metadata.get('page', 'N/A')}
- Category: {metadata.get('category', 'Unknown')}
{human_feedback_line}{entity_info}- Full Content:
{doc.page_content}
---""")
        
    return "\n".join(formatted)
```

**참고**: 기존 메서드 구조를 완전히 유지하면서 human_feedback과 entity 정보만 조건부로 추가합니다. 이렇게 하면 기존 로직이 깨지지 않으면서도 추가 정보를 활용할 수 있습니다.

#### 3.2 Synthesis 프롬프트 개선
```python
# workflow/nodes/synthesis.py (line 49-98)
# synthesis_prompt 수정

"""Guidelines:
1. Base your answer ONLY on the provided documents
2. **Priority Order**: Human Verification > Entity Structured Data > Raw Content ✅
3. If human feedback conflicts with other documents, trust human feedback
4. For tables and figures, use the structured entity information when available
5. Include entity keywords and details in your response when relevant
6. Cite sources using reference numbers [1], [2], etc.
..."""
```

**영향도**: 낮음 (선택적 개선)
**테스트**: Human feedback과 Entity 정보가 있는/없는 케이스 비교

---

## 4. 구현 우선순위 및 일정

### 즉시 구현 (Day 1)
1. ✅ Phase 1.1: Retrieval 노드 metadata 추가 (5분)
2. ✅ Phase 1.2: Synthesis 노드 포맷팅 개선 (10분)
3. ✅ 기본 테스트 실행

### 단기 구현 (Week 1)
4. ⚠️ Phase 2.1: 인제스트 스크립트 수정
5. ⚠️ Phase 2.2: 인제스트 스크립트 내 extract_entity_text 함수 추가
6. ⚠️ 검색 성능 테스트

### 중기 구현 (Week 2)
7. 🎯 Phase 3.1: HallucinationCheck 기존 로직 강화
8. 🎯 Phase 3.2: Synthesis 프롬프트 최적화

---

## 5. 테스트 계획

### 단위 테스트
```python
# scripts/test_human_feedback_integration.py

async def test_retrieval_with_feedback():
    """Human feedback이 metadata에 포함되는지 확인"""
    pass

async def test_synthesis_with_feedback():
    """Human feedback이 답변 생성에 활용되는지 확인"""
    pass

async def test_search_with_feedback():
    """Human feedback이 검색되는지 확인"""
    pass
```

### 통합 테스트
1. Human feedback 없는 문서만으로 워크플로우 실행
2. Human feedback 있는 문서 추가 후 동일 쿼리 실행
3. 결과 비교 및 개선도 측정

---

## 6. 리스크 및 주의사항

### 리스크
1. **재인덱싱 부하**: Phase 2에서 전체 문서 재인덱싱 필요
2. **성능 영향**: search_vector 크기 증가로 인한 검색 속도 저하 가능
3. **하위 호환성**: human_feedback 없는 기존 데이터와의 호환성

### 완화 방안
1. **점진적 적용**: Phase별 단계적 구현
2. **조건부 처리**: human_feedback 없어도 정상 작동
3. **롤백 계획**: 각 Phase별 독립적 롤백 가능
4. **모니터링**: 성능 메트릭 지속 관찰

---

## 7. 예상 효과

### 정량적 효과 (Dual Integration)
- 검색 정확도: +10-15% (entity keywords/questions 포함)
- 답변 신뢰도: +15-20% (structured entity data 활용)
- 테이블/그림 정확도: +30-40% (entity 구조화 정보 활용)
- 환각 감소: -25-35% (dual ground truth 활용)
- 쿼리 매칭률: +20% (hypothetical_questions 활용)

### 정성적 효과
- 구조화된 정보 제공 (테이블, 그림 설명)
- 사용자 신뢰도 향상
- 점진적 품질 개선 가능
- Human-in-the-loop + AI-structured 하이브리드 시스템

---

## 8. 실행 명령어 예시

### Phase 1 구현
```bash
# 1. Retrieval 노드 수정
vim workflow/nodes/retrieval.py +227

# 2. Synthesis 노드 수정  
vim workflow/nodes/synthesis.py +122

# 3. 테스트 실행
python scripts/test_retrieval_node.py
python scripts/test_synthesis_node.py
```

### Phase 2 구현
```bash
# 1. 인제스트 스크립트 수정 (extract_entity_text 함수 추가)
vim scripts/2_phase1_ingest_documents.py +135

# 2. DB 재생성 (수정된 스크립트로 처음부터 인제스트)
python scripts/2_phase1_ingest_documents.py

# 3. 검색 테스트
python scripts/test_retrieval_real_data.py
```

---

## 결론

Human Feedback과 Entity의 **이중 통합(Dual Integration)**으로 시스템 성능을 획기적으로 개선합니다:

### 통합 전략
1. **Phase 1**: 즉시 구현 가능
   - Human feedback metadata 추가
   - **Entity 구조화 정보 렌더링** (테이블/그림 설명)
   - Synthesis 노드에서 즉시 활용 가능

2. **Phase 2**: 검색 시스템 개선
   - Human feedback 검색 포함
   - **Entity keywords/questions 검색 활용**
   - 재인덱싱으로 검색 품질 대폭 향상

3. **Phase 3**: 품질 검증 강화
   - Human feedback을 primary ground truth로
   - **Entity를 secondary ground truth로**
   - 이중 검증으로 환각 최소화

### 핵심 개선사항
- **정보 우선순위**: Human Feedback > Entity Structured Data > Raw Content
- **테이블/그림 처리**: Entity 정보로 구조화된 렌더링
- **검색 강화**: Keywords와 hypothetical_questions 활용
- **환각 방지**: 이중 ground truth 시스템

각 단계는 독립적으로 구현/테스트/롤백 가능하며, 기존 시스템의 안정성을 해치지 않습니다.