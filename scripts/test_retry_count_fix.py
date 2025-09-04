#!/usr/bin/env python3
"""
Test to verify retry_count is properly reset between queries
"""

import sys
from pathlib import Path
import logging

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

from workflow.graph import MVPWorkflowGraph


def test_retry_count_reset():
    """Test that retry_count is properly reset between queries"""
    print("=" * 60)
    print("Retry Count Reset Test")
    print("=" * 60)
    
    try:
        # 워크플로우 생성
        print("\n1. Creating workflow...")
        workflow = MVPWorkflowGraph()
        print("   ✅ Workflow created successfully")
        
        # 첫 번째 쿼리 - 실패를 유도하기 위한 어려운 쿼리
        query1 = "GV80 엔진 오일 교체 주기와 사양을 상세하게 알려줘"
        print(f"\n2. Running first query: '{query1}'")
        result1 = workflow.run(query1)
        
        # retry_count 확인
        retry_count1 = result1.get("retry_count", 0)
        print(f"   - First query retry_count: {retry_count1}")
        
        # 에러나 경고 확인
        if result1.get("error"):
            print(f"   - Error: {result1['error']}")
        if result1.get("warnings"):
            print(f"   - Warnings: {result1['warnings']}")
            
        # 메시지에서 retry 관련 내용 찾기
        retry_messages_found = False
        messages = result1.get("messages", [])
        for msg in messages:
            if hasattr(msg, 'content') and "답변 재생성 중" in str(msg.content):
                print(f"   - Found retry message: {msg.content[:100]}...")
                retry_messages_found = True
                import re
                match = re.search(r'시도 (\d+)/(\d+)', msg.content)
                if match:
                    attempt = int(match.group(1))
                    print(f"     → Retry attempt: {attempt}")
        
        print(f"   - Retry messages found: {retry_messages_found}")
        
        # 두 번째 쿼리 - retry_count가 초기화되는지 확인
        query2 = "똑딱이 문서에 대해 알려줘"
        print(f"\n3. Running second query: '{query2}'")
        result2 = workflow.run(query2)
        
        # retry_count 확인
        retry_count2 = result2.get("retry_count", 0)
        print(f"   - Second query retry_count: {retry_count2}")
        
        # 메시지에서 retry 관련 내용 찾기
        incorrect_retry_found = False
        messages2 = result2.get("messages", [])
        for msg in messages2:
            if hasattr(msg, 'content') and "답변 재생성 중" in str(msg.content):
                import re
                match = re.search(r'시도 (\d+)/(\d+)', msg.content)
                if match:
                    attempt = int(match.group(1))
                    print(f"   - Found retry message: attempt {attempt}")
                    # 새 쿼리인데 시도가 2 이상이면 문제
                    if attempt > 1:
                        print(f"   ❌ ERROR: Second query started at attempt {attempt} instead of 1!")
                        incorrect_retry_found = True
                    else:
                        print(f"   ✅ OK: Retry properly started at attempt 1")
        
        if not incorrect_retry_found and retry_messages_found:
            print(f"   ✅ Retry count was properly reset for second query")
        
        # 세 번째 쿼리 - 추가 검증
        query3 = "디지털 정부 혁신 추진 계획에 대해 알려줘"
        print(f"\n4. Running third query: '{query3}'")
        result3 = workflow.run(query3)
        
        # retry_count 확인
        retry_count3 = result3.get("retry_count", 0)
        print(f"   - Third query retry_count: {retry_count3}")
        
        # 메시지에서 retry 관련 내용 찾기
        incorrect_retry_found3 = False
        messages3 = result3.get("messages", [])
        for msg in messages3:
            if hasattr(msg, 'content') and "답변 재생성 중" in str(msg.content):
                import re
                match = re.search(r'시도 (\d+)/(\d+)', msg.content)
                if match:
                    attempt = int(match.group(1))
                    print(f"   - Found retry message: attempt {attempt}")
                    if attempt > 1:
                        print(f"   ❌ ERROR: Third query started at attempt {attempt} instead of 1!")
                        incorrect_retry_found3 = True
                    else:
                        print(f"   ✅ OK: Retry properly started at attempt 1")
        
        if not incorrect_retry_found3:
            print(f"   ✅ Retry count was properly reset for third query")
        
        # 최종 결과
        print("\n" + "=" * 60)
        print("Test Summary:")
        print("=" * 60)
        print(f"Query 1 retry count: {retry_count1}")
        print(f"Query 2 retry count: {retry_count2}")
        print(f"Query 3 retry count: {retry_count3}")
        
        if not incorrect_retry_found and not incorrect_retry_found3:
            print("\n✅ TEST PASSED: Retry count is properly reset between queries!")
        else:
            print("\n❌ TEST FAILED: Retry count not properly reset between queries!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_retry_count_reset()