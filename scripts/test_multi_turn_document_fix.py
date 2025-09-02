#!/usr/bin/env python3
"""
Multi-turn 대화에서 문서 누적 문제 수정 확인 테스트
"""

import os
import sys
from pathlib import Path
import logging

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from workflow.graph import MVPWorkflowGraph
from workflow.state import MVPWorkflowState
from langchain_core.messages import HumanMessage, AIMessage

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_multi_turn_rag():
    """Multi-turn RAG 쿼리에서 문서 누적 문제가 해결되었는지 테스트"""
    
    print("\n" + "="*60)
    print("Multi-turn RAG 문서 누적 수정 테스트")
    print("="*60)
    
    # 워크플로우 그래프 생성
    workflow = MVPWorkflowGraph()
    
    # 테스트 시나리오
    test_queries = [
        ("안녕", "simple"),
        ("클라우드와 디지털 서비스 이용 활성화에 대해 알려줘", "rag"),
        ("내가 방금 뭐라고 물어봤어?", "history"),
        ("너가 다루고 있는 문서는 뭐가 있어?", "rag")
    ]
    
    # 각 쿼리별 결과 저장
    results = []
    first_rag_docs = 0
    second_rag_docs = 0
    
    for i, (query, expected_type) in enumerate(test_queries, 1):
        print(f"\n--- 쿼리 {i}: '{query}' (예상 타입: {expected_type}) ---")
        
        # 워크플로우 실행
        try:
            result = workflow.run(query)
            results.append(result)
            
            # 문서 수 확인
            documents = result.get("documents", [])
            print(f"✅ 쿼리 완료")
            print(f"   - 현재 state의 문서 수: {len(documents)}")
            
            # RAG 쿼리의 경우 synthesis 로그 확인
            if expected_type == "rag":
                metadata = result.get("metadata", {})
                synthesis_info = metadata.get("synthesis", {})
                docs_used = synthesis_info.get("documents_used", 0)
                print(f"   - Synthesis에 사용된 문서 수: {docs_used}")
                
                # 문서 누적 체크
                if i == 2:  # 첫 번째 RAG 쿼리
                    first_rag_docs = len(documents)
                    print(f"   📝 첫 번째 RAG 쿼리 문서 수 저장: {first_rag_docs}")
                elif i == 4:  # 두 번째 RAG 쿼리
                    second_rag_docs = len(documents)
                    print(f"   📝 두 번째 RAG 쿼리 문서 수: {second_rag_docs}")
                    
                    if second_rag_docs > first_rag_docs * 1.5:
                        print(f"   ❌ 문서 누적 발생! ({first_rag_docs} → {second_rag_docs})")
                    else:
                        print(f"   ✅ 문서 누적 없음! (각 RAG 쿼리마다 독립적)")
            
        except Exception as e:
            print(f"❌ 쿼리 실행 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            break
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60)

if __name__ == "__main__":
    test_multi_turn_rag()