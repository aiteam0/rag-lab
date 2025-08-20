# 🔍 State Flow Analysis - 현재 시스템 분석

> **작성일**: 2025-01-14
> **목적**: 현재 워크플로우의 State 흐름 파악 및 수정 계획 수립

## 📊 현재 워크플로우 구조

### 1. 전체 플로우
```
[START] → planning → subtask_executor → retrieval → synthesis → hallucination_check → answer_grader → [END]
```

### 2. 노드별 State 입출력 분석

#### Planning Node (`planning_agent.py`)
**입력 State 필드**:
- `query`: 사용자 원본 쿼리

**출력 State 필드**:
- `subtasks`: 생성된 서브태스크 리스트
- `current_subtask_idx`: 0으로 초기화
- `metadata`: planning 정보 추가
- `workflow_status`: "running"

#### Subtask Executor Node (`subtask_executor.py`)
**입력 State 필드**:
- `subtasks`: 서브태스크 리스트
- `current_subtask_idx`: 현재 처리할 인덱스

**출력 State 필드**:
- `query_variations`: Multi-Query 변형들
- `search_filter`: 검색 필터 (선택적)
- `subtasks`: 상태 업데이트 (status: "processing")
- `current_subtask_idx`: 다음 처리를 위해 업데이트

#### Retrieval Node (`retrieval.py`)
**입력 State 필드**:
- `query` 또는 `subtasks[current_idx]["query"]`
- `query_variations`: Multi-Query 리스트
- `search_filter`: 필터 조건

**출력 State 필드**:
- `documents`: 검색된 문서들 (누적)
- `subtasks`: documents 추가, status를 "retrieved"로
- `metadata`: 검색 통계 추가

#### Synthesis Node (`synthesis.py`)
**입력 State 필드**:
- `query` 또는 `subtasks[current_idx]["query"]`
- `documents`: 검색된 문서들
- `hallucination_feedback`: 재시도시 피드백
- `quality_feedback`: 재시도시 피드백

**출력 State 필드**:
- `intermediate_answer` 또는 `final_answer`
- `confidence_score`: 신뢰도
- `metadata`: synthesis 정보
- `retry_count`: 재시도 횟수

#### Hallucination Check Node (`hallucination.py`)
**입력 State 필드**:
- `final_answer`: 생성된 답변
- `documents`: 원본 문서들

**출력 State 필드**:
- `hallucination_check`: 검사 결과
- `metadata`: 환각 검사 정보

#### Answer Grader Node (`answer_grader.py`)
**입력 State 필드**:
- `query`: 원본 쿼리
- `final_answer`: 최종 답변

**출력 State 필드**:
- `answer_grade`: 평가 결과
- `metadata`: 평가 정보
- `workflow_status`: "completed" 또는 "failed"

## 🔀 조건부 라우팅 로직

### 1. `_should_continue_subtasks` (subtask_executor 이후)
- `continue`: 더 처리할 서브태스크가 있음 → retrieval로
- `complete`: 모든 서브태스크 완료 → synthesis로
- `failed`: 에러 발생 → END

### 2. `_should_web_search` (retrieval 이후)
- `search`: 문서 부족 (< 3개) → web_search로
- `continue`: 충분한 문서 → subtask_executor로

### 3. `_check_hallucination` (hallucination_check 이후)
- `valid`: 검사 통과 → answer_grader로
- `retry`: 재시도 필요 → synthesis로
- `failed`: 실패 → END

### 4. `_check_answer_quality` (answer_grader 이후)
- `accept`: 품질 통과 → END
- `retry`: 재시도 필요 → synthesis로
- `failed`: 실패 → END

## 🎯 수정 계획 (WORKFLOW_ENHANCEMENT_PLAN.md 기반)

### Phase 1: State 수정
1. **MessagesState 상속**: messages 필드 자동 추가
2. **3개 필드 추가**:
   - `query_type`: simple/rag_required/history_required
   - `enhanced_query`: 컨텍스트 개선된 쿼리
   - `current_node`: 디버깅용

### Phase 2: 새로운 노드 추가
1. **QueryRouterNode**: 새로운 엔트리포인트
   - 입력: query, messages
   - 출력: query_type, messages
   
2. **DirectResponseNode**: simple 쿼리 처리
   - 입력: query
   - 출력: final_answer, messages, workflow_status="completed"
   
3. **ContextEnhancementNode**: history_required 처리
   - 입력: query, messages
   - 출력: enhanced_query, messages

### Phase 3: Graph 재구성
1. **조건부 엔트리포인트**:
   - ENABLE_QUERY_ROUTING=true: query_router가 엔트리
   - ENABLE_QUERY_ROUTING=false: planning이 엔트리 (기존 동작)

2. **새로운 라우팅**:
   ```
   query_router → {
     simple: direct_response → END
     history_required: context_enhancement → planning
     rag_required: planning
   }
   ```

### Phase 4: 메시지 지원
- 각 노드에 `messages` 필드 반환 추가 (AIMessage 리스트)

## 📝 작업 기록

| 시간 | 작업 내용 | 상태 |
|------|----------|------|
| 2025-01-14 14:00 | graph.py 구조 분석 완료 | ✅ |
| 2025-01-14 14:05 | State 흐름 문서화 | ✅ |
| 2025-01-14 14:10 | Phase 1 시작 예정 | 🔄 |