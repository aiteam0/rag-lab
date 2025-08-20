# 🚀 LangGraph Chat UI 실시간 스트리밍 통합 가이드

> **목적**: 이 문서는 LangGraph 에이전트 개발자가 Chat UI와 통합하여 노드의 중간 실행 결과를 실시간으로 표시하는 방법을 상세히 설명합니다.

## 📋 목차

1. [개요](#개요)
2. [스트리밍 아키텍처](#스트리밍-아키텍처)
3. [핵심 메커니즘](#핵심-메커니즘)
4. [필수 요구사항](#필수-요구사항)
5. [단계별 구현 가이드](#단계별-구현-가이드)
6. [실제 구현 예제](#실제-구현-예제)
7. [베스트 프랙티스](#베스트-프랙티스)
8. [트러블슈팅](#트러블슈팅)
9. [참고 자료](#참고-자료)

---

## 개요

LangGraph Chat UI는 LangGraph 서버와 통합되어 **에이전트의 실행 과정을 실시간으로 시각화**할 수 있는 Next.js 기반 웹 애플리케이션입니다. 이 가이드는 여러분의 LangGraph 에이전트가 Chat UI에서 중간 실행 결과를 표시하도록 구현하는 방법을 설명합니다.

### 주요 특징
- ✅ **실시간 스트리밍**: 각 노드 실행 결과가 즉시 UI에 표시
- ✅ **투명한 프로세스**: 사용자가 AI의 사고 과정을 단계별로 확인 가능
- ✅ **간단한 통합**: 최소한의 코드 변경으로 기존 에이전트 확장
- ✅ **풍부한 피드백**: 이모지와 진행률 표시로 직관적인 상태 전달

---

## 스트리밍 아키텍처

### 전체 시스템 구조

```
┌──────────────────┐     WebSocket/SSE      ┌──────────────────┐
│                  │ ◄─────────────────────► │                  │
│   Chat UI        │                         │  LangGraph       │
│   (Next.js)      │     API Passthrough     │  Server          │
│   Port: 3000     │ ◄─────────────────────► │  Port: 2024      │
│                  │                         │                  │
└──────────────────┘                         └──────────────────┘
        ▲                                            ▲
        │                                            │
        │ Display                              State Changes
        │ Messages                             (Auto-streaming)
        │                                            │
        ▼                                            ▼
   [사용자 인터페이스]                        [Agent Graph Nodes]
```

### 데이터 플로우

1. **노드 실행** → State 변경 발생
2. **LangGraph 서버** → State diff 감지 및 이벤트 생성
3. **WebSocket/SSE** → 실시간 이벤트 스트림 전송
4. **Chat UI** → 스트림 수신 및 메시지 렌더링
5. **사용자** → 실시간으로 진행 상황 확인

---

## 핵심 메커니즘

### 1. Backend: 메시지 생성 및 State 업데이트

```python
def my_node(state: AgentState):
    """노드에서 중간 결과를 생성하는 예시"""
    
    # 진행 상황 메시지 생성
    progress_msg = AIMessage(content="🔄 작업을 처리하고 있습니다...")
    
    # 실제 작업 수행
    result = perform_task()
    
    # 완료 메시지 생성
    complete_msg = AIMessage(content=f"✅ 작업 완료: {result}")
    
    # State에 메시지 추가 (자동으로 스트리밍됨)
    return {
        "messages": [progress_msg, complete_msg]
    }
```

### 2. LangGraph Server: 자동 스트리밍

LangGraph 서버는 각 노드 실행 후 State 변경을 자동으로 감지하고 스트리밍합니다:

```python
# graph.py
app = workflow.compile()  # 컴파일 시 자동 스트리밍 활성화

# langgraph.json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./graph.py:app"  # 또는 graph 변수명
  }
}
```

### 3. Frontend: 실시간 수신 및 렌더링

Chat UI는 `@langchain/langgraph-sdk`의 `useStream` 훅을 사용하여 스트림을 처리합니다:

```typescript
// 자동으로 처리되는 부분 (Chat UI 내부)
const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "agent",
    onCustomEvent: (event) => {
        // 메시지 자동 업데이트
    }
});
```

---

## 필수 요구사항

### ✅ 체크리스트

1. **State 클래스**
   - [ ] `MessagesState`를 상속하거나
   - [ ] `messages` 필드를 포함한 State 정의

2. **메시지 반환**
   - [ ] 각 노드에서 `AIMessage` 객체 반환
   - [ ] `return {"messages": [AIMessage(...)]}`

3. **서버 설정**
   - [ ] `langgraph.json` 파일 생성
   - [ ] Graph 객체 export

4. **환경 설정**
   - [ ] Chat UI 환경변수 설정
   - [ ] API URL과 Assistant ID 지정

---

## 단계별 구현 가이드

### Step 1: State 클래스 정의

```python
from langgraph.graph import MessagesState
from typing import Any, Dict

class MyAgentState(MessagesState):
    """
    MessagesState를 반드시 상속해야 합니다.
    messages 필드는 자동으로 포함됩니다.
    """
    # 추가 필드 (선택사항)
    current_step: int = 0
    total_steps: int = 0
    context: Dict[str, Any] = {}
```

### Step 2: 중간 결과를 표시하는 노드 작성

```python
from langchain_core.messages import AIMessage

def processing_node(state: MyAgentState) -> Dict[str, Any]:
    """중간 진행 상황을 표시하는 노드"""
    
    messages = []
    
    # 1. 시작 알림
    messages.append(
        AIMessage(content="🔄 작업을 시작합니다...")
    )
    
    # 2. 진행 상황 (여러 메시지 가능)
    for i in range(3):
        messages.append(
            AIMessage(content=f"📊 단계 {i+1}/3 처리 중...")
        )
        # 실제 작업 수행
        time.sleep(1)
    
    # 3. 완료 알림
    messages.append(
        AIMessage(content="✅ 모든 작업이 완료되었습니다!")
    )
    
    # 4. 최종 결과
    final_result = "처리된 데이터 요약..."
    messages.append(
        AIMessage(content=f"📝 결과: {final_result}")
    )
    
    return {
        "messages": messages,
        "current_step": 3,
        "total_steps": 3
    }
```

### Step 3: Graph 구성

```python
from langgraph.graph import StateGraph, START, END

def create_agent():
    """에이전트 그래프 생성"""
    
    # 1. StateGraph 초기화
    workflow = StateGraph(MyAgentState)
    
    # 2. 노드 추가
    workflow.add_node("process", processing_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("summarize", summarize_node)
    
    # 3. 엣지 연결
    workflow.add_edge(START, "process")
    workflow.add_edge("process", "analyze")
    workflow.add_edge("analyze", "summarize")
    workflow.add_edge("summarize", END)
    
    # 4. 컴파일
    return workflow.compile()

# LangGraph 서버용 export (중요!)
graph = create_agent()  # 또는 app = create_agent()
```

### Step 4: langgraph.json 설정

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./my_agent.py:graph"
  },
  "env": ".env"
}
```

### Step 5: 환경 설정

**.env 파일 (Backend)**:
```bash
# LLM 설정
OPENAI_API_KEY=sk-...
# 또는
ANTHROPIC_API_KEY=sk-ant-...
```

**.env 파일 (Chat UI)**:
```bash
# Chat UI 설정
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=agent
```

### Step 6: 실행

```bash
# Terminal 1: LangGraph 서버 실행
cd your-agent-directory
langgraph dev --port 2024

# Terminal 2: Chat UI 실행
cd agent-chat-ui
pnpm dev
```

---

## 실제 구현 예제

### 예제 1: 데이터 처리 파이프라인

```python
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.messages import AIMessage
import time
from typing import List, Dict, Any

class DataPipelineState(MessagesState):
    """데이터 파이프라인 State"""
    data_source: str = ""
    record_count: int = 0
    processed_count: int = 0
    errors: List[str] = []

def extract_data_node(state: DataPipelineState) -> Dict[str, Any]:
    """데이터 추출 노드"""
    messages = []
    
    # 추출 시작
    messages.append(
        AIMessage(content="🔄 데이터 소스에 연결하고 있습니다...")
    )
    
    # 연결 시뮬레이션
    time.sleep(1)
    messages.append(
        AIMessage(content="✅ 데이터베이스 연결 성공")
    )
    
    # 데이터 추출
    messages.append(
        AIMessage(content="📊 데이터를 추출하고 있습니다...")
    )
    
    record_count = 1000  # 실제로는 DB 쿼리 결과
    
    messages.append(
        AIMessage(content=f"✅ {record_count}개의 레코드를 추출했습니다")
    )
    
    return {
        "messages": messages,
        "data_source": "production_db",
        "record_count": record_count
    }

def transform_data_node(state: DataPipelineState) -> Dict[str, Any]:
    """데이터 변환 노드"""
    messages = []
    total = state["record_count"]
    batch_size = 100
    processed = 0
    
    messages.append(
        AIMessage(content=f"🔄 {total}개 레코드 변환을 시작합니다...")
    )
    
    # 배치 처리 시뮬레이션
    for batch_num in range(0, total, batch_size):
        processed = min(batch_num + batch_size, total)
        progress = (processed / total) * 100
        
        # 진행률 표시
        messages.append(
            AIMessage(
                content=f"📊 변환 중... {progress:.1f}% ({processed}/{total})"
            )
        )
        
        # 실제 변환 작업 시뮬레이션
        time.sleep(0.5)
    
    messages.append(
        AIMessage(content="✅ 데이터 변환 완료!")
    )
    
    return {
        "messages": messages,
        "processed_count": processed
    }

def load_data_node(state: DataPipelineState) -> Dict[str, Any]:
    """데이터 로드 노드"""
    messages = []
    processed = state["processed_count"]
    
    messages.append(
        AIMessage(content="🔄 타겟 시스템에 데이터를 로드하고 있습니다...")
    )
    
    # 로드 시뮬레이션
    time.sleep(2)
    
    messages.append(
        AIMessage(content=f"✅ {processed}개 레코드 로드 완료")
    )
    
    # 최종 요약
    summary = f"""
📈 **ETL 파이프라인 실행 완료**

- 데이터 소스: {state['data_source']}
- 추출된 레코드: {state['record_count']}개
- 처리된 레코드: {processed}개
- 에러: {len(state.get('errors', []))}개
- 상태: ✅ 성공
    """
    
    messages.append(AIMessage(content=summary))
    
    return {"messages": messages}

# Graph 생성
def create_etl_pipeline():
    workflow = StateGraph(DataPipelineState)
    
    # 노드 추가
    workflow.add_node("extract", extract_data_node)
    workflow.add_node("transform", transform_data_node)
    workflow.add_node("load", load_data_node)
    
    # 엣지 연결
    workflow.add_edge(START, "extract")
    workflow.add_edge("extract", "transform")
    workflow.add_edge("transform", "load")
    workflow.add_edge("load", END)
    
    return workflow.compile()

graph = create_etl_pipeline()
```

### 예제 2: 도구 사용 에이전트

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

@tool
def search_database(query: str) -> str:
    """데이터베이스 검색 도구"""
    # 실제 DB 검색 로직
    return f"Found 10 results for: {query}"

@tool
def calculate_statistics(data: str) -> str:
    """통계 계산 도구"""
    # 실제 통계 계산 로직
    return "Average: 75.5, Median: 72.0, StdDev: 12.3"

class AnalysisAgentState(MessagesState):
    """분석 에이전트 State"""
    analysis_type: str = ""
    results: Dict[str, Any] = {}

def prepare_analysis_node(state: AnalysisAgentState) -> Dict[str, Any]:
    """분석 준비 노드"""
    messages = []
    
    # 분석 시작 알림
    messages.append(
        AIMessage(content="🔍 데이터 분석을 준비하고 있습니다...")
    )
    
    # 필요한 도구 확인
    messages.append(
        AIMessage(content="🔧 필요한 도구를 확인했습니다: search_database, calculate_statistics")
    )
    
    return {
        "messages": messages,
        "analysis_type": "statistical_analysis"
    }

def execute_tools_node(state: AnalysisAgentState) -> Dict[str, Any]:
    """도구 실행 노드"""
    llm = ChatOpenAI(model="gpt-4o-mini")
    tools = [search_database, calculate_statistics]
    model_with_tools = llm.bind_tools(tools)
    
    messages = []
    
    # 도구 사용 알림
    messages.append(
        AIMessage(content="🔄 데이터베이스를 검색하고 있습니다...")
    )
    
    # 도구 호출 (실제 구현)
    response = model_with_tools.invoke([
        HumanMessage(content="최근 판매 데이터를 검색하고 통계를 계산해주세요")
    ])
    
    if response.tool_calls:
        messages.append(
            AIMessage(content=f"🔧 {len(response.tool_calls)}개의 도구를 실행합니다...")
        )
        messages.append(response)  # 도구 호출 메시지
    
    return {"messages": messages}

def summarize_analysis_node(state: AnalysisAgentState) -> Dict[str, Any]:
    """분석 요약 노드"""
    messages = []
    
    messages.append(
        AIMessage(content="📝 분석 결과를 요약하고 있습니다...")
    )
    
    # 요약 생성
    summary = """
📊 **데이터 분석 완료**

**검색 결과**:
- 총 10개의 관련 레코드 발견
- 기간: 2024년 1월 - 현재

**통계 분석**:
- 평균값: 75.5
- 중앙값: 72.0
- 표준편차: 12.3

**인사이트**:
- 데이터는 정규분포를 따름
- 이상치 없음
- 추세: 상승 경향
    """
    
    messages.append(AIMessage(content=summary))
    
    return {"messages": messages}

# Graph with tools
def create_analysis_agent():
    workflow = StateGraph(AnalysisAgentState)
    
    # 도구 노드 생성
    tool_node = ToolNode([search_database, calculate_statistics])
    
    # 노드 추가
    workflow.add_node("prepare", prepare_analysis_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("summarize", summarize_analysis_node)
    
    # 엣지 연결
    workflow.add_edge(START, "prepare")
    workflow.add_edge("prepare", "execute_tools")
    
    # 조건부 엣지 (도구 호출 여부)
    def should_use_tools(state):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "summarize"
    
    workflow.add_conditional_edges(
        "execute_tools",
        should_use_tools,
        {
            "tools": "tools",
            "summarize": "summarize"
        }
    )
    
    workflow.add_edge("tools", "summarize")
    workflow.add_edge("summarize", END)
    
    return workflow.compile()

graph = create_analysis_agent()
```

### 예제 3: Sequential Thinking 패턴

```python
class ComplexProblemState(MessagesState):
    """복잡한 문제 해결 State"""
    problem: str = ""
    steps: List[Dict[str, str]] = []
    current_step: int = 0
    step_results: List[str] = []

def analyze_complexity_node(state: ComplexProblemState) -> Dict[str, Any]:
    """복잡도 분석 노드"""
    problem = state["messages"][-1].content if state["messages"] else ""
    
    messages = [
        AIMessage(content="🔄 문제 복잡도를 분석하고 있습니다..."),
        AIMessage(content="📊 복잡도: 높음 - 단계별 접근이 필요합니다"),
    ]
    
    return {
        "messages": messages,
        "problem": problem
    }

def decompose_problem_node(state: ComplexProblemState) -> Dict[str, Any]:
    """문제 분해 노드"""
    messages = [
        AIMessage(content="🔄 문제를 단계별로 분해하고 있습니다...")
    ]
    
    # 문제를 단계로 분해
    steps = [
        {"step": 1, "task": "데이터 수집", "description": "필요한 정보 수집"},
        {"step": 2, "task": "분석", "description": "수집된 데이터 분석"},
        {"step": 3, "task": "해결책 도출", "description": "분석 기반 해결책 제시"}
    ]
    
    steps_text = "\n".join([
        f"  {s['step']}. {s['task']}: {s['description']}"
        for s in steps
    ])
    
    messages.append(
        AIMessage(content=f"📝 {len(steps)}개 단계로 분해 완료:\n{steps_text}")
    )
    
    return {
        "messages": messages,
        "steps": steps
    }

def execute_step_node(state: ComplexProblemState) -> Dict[str, Any]:
    """단계 실행 노드"""
    current = state.get("current_step", 0)
    steps = state.get("steps", [])
    
    if current >= len(steps):
        return {"messages": []}
    
    step = steps[current]
    messages = []
    
    # 현재 단계 실행
    messages.append(
        AIMessage(
            content=f"🔄 단계 {step['step']}/{len(steps)} 실행 중: {step['task']}"
        )
    )
    
    # 실제 작업 시뮬레이션
    time.sleep(1)
    result = f"단계 {step['step']} 완료: {step['task']} 성공"
    
    messages.append(
        AIMessage(content=f"✅ {result}")
    )
    
    return {
        "messages": messages,
        "current_step": current + 1,
        "step_results": state.get("step_results", []) + [result]
    }

def synthesize_solution_node(state: ComplexProblemState) -> Dict[str, Any]:
    """해결책 종합 노드"""
    messages = [
        AIMessage(content="🔄 최종 답변을 종합하고 있습니다...")
    ]
    
    # 결과 종합
    num_steps = len(state.get("step_results", []))
    solution = f"""
✅ **문제 해결 완료**

**원본 문제**: {state.get("problem", "Unknown")}

**수행된 단계**: {num_steps}개
{chr(10).join([f"- {r}" for r in state.get("step_results", [])])}

**최종 해결책**:
분석 결과를 바탕으로 다음과 같은 해결책을 제시합니다...

---
*{num_steps}단계의 순차적 사고로 분석됨*
    """
    
    messages.append(AIMessage(content=solution))
    
    return {"messages": messages}

# Sequential Thinking Graph
def create_sequential_agent():
    workflow = StateGraph(ComplexProblemState)
    
    # 노드 추가
    workflow.add_node("analyze", analyze_complexity_node)
    workflow.add_node("decompose", decompose_problem_node)
    workflow.add_node("execute", execute_step_node)
    workflow.add_node("synthesize", synthesize_solution_node)
    
    # 엣지 연결
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "decompose")
    workflow.add_edge("decompose", "execute")
    
    # 조건부 엣지 (더 실행할 단계가 있는지)
    def should_continue_execution(state):
        current = state.get("current_step", 0)
        total = len(state.get("steps", []))
        if current < total:
            return "execute"  # 계속 실행
        return "synthesize"  # 종합으로
    
    workflow.add_conditional_edges(
        "execute",
        should_continue_execution,
        {
            "execute": "execute",
            "synthesize": "synthesize"
        }
    )
    
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()

graph = create_sequential_agent()
```

---

## 베스트 프랙티스

### 1. 메시지 작성 가이드

#### ✅ 좋은 예시

```python
# 명확한 진행 상황 표시
AIMessage(content="🔄 단계 1/5: 데이터 유효성 검증 중...")
AIMessage(content="📊 진행률: 60% (600/1000 레코드 처리)")
AIMessage(content="✅ 검증 완료: 모든 데이터가 유효합니다")

# 구조화된 결과 표시
AIMessage(content="""
📈 **처리 결과**
- 총 처리: 1000개
- 성공: 950개
- 실패: 50개
- 처리 시간: 2.5초
""")
```

#### ❌ 피해야 할 예시

```python
# 불명확한 메시지
AIMessage(content="처리중...")
AIMessage(content="...")
AIMessage(content="완료")

# 너무 기술적인 메시지
AIMessage(content="[DEBUG] Processing node_id=xyz123 with params={...}")
```

### 2. 이모지 사용 규칙

| 이모지 | 용도 | 사용 예시 |
|--------|------|-----------|
| 🔄 | 진행 중 | "🔄 데이터를 처리하고 있습니다..." |
| 📊 | 분석/통계 | "📊 분석 결과: ..." |
| 📝 | 문서/결과 | "📝 최종 보고서 생성 중..." |
| 🔍 | 검색/조사 | "🔍 관련 정보를 검색하고 있습니다..." |
| ⚙️ | 설정/처리 | "⚙️ 시스템 설정 중..." |
| ✅ | 완료 | "✅ 작업이 성공적으로 완료되었습니다" |
| ❌ | 실패 | "❌ 오류가 발생했습니다" |
| ⚠️ | 경고 | "⚠️ 주의가 필요한 사항이 있습니다" |
| 💡 | 제안/인사이트 | "💡 다음과 같은 개선안을 제안합니다" |
| 🚀 | 시작 | "🚀 작업을 시작합니다" |

### 3. 성능 최적화

#### 배치 메시지 vs 개별 메시지

```python
# ✅ 배치 메시지 (권장) - 네트워크 오버헤드 감소
def batch_node(state):
    messages = []
    for i in range(10):
        messages.append(AIMessage(content=f"처리 {i+1}/10"))
    return {"messages": messages}  # 한 번에 전송

# ⚠️ 개별 메시지 (필요한 경우만) - 실시간성이 중요할 때
def realtime_node(state):
    for i in range(10):
        # 각각 별도 노드로 분리하거나
        # 중간에 다른 노드를 거쳐야 할 때
        yield {"messages": [AIMessage(content=f"처리 {i+1}/10")]}
```

### 4. 에러 처리

```python
def safe_node(state: AgentState) -> Dict[str, Any]:
    """안전한 노드 구현"""
    messages = []
    
    try:
        messages.append(
            AIMessage(content="🔄 작업을 시작합니다...")
        )
        
        # 위험한 작업
        result = risky_operation()
        
        messages.append(
            AIMessage(content=f"✅ 성공: {result}")
        )
        
    except SpecificError as e:
        messages.append(
            AIMessage(content=f"⚠️ 예상된 오류: {str(e)}")
        )
        messages.append(
            AIMessage(content="🔄 대체 방법으로 재시도합니다...")
        )
        # 대체 로직
        
    except Exception as e:
        messages.append(
            AIMessage(content=f"❌ 예상치 못한 오류: {str(e)}")
        )
        messages.append(
            AIMessage(content="📝 오류를 기록하고 계속 진행합니다...")
        )
    
    return {"messages": messages}
```

### 5. 사용자 경험 개선

```python
def user_friendly_node(state: AgentState) -> Dict[str, Any]:
    """사용자 친화적인 메시지"""
    messages = []
    
    # 1. 컨텍스트 제공
    messages.append(
        AIMessage(content="🔍 요청하신 판매 데이터를 분석하겠습니다")
    )
    
    # 2. 예상 시간 안내
    messages.append(
        AIMessage(content="⏱️ 예상 소요 시간: 약 30초")
    )
    
    # 3. 단계별 진행 상황
    total_steps = 5
    for i in range(total_steps):
        messages.append(
            AIMessage(
                content=f"📊 {i+1}/{total_steps} - {['데이터 로드', '정제', '분석', '시각화', '요약'][i]}"
            )
        )
        time.sleep(0.5)
    
    # 4. 결과 요약 (핵심만)
    messages.append(
        AIMessage(content="""
✅ **분석 완료**

**핵심 발견사항**:
• 매출이 전월 대비 15% 증가
• 신규 고객이 주요 성장 동력
• 주말 판매가 특히 활발

자세한 내용을 보시려면 '상세 보고서'를 요청해주세요.
        """)
    )
    
    return {"messages": messages}
```

---

## 트러블슈팅

### 문제 1: 메시지가 UI에 표시되지 않음

**원인**:
- State가 MessagesState를 상속하지 않음
- messages 필드가 없거나 잘못된 타입

**해결책**:
```python
# ✅ 올바른 구현
class MyState(MessagesState):
    pass

# ❌ 잘못된 구현
class MyState(TypedDict):
    messages: list  # MessagesState를 상속해야 함
```

### 문제 2: 스트리밍이 작동하지 않음

**원인**:
- LangGraph 서버가 아닌 일반 Python으로 실행
- langgraph.json 설정 오류

**해결책**:
```bash
# ✅ 올바른 실행
langgraph dev --port 2024

# ❌ 잘못된 실행
python my_agent.py
```

### 문제 3: 한글이 깨져서 표시됨

**원인**:
- 인코딩 문제

**해결책**:
```python
# UTF-8 인코딩 명시
AIMessage(content="한글 메시지".encode('utf-8').decode('utf-8'))

# 또는 파일 상단에
# -*- coding: utf-8 -*-
```

### 문제 4: 메시지 순서가 뒤바뀜

**원인**:
- 비동기 처리로 인한 순서 보장 실패

**해결책**:
```python
# 한 번에 순서대로 반환
return {
    "messages": [msg1, msg2, msg3]  # 순서 보장
}
```

### 문제 5: 성능 문제 (느린 응답)

**원인**:
- 너무 많은 메시지 생성
- 각 메시지마다 네트워크 왕복

**해결책**:
```python
# 메시지 배치 처리
messages = []
for item in large_list:
    if len(messages) % 10 == 0:  # 10개마다 한 번씩만
        messages.append(
            AIMessage(content=f"처리 중: {len(messages)}/{len(large_list)}")
        )
```

---

## 참고 자료

### 공식 문서
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Streaming Guide](https://langchain-ai.github.io/langgraph/how-tos/streaming/)
- [Chat UI Repository](https://github.com/langchain-ai/agent-chat-ui)

### 관련 파일 (이 프로젝트)
- `/multimodal-agent/src/agent/graph.py` - Graph 구성 예제
- `/multimodal-agent/src/agent/nodes/sequential.py` - Sequential Thinking 구현
- `/agent-chat-ui/src/providers/Stream.tsx` - 프론트엔드 스트림 처리

### 핵심 패키지
```bash
# Backend
pip install langgraph langchain-core langchain-openai

# Frontend
pnpm add @langchain/langgraph-sdk
```

### 환경 변수 템플릿

**.env.example (Backend)**:
```bash
# LLM Provider (choose one)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# AZURE_OPENAI_ENDPOINT=https://...
# AZURE_OPENAI_API_KEY=...

# Optional Tools
TAVILY_API_KEY=tvly-...  # Web search
OPENWEATHER_API_KEY=...  # Weather
```

**.env.example (Chat UI)**:
```bash
# Development
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=agent

# Production
# NEXT_PUBLIC_API_URL=https://your-domain.com/api
# LANGGRAPH_API_URL=https://your-langgraph-server.com
# LANGSMITH_API_KEY=lsv2_...
```

---

## 마무리

이 가이드를 따라 구현하면, 여러분의 LangGraph 에이전트도 Chat UI에서 실시간으로 중간 실행 결과를 표시할 수 있습니다. 핵심은:

1. **MessagesState 상속** ✅
2. **AIMessage 반환** ✅
3. **LangGraph 서버 실행** ✅
4. **올바른 설정** ✅

질문이나 이슈가 있다면:
- GitHub Issues: [agent-chat-ui/issues](https://github.com/langchain-ai/agent-chat-ui/issues)
- LangGraph Discord: [Join Discord](https://discord.gg/langchain)

Happy Streaming! 🚀

---

*Last Updated: 2025-01-11*
*Version: 1.0.0*
*Author: LangGraph Community*