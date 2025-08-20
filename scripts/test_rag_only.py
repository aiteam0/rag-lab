#!/usr/bin/env python3
"""
RAG Required Test만 단독으로 실행하는 테스트
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG 레벨로 상세 로그
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_rag_required():
    """RAG Required 쿼리 단독 테스트"""
    print("\n" + "="*60)
    print("RAG Required Test - Isolated Run")
    print("="*60 + "\n")
    
    # 워크플로우 초기화
    print("Initializing workflow...")
    workflow = MVPWorkflowGraph()
    
    if not workflow.enable_routing:
        print("❌ Query Routing is DISABLED!")
        return
    
    print("✅ Query Routing is ENABLED\n")
    
    # RAG Required 테스트 쿼리
    query = "GV80 엔진 오일 교체 주기와 권장 오일 사양을 알려주세요"
    print(f"Query: {query}\n")
    
    # 워크플로우 실행
    start_time = datetime.now()
    events = []
    error_occurred = False
    
    try:
        print("Starting workflow execution...")
        print("-" * 40)
        
        for event in workflow.stream(query, config={"recursion_limit": 30}):
            events.append(event)
            
            # 각 이벤트 출력
            for node_name, state in event.items():
                print(f"\n[Event {len(events)}] Node: {node_name}")
                
                # 주요 필드 출력
                if "query_type" in state:
                    print(f"  Query Type: {state['query_type']}")
                if "subtasks" in state and state["subtasks"]:
                    print(f"  Subtasks: {len(state['subtasks'])} created")
                if "documents" in state and state["documents"]:
                    print(f"  Documents: {len(state['documents'])} retrieved")
                if "error" in state and state["error"]:
                    print(f"  ❌ Error: {state['error']}")
                    error_occurred = True
                if "warnings" in state and state["warnings"]:
                    for warning in state["warnings"]:
                        print(f"  ⚠️ Warning: {warning}")
                if "final_answer" in state and state["final_answer"]:
                    print(f"  ✅ Final Answer: {str(state['final_answer'])[:100]}...")
        
        print("-" * 40)
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nExecution completed in {elapsed:.2f}s")
        
    except Exception as e:
        print(f"\n❌ Exception occurred: {str(e)}")
        error_occurred = True
    
    # 최종 상태 분석
    print("\n" + "="*60)
    print("Final State Analysis")
    print("="*60)
    
    final_state = {}
    for event in events:
        for node_name, state in event.items():
            final_state.update(state)
    
    print(f"\nTotal Events: {len(events)}")
    print(f"Error Occurred: {'Yes' if error_occurred else 'No'}")
    
    # 필수 필드 확인
    required_fields = ["query_type", "subtasks", "documents", "final_answer"]
    for field in required_fields:
        if field in final_state:
            value = final_state[field]
            if value:
                if field == "documents":
                    print(f"✅ {field}: {len(value)} items")
                elif field == "subtasks":
                    print(f"✅ {field}: {len(value)} items")
                elif field == "final_answer":
                    print(f"✅ {field}: Present ({len(str(value))} chars)")
                else:
                    print(f"✅ {field}: {value}")
            else:
                print(f"❌ {field}: Empty/None")
        else:
            print(f"❌ {field}: Missing")
    
    # 에러 상세 분석
    if "error" in final_state and final_state["error"]:
        print(f"\n❌ Error Details: {final_state['error']}")
    
    # 경고 상세 분석
    if "warnings" in final_state and final_state["warnings"]:
        print(f"\n⚠️ Warnings ({len(final_state['warnings'])}):")
        for i, warning in enumerate(final_state["warnings"], 1):
            print(f"  {i}. {warning}")
    
    # 워크플로우 경로 분석
    path = []
    for event in events:
        for node_name in event.keys():
            if node_name not in path:
                path.append(node_name)
    
    print(f"\nWorkflow Path: {' → '.join(path)}")
    
    return not error_occurred and "final_answer" in final_state


if __name__ == "__main__":
    success = asyncio.run(test_rag_required())
    print("\n" + "="*60)
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("="*60)