# State Dependency Analysis - MVP Workflow

## Workflow Sequence
```
planning → subtask_executor → retrieval → (web_search) → synthesis → hallucination_check → answer_grader → END
```

## 1. PlanningAgentNode

### Reads from State:
- `query` (required) - 사용자 쿼리

### Writes to State:
- `subtasks` - 서브태스크 리스트 [{query, description, status: "pending"}]
- `current_subtask_idx` - 현재 서브태스크 인덱스 (0)
- `metadata` - {"strategy": plan.strategy}

### Errors:
- `error` - 실패 시
- `workflow_status` - "failed"
- `warnings` - 경고 메시지

---

## 2. SubtaskExecutorNode

### Reads from State:
- `subtasks` - 서브태스크 리스트
- `current_subtask_idx` - 현재 처리할 서브태스크 인덱스
- `metadata` - 기존 메타데이터

### Writes to State:
- `subtasks` - 업데이트된 서브태스크 (status: "executing", query_variations, extracted_info 추가)
- `search_filter` - MVPSearchFilter dict (필터가 있는 경우)
- `metadata` - 서브태스크별 메타데이터 추가
- `current_query_variations` - 쿼리 변형 리스트 (Retrieval Node용)
- `workflow_status` - "completed" (모든 서브태스크 완료 시)

### Errors:
- `error` - DB 연결 실패 등
- `workflow_status` - "failed"
- `warnings` - 경고 메시지

---

## 3. RetrievalNode

### Reads from State:
- `query` (required) - 원본 쿼리
- `subtasks` - 서브태스크 리스트
- `current_subtask_idx` - 현재 서브태스크 인덱스
- `search_filter` - 검색 필터 (SubtaskExecutor에서 생성)
- `execution_time` - 기존 실행 시간
- `metadata` - 기존 메타데이터

### Writes to State:
- `documents` - 검색된 문서 리스트 (누적)
- `subtasks` - 서브태스크에 documents, status: "completed" 추가
- `search_language` - 감지된 언어
- `confidence_score` - 검색 신뢰도
- `execution_time` - retrieval 시간 추가
- `metadata` - retrieval 정보 추가

### Errors:
- `error` - 검색 실패
- `workflow_status` - "failed"
- `warnings` - 경고 메시지

---

## 4. Web Search Node (Optional)

### Reads from State:
- `query` - 원본 쿼리
- `subtasks` - 서브태스크 리스트
- `current_subtask_idx` - 현재 서브태스크 인덱스
- `documents` - 기존 문서 리스트
- `metadata` - 기존 메타데이터

### Writes to State:
- `documents` - 웹 검색 결과 추가 (누적)
- `metadata` - web_search_performed, web_search_results 추가

### Errors:
- `warnings` - 웹 검색 실패 경고

---

## 5. SynthesisNode

### Reads from State:
- `query` (required) - 원본 쿼리
- `subtasks` - 서브태스크 리스트
- `current_subtask_idx` - 현재 서브태스크 인덱스
- `documents` - 검색된 문서 리스트
- `metadata` - 기존 메타데이터

### Writes to State:
- `intermediate_answer` - 중간 답변 (서브태스크 처리 시)
- `final_answer` - 최종 답변 (전체 쿼리 처리 시)
- `confidence_score` - 답변 신뢰도
- `subtasks` - 서브태스크에 answer, status: "completed" 추가
- `metadata` - synthesis 정보 추가

### Errors:
- `error` - 합성 실패
- `workflow_status` - "failed"
- `warnings` - 경고 메시지

---

## 6. HallucinationCheckNode

### Reads from State:
- `query` (required) - 원본 쿼리
- `intermediate_answer` or `final_answer` - 체크할 답변
- `documents` - 검증용 문서
- `metadata` - 기존 메타데이터

### Writes to State:
- `hallucination_check` - QualityCheckResult {is_valid, score, reason, suggestions, needs_retry}
- `should_retry` - 재시도 필요 여부
- `retry_count` - 재시도 횟수 증가
- `metadata` - hallucination_check 정보 추가

### Errors:
- `error` - 체크 실패
- `workflow_status` - "failed"
- `warnings` - 경고 메시지

---

## 7. AnswerGraderNode

### Reads from State:
- `query` (required) - 원본 쿼리
- `intermediate_answer` or `final_answer` - 평가할 답변
- `documents` - 참고 문서
- `metadata` - 기존 메타데이터

### Writes to State:
- `answer_grade` - QualityCheckResult {is_valid, score, reason, suggestions, needs_retry}
- `should_retry` - 재시도 필요 여부
- `metadata` - answer_grade 정보 추가

### Errors:
- `error` - 평가 실패
- `workflow_status` - "failed"
- `warnings` - 경고 메시지

---

## 🔍 Critical Dependencies

### 1. **Planning → SubtaskExecutor**
✅ `subtasks` - Planning이 생성, SubtaskExecutor가 사용
✅ `current_subtask_idx` - Planning이 0으로 초기화, SubtaskExecutor가 읽음

### 2. **SubtaskExecutor → Retrieval**
✅ `search_filter` - SubtaskExecutor가 생성, Retrieval이 사용
✅ `current_query_variations` - SubtaskExecutor가 생성, Retrieval이 사용 가능 (현재 미사용)
✅ `subtasks` - SubtaskExecutor가 업데이트, Retrieval이 읽음

### 3. **Retrieval → Synthesis**
✅ `documents` - Retrieval이 생성/누적, Synthesis가 사용
✅ `subtasks` - Retrieval이 documents 추가, Synthesis가 읽음

### 4. **Synthesis → HallucinationCheck**
✅ `intermediate_answer`/`final_answer` - Synthesis가 생성, HallucinationCheck가 사용
✅ `documents` - Synthesis가 전달, HallucinationCheck가 검증용으로 사용

### 5. **HallucinationCheck → AnswerGrader**
✅ `intermediate_answer`/`final_answer` - 그대로 전달
✅ `documents` - 그대로 전달
✅ `retry_count` - HallucinationCheck가 설정, Graph가 확인

### 6. **AnswerGrader → END/Retry**
✅ `answer_grade` - AnswerGrader가 생성, Graph가 확인
✅ `should_retry` - AnswerGrader가 설정, Graph가 확인

---

## ⚠️ Potential Issues

### 1. **current_query_variations 미사용**
- SubtaskExecutor에서 생성하지만 Retrieval에서 사용하지 않음
- Multi-query 전략이 구현되지 않음

### 2. **서브태스크 순차 처리**
- 현재 한 번에 하나의 서브태스크만 처리
- `current_subtask_idx` 증가 로직이 누락될 수 있음
- Graph에서 subtask 완료 후 인덱스 증가 필요

### 3. **Retry Count 관리**
- `retry_count`가 초기화되지 않음
- Graph에서 retry 시 증가시켜야 함

### 4. **문서 누적 문제**
- Retrieval이 documents를 누적하는데, 중복 처리 필요할 수 있음

---

## 📋 Recommendations

1. **Graph에서 처리 필요**:
   - `current_subtask_idx` 증가 로직
   - `retry_count` 초기화 및 증가
   - 서브태스크 완료 판단

2. **Multi-Query 구현**:
   - RetrievalNode에서 `current_query_variations` 활용
   - 여러 쿼리로 검색 후 병합

3. **State 초기화**:
   - Graph의 initial_state에 필요한 필드 초기화 추가
   ```python
   initial_state = {
       "query": query,
       "workflow_status": "started",
       "metadata": {},
       "retry_count": 0,
       "documents": [],
       "execution_time": {}
   }
   ```

4. **문서 중복 제거**:
   - Retrieval에서 문서 ID 기반 중복 제거 로직 추가