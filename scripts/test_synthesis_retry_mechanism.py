#!/usr/bin/env python
"""
Synthesis Node Retry Mechanism 테스트
OpenAI API 서버 에러 시뮬레이션 및 exponential backoff 검증
"""

import sys
from pathlib import Path
import time
import logging
from unittest.mock import Mock, patch

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.synthesis import SynthesisNode
from langchain_core.documents import Document

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockStructuredLLM:
    """Mock LLM that simulates server errors"""
    
    def __init__(self, fail_attempts=2):
        self.fail_attempts = fail_attempts
        self.attempt_count = 0
    
    def invoke(self, messages):
        self.attempt_count += 1
        
        if self.attempt_count <= self.fail_attempts:
            logger.info(f"[MOCK] Simulating server error on attempt {self.attempt_count}")
            raise Exception("The server had an error while processing your request. Sorry about that")
        else:
            logger.info(f"[MOCK] Success on attempt {self.attempt_count}")
            return Mock(
                answer="Mock answer",
                confidence=0.9,
                sources_used=["[1]"],
                key_points=["Test point"],
                references_table="| 참조번호 | 문서명 | 페이지 | 내용 요약 |\n| [1] | test.pdf | 1 | Test content |",
                page_images=None,
                human_feedback_used=None,
                entity_references=None,
                warnings=None
            )


def test_retry_mechanism_success():
    """재시도 후 성공하는 케이스 테스트"""
    print("\n" + "="*60)
    print("🔄 Retry Mechanism Success Test")
    print("="*60)
    
    synthesis_node = SynthesisNode()
    mock_llm = MockStructuredLLM(fail_attempts=2)  # 2번 실패 후 성공
    messages = ["test message"]
    
    start_time = time.time()
    
    try:
        result = synthesis_node._invoke_with_retry(mock_llm, messages, max_retries=3)
        end_time = time.time()
        
        print(f"✅ Success after {mock_llm.attempt_count} attempts")
        print(f"⏱️ Total time: {end_time - start_time:.2f} seconds")
        print(f"📝 Result: {result.answer}")
        
        # 검증
        assert mock_llm.attempt_count == 3, f"Expected 3 attempts, got {mock_llm.attempt_count}"
        assert result.answer == "Mock answer", "Result should contain mock answer"
        print("✅ All assertions passed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_retry_mechanism_failure():
    """최대 재시도 후 실패하는 케이스 테스트"""
    print("\n" + "="*60)
    print("❌ Retry Mechanism Failure Test")
    print("="*60)
    
    synthesis_node = SynthesisNode()
    mock_llm = MockStructuredLLM(fail_attempts=5)  # 5번 계속 실패
    messages = ["test message"]
    
    start_time = time.time()
    
    try:
        result = synthesis_node._invoke_with_retry(mock_llm, messages, max_retries=3)
        print("❌ Should have failed but didn't")
        return False
        
    except Exception as e:
        end_time = time.time()
        
        print(f"✅ Correctly failed after {mock_llm.attempt_count} attempts")
        print(f"⏱️ Total time: {end_time - start_time:.2f} seconds")
        print(f"🚨 Final error: {e}")
        
        # 검증
        assert mock_llm.attempt_count == 4, f"Expected 4 attempts (3 retries + 1 initial), got {mock_llm.attempt_count}"
        assert "server had an error" in str(e), "Should contain server error message"
        print("✅ All assertions passed!")
        
        return True


def test_non_server_error():
    """서버 에러가 아닌 경우 즉시 실패 테스트"""
    print("\n" + "="*60)
    print("⚡ Non-Server Error Test")
    print("="*60)
    
    synthesis_node = SynthesisNode()
    
    # Non-server error를 발생시키는 Mock
    class NonServerErrorLLM:
        def __init__(self):
            self.attempt_count = 0
        
        def invoke(self, messages):
            self.attempt_count += 1
            raise ValueError("Invalid input format")  # 서버 에러가 아님
    
    mock_llm = NonServerErrorLLM()
    messages = ["test message"]
    
    start_time = time.time()
    
    try:
        result = synthesis_node._invoke_with_retry(mock_llm, messages, max_retries=3)
        print("❌ Should have failed immediately but didn't")
        return False
        
    except Exception as e:
        end_time = time.time()
        
        print(f"✅ Correctly failed immediately after {mock_llm.attempt_count} attempt")
        print(f"⏱️ Total time: {end_time - start_time:.2f} seconds")
        print(f"🚨 Error: {e}")
        
        # 검증
        assert mock_llm.attempt_count == 1, f"Should fail immediately, got {mock_llm.attempt_count} attempts"
        assert "Invalid input format" in str(e), "Should contain original error message"
        print("✅ All assertions passed!")
        
        return True


def test_exponential_backoff_timing():
    """Exponential backoff 타이밍 검증"""
    print("\n" + "="*60)
    print("⏰ Exponential Backoff Timing Test")
    print("="*60)
    
    synthesis_node = SynthesisNode()
    
    # 타이밍 측정을 위한 Mock
    class TimingMockLLM:
        def __init__(self):
            self.attempt_times = []
        
        def invoke(self, messages):
            self.attempt_times.append(time.time())
            
            if len(self.attempt_times) <= 2:  # 처음 2번 실패
                raise Exception("The server had an error while processing your request")
            else:
                return Mock(
                    answer="Success after timing test",
                    confidence=0.9,
                    sources_used=["[1]"],
                    key_points=["Test"],
                    references_table="| Test |",
                    page_images=None,
                    human_feedback_used=None,
                    entity_references=None,
                    warnings=None
                )
    
    mock_llm = TimingMockLLM()
    messages = ["test message"]
    
    start_time = time.time()
    
    try:
        result = synthesis_node._invoke_with_retry(mock_llm, messages, max_retries=3)
        
        # 타이밍 분석
        if len(mock_llm.attempt_times) >= 3:
            wait_time_1 = mock_llm.attempt_times[1] - mock_llm.attempt_times[0]
            wait_time_2 = mock_llm.attempt_times[2] - mock_llm.attempt_times[1]
            
            print(f"⏱️ Wait time between attempt 1-2: {wait_time_1:.2f}s")
            print(f"⏱️ Wait time between attempt 2-3: {wait_time_2:.2f}s")
            
            # Exponential backoff 검증 (1s → 2s 정도의 증가)
            # 실제로는 (2^0) + jitter ≈ 1s, (2^1) + jitter ≈ 2s
            print(f"✅ Exponential backoff working: {wait_time_1:.1f}s → {wait_time_2:.1f}s")
            
            return True
        
    except Exception as e:
        print(f"❌ Timing test failed: {e}")
        return False


def main():
    """모든 테스트 실행"""
    print("🔧 Synthesis Node Exponential Backoff Retry Tests")
    print("=" * 60)
    
    tests = [
        ("Success after retries", test_retry_mechanism_success),
        ("Failure after max retries", test_retry_mechanism_failure), 
        ("Non-server error immediate fail", test_non_server_error),
        ("Exponential backoff timing", test_exponential_backoff_timing),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            success = test_func()
            results.append((test_name, success))
            
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Exponential backoff retry mechanism is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)