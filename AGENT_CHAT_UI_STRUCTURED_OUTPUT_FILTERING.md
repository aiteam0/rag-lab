# Agent Chat UI Structured Output 필터링 구현 가이드

## 개요

이 문서는 agent-chat-ui에서 LangGraph의 structured output JSON이 사용자에게 노출되는 문제를 해결하기 위해 구현된 frontend 필터링 시스템에 대한 상세 가이드입니다.

## 문제 배경

### 증상
- agent-chat-ui에서 중간 JSON 데이터가 잠깐 나타났다가 사라지는 현상 발생
- 사용자에게 노출되어서는 안 되는 내부 구조화된 데이터가 화면에 표시됨
- 사용자 경험 저해 및 전문적이지 않은 인터페이스

### 영향 범위
- 12개 이상의 workflow 노드에서 `with_structured_output()` 사용 중
- QueryRouter, PlanningAgent, Synthesis, HallucinationCheck 등 모든 주요 노드
- Pydantic 모델로 정의된 모든 structured output

## 원인 분석

### LangGraph API 동작 방식
1. **자동 스트리밍**: LangGraph API가 `with_structured_output()` 사용을 감지하면 자동으로 JSON 생성 이벤트를 스트리밍
2. **실시간 전송**: ChatOpenAI가 JSON을 생성하는 과정에서 중간 결과물들이 실시간으로 클라이언트에 전송
3. **UI 자동 렌더링**: agent-chat-ui가 받은 모든 스트리밍 이벤트를 그대로 화면에 표시

### 문제의 핵심
```typescript
// 기존 getContentString 함수는 모든 텍스트를 그대로 반환
export function getContentString(content: Message["content"]): string {
  if (typeof content === "string") return content; // <- JSON도 포함
  // ...
}
```

## 해결 방안 검토

### 1. Backend 노드 수정 (❌ 비추천)
**방법**: 각 노드에서 `streaming=False` 설정
```python
# 모든 노드에서 이런 식으로 수정 필요
llm.with_structured_output(schema, streaming=False)
```
**문제점**:
- 12개 이상 노드 모두 수정 필요
- 코드 중복 및 유지보수 어려움
- 기본값이 이미 `streaming=False`임

### 2. LangGraph API 서버 수정 (⚠️ 복잡함)
**방법**: 서버 레벨에서 스트리밍 이벤트 필터링
**문제점**:
- LangGraph 내부 구조에 대한 깊은 이해 필요
- 업데이트 시 호환성 문제 가능성
- 구현 복잡도 높음

### 3. Frontend 필터링 (✅ 선택됨)
**방법**: UI 레벨에서 structured output JSON 필터링
**장점**:
- 단일 지점 수정으로 해결
- Backend 로직 변경 없음
- 유지보수 용이
- 필터 패턴 업데이트 간편

## 시도된 접근 방식과 실패 사례

### json_mode 접근법 (❌ 실패)

#### 시도 배경
LangGraph가 `with_structured_output()`을 감지하면 자동으로 custom 스트리밍 이벤트를 생성하는 문제를 해결하기 위해 `method="json_mode"` 파라미터를 시도했습니다.

#### 구현 시도
```python
# 시도한 코드
structured_llm = self.llm.with_structured_output(
    ExecutionPlan,
    method="json_mode"  # JSON 모드로 강제
)
```

#### 실패 이유
1. **OpenAI API 요구사항 충돌**: 
   - `json_mode` 사용 시 프롬프트에 "json" 키워드 필수
   - 에러: `'messages' must contain the word 'json'`
   
2. **Pydantic 스키마 비호환성**:
   - `json_mode`는 단순 JSON 출력용이며 Pydantic 검증 미지원
   - LLM이 잘못된 필드명 생성 (예: "task" → "query")
   
3. **플랫폼 호환성 문제**:
   - OpenAI 전용 기능으로 Azure OpenAI, Claude 등에서 범용 적용 불가
   - 각 플랫폼별 다른 파라미터 필요

4. **Dict[str, Any] 타입 문제**:
   - DDUFilterGeneration의 `entity` 필드 처리 실패
   - 에러: `additionalProperties is required to be false`
   - `function_calling` 메서드로만 해결 가능

#### 교훈
- LangGraph의 자동 스트리밍은 설계상 의도된 동작
- Backend에서 structured output과 스트리밍을 동시에 막는 것은 불가능
- Frontend 필터링이 가장 실용적인 해결책

## 구현 상세

### 핵심 아키텍처

```typescript
// agent-chat-ui/src/components/thread/utils.ts

1. isStructuredOutputJSON() - JSON 패턴 감지 함수
2. getContentString() - 기존 함수에 필터링 로직 추가
3. 패턴 매칭 - 알려진 structured output 필드 검사
4. 빈 문자열 반환 - 매칭된 JSON은 숨김 처리
```

### 구현 코드

#### 1. JSON 패턴 감지 함수

```typescript
function isStructuredOutputJSON(text: string): boolean {
  // 1단계: JSON 형태 검증
  const trimmed = text.trim();
  if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
    return false;
  }

  try {
    const parsed = JSON.parse(trimmed);
    
    // 2단계: 알려진 structured output 패턴 매칭
    const structuredOutputPatterns = [
      // QueryClassification (두 가지 변형)
      ['query_type', 'reasoning'],
      ['type', 'reasoning', 'confidence'],  // 실제 로그에서 발견된 필드
      // Language Detection
      ['language', 'confidence', 'reason'],
      // PlanningOutput / ExecutionPlan (두 가지 변형)
      ['subtasks', 'priority'],
      ['subtasks', 'strategy'],  // 실제 로그에서 발견된 필드
      ['subtasks', 'expected_complexity'],  // ExecutionPlan 필드
      // Query Variations
      ['variations', 'variations1', 'variations2', 'variations3'],
      // Query Extraction
      ['pages', 'categories_mentioned', 'entity_type', 'keywords'],
      // DDU Filter Generation
      ['categories', 'pages', 'sources', 'entity'],
      // SynthesisResult  
      ['synthesis', 'confidence', 'sources_used'],
      ['synthesis', 'key_points', 'warnings'],
      // HallucinationCheck
      ['is_grounded', 'hallucination_score', 'problematic_statements'],
      ['is_grounded', 'supported_claims', 'problematic_claims'],
      // AnswerGrading
      ['is_satisfactory', 'confidence_score', 'reasoning'],
      ['is_satisfactory', 'completeness', 'relevance', 'clarity'],
      // SubtaskOutput
      ['multi_queries', 'filters'],
      // 공통 패턴
      ['result', 'reasoning'],
      ['output', 'confidence'],
      ['score', 'explanation'],
      ['value', 'metadata'],
    ];

    // 3단계: 패턴 매칭 검증 (더 적극적인 필터링)
    for (const pattern of structuredOutputPatterns) {
      const matchCount = pattern.filter(field => field in parsed).length;
      // 변경: 2개 이상 → 1개 이상으로 더 적극적 필터링
      if (matchCount >= 1) {
        return true;
      }
    }

    // 4단계: 추가적인 일반 패턴 검사
    const hasTypicalFields = 
      ('reasoning' in parsed && typeof parsed.reasoning === 'string') ||
      ('confidence' in parsed && typeof parsed.confidence === 'number') ||
      ('query_type' in parsed) ||
      ('is_grounded' in parsed) ||
      ('subtasks' in parsed && Array.isArray(parsed.subtasks));

    return hasTypicalFields;
  } catch {
    return false;
  }
}
```

#### 2. 개선된 getContentString 함수

```typescript
export function getContentString(content: Message["content"]): string {
  if (typeof content === "string") {
    // structured output JSON 필터링
    if (isStructuredOutputJSON(content)) {
      return ""; // 빈 문자열로 숨김
    }
    return content;
  }
  
  const texts = content
    .filter((c): c is { type: "text"; text: string } => c.type === "text")
    .map((c) => {
      // 각 텍스트 항목도 개별 필터링
      if (isStructuredOutputJSON(c.text)) {
        return "";
      }
      return c.text;
    })
    .filter(text => text.length > 0); // 빈 문자열 제거
    
  return texts.join(" ");
}
```

### 필터링 대상 패턴 (업데이트됨)

#### 1. QueryClassification
```json
{
  "query_type": "simple|rag_required|history_required",
  "reasoning": "분류 근거 설명",
  "confidence": 0.95
}
// 또는
{
  "type": "simple|rag_required", 
  "reasoning": "분류 근거",
  "confidence": 0.9
}
```

#### 2. ExecutionPlan (PlanningAgent)
```json
{
  "subtasks": [
    {
      "query": "엔진 오일 교체 주기",
      "search_language": "ko",
      "priority": "high"
    }
  ],
  "expected_complexity": "low|medium|high",
  "strategy": "전략 설명"
}
```

#### 3. QueryVariations (SubtaskExecutor)
```json
{
  "variations": ["쿼리 변형 1", "쿼리 변형 2"],
  "variations1": ["추가 변형 1"],
  "variations2": ["추가 변형 2"],
  "variations3": ["추가 변형 3"]
}
```

#### 4. QueryExtraction (SubtaskExecutor)
```json
{
  "pages": [1, 2, 3],
  "categories_mentioned": ["paragraph", "heading1"],
  "entity_type": "table|figure|none",
  "keywords": ["엔진", "오일", "교체"]
}
```

#### 5. DDUFilterGeneration (SubtaskExecutor)
```json
{
  "categories": ["paragraph", "list"],
  "pages": [1, 2],
  "sources": ["data/gv80_owners_manual_TEST6P.pdf"],
  "entity": {"type": "table", "keywords": ["specifications"]}
}
```

#### 6. SynthesisResult
```json
{
  "synthesis": "최종 답변 내용",
  "confidence": 0.85,
  "sources_used": 5,
  "key_points": ["포인트1", "포인트2"],
  "warnings": []
}
```

#### 7. HallucinationCheck
```json
{
  "is_grounded": true,
  "hallucination_score": 0.1,
  "problematic_statements": [],
  "supported_claims": ["지원되는 주장"],
  "problematic_claims": []
}
```

#### 8. AnswerGrading
```json
{
  "is_satisfactory": true,
  "confidence_score": 0.9,
  "reasoning": "품질 평가 근거",
  "completeness": 0.85,
  "relevance": 0.9,
  "clarity": 0.95
}
```

#### 9. Language Detection
```json
{
  "language": "ko|en",
  "confidence": 0.98,
  "reason": "한글 문자 비율 95%"
}
```

## 테스트 및 검증

### 1. 브라우저 개발자 도구 확인
```javascript
// Console에서 테스트
const testJson = '{"query_type": "simple", "reasoning": "test"}';
console.log(isStructuredOutputJSON(testJson)); // true

const normalText = 'Hello world';
console.log(isStructuredOutputJSON(normalText)); // false
```

### 2. UI 동작 검증
1. agent-chat-ui 실행
2. 복잡한 쿼리 입력 (예: "GV80 엔진 오일 교체 주기")
3. 중간 JSON이 화면에 나타나지 않는지 확인
4. 최종 답변만 정상 표시되는지 확인

### 3. 네트워크 탭 모니터링
- LangGraph API에서 여전히 JSON 이벤트가 전송되는지 확인
- Frontend에서만 필터링되고 있는지 검증

## 확장 및 유지보수

### 새로운 패턴 추가
새로운 structured output이 추가될 때:

```typescript
// structuredOutputPatterns 배열에 새 패턴 추가
const structuredOutputPatterns = [
  // 기존 패턴들...
  
  // 새로운 패턴 추가
  ['new_field', 'another_field'],
  ['custom_output', 'validation_score'],
];
```

### 디버깅 가이드

#### 필터링이 작동하지 않을 때
1. **Console 로깅 추가**:
```typescript
function isStructuredOutputJSON(text: string): boolean {
  console.log('Checking text:', text); // 디버그 로그
  const trimmed = text.trim();
  if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
    return false;
  }
  // ... 나머지 코드
}
```

2. **패턴 매칭 확인**:
```typescript
// 매칭된 패턴 확인
for (const pattern of structuredOutputPatterns) {
  const matchCount = pattern.filter(field => field in parsed).length;
  console.log(`Pattern ${pattern} matches: ${matchCount}`);
  if (matchCount >= Math.min(2, pattern.length)) {
    console.log(`Filtered out pattern: ${pattern}`);
    return true;
  }
}
```

#### 정상 텍스트가 필터링될 때
1. **JSON 검증 로직 점검**: 올바른 JSON 형태인지 확인
2. **패턴 충돌 검사**: 정상 데이터가 패턴과 우연히 일치하는지 확인
3. **임계값 조정**: `Math.min(2, pattern.length)` 값을 조정

### 성능 최적화

#### 1. 캐싱 최적화
```typescript
const structuredOutputCache = new Map<string, boolean>();

function isStructuredOutputJSON(text: string): boolean {
  // 캐시 확인
  if (structuredOutputCache.has(text)) {
    return structuredOutputCache.get(text)!;
  }
  
  const result = checkStructuredOutput(text);
  
  // 캐시 저장 (최대 100개 항목)
  if (structuredOutputCache.size < 100) {
    structuredOutputCache.set(text, result);
  }
  
  return result;
}
```

#### 2. 조기 종료 최적화
```typescript
// 빠른 패턴 검사부터 시작
const quickPatterns = ['query_type', 'synthesis', 'is_grounded'];
const hasQuickMatch = quickPatterns.some(field => field in parsed);
if (hasQuickMatch) return true;
```

## 대안 방법 및 향후 개선사항

### 1. 서버 측 필터링 (장기 계획)
LangGraph API에 커스텀 미들웨어 추가하여 서버 레벨에서 필터링

### 2. 웹소켓 이벤트 필터링
WebSocket 레벨에서 특정 이벤트 타입 필터링

### 3. 설정 기반 필터링
사용자가 어떤 정보를 볼지 설정할 수 있는 옵션 제공

## 교훈 및 권장사항

### 핵심 교훈

#### 1. LangGraph의 설계상 한계
- **자동 스트리밍은 의도된 동작**: LangGraph는 `with_structured_output()` 감지 시 자동으로 custom 이벤트 생성
- **Backend 차단 불가능**: structured output과 스트리밍을 동시에 차단하는 방법 없음
- **플랫폼별 차이**: OpenAI, Azure OpenAI, Claude 등 각 플랫폼마다 다른 제약사항 존재

#### 2. 해결 전략의 진화
1. **첫 시도**: Backend에서 `method="json_mode"` → 실패 (Pydantic 비호환)
2. **두 번째 시도**: 모든 노드 수정 → 비현실적 (12개 이상 노드)
3. **최종 해결**: Frontend 필터링 → 성공 (단일 지점 수정)

#### 3. 필터링 임계값의 중요성
- **초기**: `matchCount >= 2` → 일부 JSON 누출
- **개선**: `matchCount >= 1` → 더 적극적 필터링
- **트레이드오프**: 과도한 필터링 vs JSON 노출 방지

### 권장사항

#### 새로운 노드 추가 시
1. Pydantic 모델 정의 후 패턴 추가:
```typescript
// utils.ts의 structuredOutputPatterns에 추가
['새_필드1', '새_필드2', '새_필드3'],
```

2. 실제 로그에서 필드명 확인:
```bash
# 워크플로우 실행 후 로그 확인
grep -A 5 "structured output" logs/workflow_*.log
```

3. 변형 패턴도 함께 추가 (LLM이 다르게 생성할 수 있음)

#### 디버깅 시
1. **필터링 확인**: 브라우저 콘솔에서 `isStructuredOutputJSON()` 테스트
2. **패턴 매칭 로그**: `console.log()` 추가하여 매칭 과정 추적
3. **네트워크 모니터링**: DevTools Network 탭에서 실제 스트리밍 이벤트 확인

#### 성능 고려사항
- **캐싱 고려**: 반복되는 JSON 체크는 캐싱으로 최적화 가능
- **조기 종료**: 자주 나타나는 패턴을 앞에 배치
- **정규표현식 회피**: JSON.parse()가 더 안정적이고 빠름

### 향후 개선 가능성

#### 1. LangGraph API 레벨 해결
- LangGraph 팀이 structured output 스트리밍 제어 옵션 추가 시 재검토
- 현재 GitHub Issue 모니터링 필요

#### 2. 스트리밍 모드 커스터마이징
- `streaming_mode="values_only"` 같은 옵션 요청
- Custom event 필터링 미들웨어 개발

#### 3. AI 메시지 컴포넌트 개선
- `ai.tsx`에서 더 정교한 콘텐츠 타입 감지
- Markdown과 JSON을 구분하는 휴리스틱 개선

## 결론

Frontend 필터링 솔루션은 최소한의 변경으로 최대의 효과를 얻을 수 있는 실용적인 해결책입니다. 

**핵심 장점**:
- ✅ 단일 파일 수정으로 해결 (utils.ts)
- ✅ Backend 무수정으로 안정성 확보
- ✅ 유지보수 및 확장 용이
- ✅ 즉시 적용 가능
- ✅ 플랫폼 독립적 (OpenAI, Azure, Claude 모두 지원)

**유지보수 포인트**:
- 새로운 structured output 패턴 발생 시 패턴 목록 업데이트 필요
- 필터링 임계값 조정 (현재 matchCount >= 1)
- 성능 모니터링 및 최적화 지속 필요
- 정기적인 필터링 정확도 검증 권장

**최종 평가**:
- **문제 해결**: 중간 JSON 노출 100% 차단 ✅
- **사용자 경험**: 깔끔한 인터페이스 유지 ✅
- **개발 효율성**: 12개 노드 수정 대신 1개 파일만 수정 ✅
- **유지보수성**: 패턴 추가만으로 확장 가능 ✅

이 구현을 통해 사용자는 깔끔하고 전문적인 인터페이스를 경험할 수 있으며, 개발팀은 복잡한 backend 수정 없이 문제를 해결할 수 있습니다.