# SynthesisResult Schema Enhancement Plan

## 현황 분석

### 현재 SynthesisResult 스키마 (5개 필드)
```python
class SynthesisResult(BaseModel):
    answer: str                    # 생성된 답변 텍스트
    confidence: float              # 신뢰도 점수 (0.0-1.0)
    sources_used: List[str]        # 사용된 출처 리스트 ('[1]', '[2]' 형식)
    key_points: List[str]          # 핵심 포인트 리스트
    references_table: str          # 참조 테이블 (markdown 형식)
```

### 실제 처리되는 데이터 (수집되지만 손실되는 정보)
1. **페이지 이미지 정보** (_collect_page_images)
2. **Entity 구조화 데이터** (똑딱이, table, figure)
3. **Human Feedback** (검증된 정보)
4. **문서 메타데이터** (source, page, category)
5. **품질 검증 정보** (hallucination_check, answer_grade)
6. **재시도 정보** (retry_count, feedback)
7. **언어 정보** (detected_language)
8. **문서별 상세 정보** (caption, contextualize_text)

## 문제점 분석

### 1. 구조적 불일치
- **프롬프트 지시사항**: 페이지 이미지 포함 지시 (lines 81-97)
- **스키마 제약**: structured_output이 페이지 이미지 필드를 지원하지 않음
- **결과**: LLM이 페이지 이미지를 포함하려 해도 스키마가 차단

### 2. 데이터 손실 체인
```
SynthesisResult 생성 → final_answer만 추출 → 나머지 필드 손실
                    → sources_used 손실
                    → key_points 손실
                    → references_table 손실
                    → page_images 없음
```

### 3. Entity 정보 미활용
- 똑딱이(PPT 삽입 문서) 메타데이터 손실
- 테이블/그림 구조화 정보 손실
- Human feedback 우선순위 정보 손실

## 개선 계획

### Phase 1: SynthesisResult 스키마 확장
재분석..

#### 2.2 새로운 헬퍼 메서드 추가
```python
def _collect_special_entities(self, documents: List[Document]) -> Dict[str, List[EntityInfo]]:
    """문서에서 특별 엔티티 수집 (똑딱이, 테이블, 그림)"""
    entities = {
        "똑딱이": [],
        "table": [],
        "figure": [],
        "image": []
    }
    
    for doc in documents:
        entity = doc.metadata.get("entity")
        if entity and isinstance(entity, dict):
            entity_type = entity.get("type")
            if entity_type in entities:
                entities[entity_type].append(EntityInfo(**entity))
    
    return {k: v for k, v in entities.items() if v}  # 비어있지 않은 것만 반환

def _collect_human_feedback(self, documents: List[Document]) -> List[str]:
    """Human feedback 수집"""
    feedback_list = []
    for doc in documents:
        feedback = doc.metadata.get("human_feedback")
        if feedback and isinstance(feedback, str) and feedback.strip():
            feedback_list.append(feedback)
    return feedback_list

def _create_document_references(self, documents: List[Document]) -> List[DocumentReference]:
    """문서 참조 상세 정보 생성"""
    references = []
    for idx, doc in enumerate(documents, 1):
        metadata = doc.metadata
        ref = DocumentReference(
            reference_number=f"[{idx}]",
            source=metadata.get("source", "Unknown"),
            page=metadata.get("page", 0),
            category=metadata.get("category", "Unknown"),
            content_summary=doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
            entity=EntityInfo(**metadata["entity"]) if metadata.get("entity") else None,
            human_feedback=metadata.get("human_feedback"),
            has_image=bool(metadata.get("page_image_path"))
        )
        references.append(ref)
    return references

def _format_page_images_section(self, page_images: List[Dict]) -> str:
    """페이지 이미지 섹션 포맷팅"""
    if not page_images:
        return ""
    
    section = "\n\n## 참조 페이지 이미지 (Referenced Page Images)\n"
    current_source = None
    
    for img in page_images:
        if img['source'] != current_source:
            current_source = img['source']
            section += f"\n### {current_source}\n"
        
        caption = f" - {img.get('caption')}" if img.get('caption') else ""
        section += f"![Page {img['page']}]({img['path']}){caption}\n"
    
    return section
```

### Phase 3: State 업데이트 수정

#### 3.1 __call__ 메서드 return 수정
```python
def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
    # ... 기존 로직 ...
    
    # EnhancedSynthesisResult 사용
    synthesis_result = self._generate_answer_with_fallback(query, documents)
    
    # 모든 구조화된 데이터 포함
    result = {
        "messages": messages,
        "final_answer": synthesis_result.answer_with_images or synthesis_result.answer,
        "confidence_score": synthesis_result.confidence,
        "metadata": {
            **metadata,
            "synthesis": {
                "documents_used": len(documents),
                "sources_cited": len(synthesis_result.sources_used),
                "key_points": synthesis_result.key_points,
                "references_table": synthesis_result.references_table,
                "page_images": [img.dict() for img in synthesis_result.page_images] if synthesis_result.page_images else [],
                "special_entities": {
                    k: [e.dict() for e in v] 
                    for k, v in synthesis_result.special_entities.items()
                } if synthesis_result.special_entities else {},
                "human_feedback_used": synthesis_result.human_feedback_used,
                "quality_metrics": synthesis_result.quality_metrics.dict() if synthesis_result.quality_metrics else None,
                "detected_language": synthesis_result.detected_language,
                "document_references": [ref.dict() for ref in synthesis_result.document_references] if synthesis_result.document_references else []
            }
        },
        "retry_count": retry_count
    }
    
    return result
```

### Phase 4: 프롬프트 업데이트

#### 4.1 Synthesis 프롬프트 수정
```python
synthesis_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant that generates comprehensive answers...

IMPORTANT CHANGES:
1. The output schema now supports page_images field - populate it with all referenced page images
2. Include special_entities for all 똑딱이, tables, and figures found
3. Populate document_references with detailed information for each citation
4. Track human_feedback_used when prioritizing human-verified information
5. Set quality_metrics based on your self-assessment
6. Detect and set the primary language used

Page Image Inclusion:
- Collect ALL page images from documents you cite
- Add them to the page_images field in the structured output
- The system will automatically append them to your answer

Special Entity Handling:
- When you find 똑딱이 entities, add them to special_entities["똑딱이"]
- Include tables in special_entities["table"]
- Include figures in special_entities["figure"]
- Always mention 똑딱이 as "PPT 삽입 문서" in your answer text
"""),
    ("human", "{query}"),
    ("human", "Documents:\n{documents}")
])
```

## 구현 우선순위

### 즉시 적용 (High Priority) - Day 1
1. EnhancedSynthesisResult 스키마 정의
2. _collect_page_images 메서드 수정
3. answer_with_images 필드 구현

### 단기 적용 (Medium Priority) - Day 2-3
4. Special entities 수집 로직
5. Document references 생성
6. Human feedback 우선순위 처리
7. Quality metrics 통합

### 장기 개선 (Low Priority) - Day 4-5
8. 프롬프트 최적화
9. 언어 감지 개선
10. 메타데이터 구조 정리

## 예상 효과

### 정보 완전성
- 페이지 이미지 100% 포함
- 똑딱이 entity 100% 언급
- Human feedback 100% 우선 반영

### 추적성 향상
- 모든 인용 출처 상세 정보 제공
- 문서별 entity 정보 보존
- 품질 메트릭 기록

### 사용자 경험
- 시각적 참조 자료 제공
- PPT 삽입 문서 명확한 구분
- 신뢰도 높은 답변 생성

## 위험 요소 및 완화 방안

### 1. 스키마 복잡도 증가
- **위험**: 너무 많은 필드로 인한 LLM 혼란
- **완화**: Optional 필드 활용, 단계적 롤아웃

### 2. 토큰 사용량 증가
- **위험**: 구조화된 출력이 커져 비용 증가
- **완화**: 필요한 필드만 선택적 포함

### 3. 하위 호환성
- **위험**: 기존 코드와 호환성 문제
- **완화**: 기존 필드 유지, 새 필드는 Optional

## 테스트 계획

```python
# test_enhanced_synthesis.py
def test_page_images_inclusion():
    """페이지 이미지가 포함되는지 테스트"""
    # 구현...

def test_ddokddak_entity_mention():
    """똑딱이 entity가 언급되는지 테스트"""
    # 구현...

def test_human_feedback_priority():
    """Human feedback이 우선되는지 테스트"""
    # 구현...

def test_document_references_completeness():
    """모든 참조 문서 정보가 포함되는지 테스트"""
    # 구현...
```

## 구현 체크리스트

- [ ] EnhancedSynthesisResult 스키마 정의
- [ ] _collect_special_entities 메서드 구현
- [ ] _collect_human_feedback 메서드 구현
- [ ] _create_document_references 메서드 구현
- [ ] _format_page_images_section 메서드 구현
- [ ] _generate_answer_with_fallback 수정
- [ ] __call__ 메서드 return 값 수정
- [ ] synthesis_prompt 업데이트
- [ ] 테스트 스크립트 작성
- [ ] 통합 테스트 실행
- [ ] 문서 업데이트