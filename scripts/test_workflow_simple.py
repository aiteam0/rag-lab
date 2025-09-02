#!/usr/bin/env python3
"""
Simple workflow test to verify asyncio fixes
"""

import sys
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph


def test_simple_workflow():
    """간단한 워크플로우 테스트"""
    print("=" * 60)
    print("Simple Workflow Test - Asyncio Fix Verification")
    print("=" * 60)
    
    try:
        # 워크플로우 생성
        print("\n1. Creating workflow...")
        workflow = MVPWorkflowGraph()
        print("   ✅ Workflow created successfully")
        
        # 간단한 쿼리 실행
        query = "엔진 오일 교체 방법"
        print(f"\n2. Running query: '{query}'")
        
        # 동기 실행 (이제 asyncio.run() 에러가 발생하지 않아야 함)
        result = workflow.run(query)
        
        # 결과 확인
        if result.get("error"):
            print(f"   ❌ Error occurred: {result['error']}")
            return False
        
        if result.get("workflow_status") == "failed":
            print(f"   ❌ Workflow failed")
            if result.get("warnings"):
                print(f"   Warnings: {result['warnings']}")
            return False
            
        print("   ✅ Workflow executed without asyncio errors")
        
        # 결과 요약 출력
        print("\n3. Results summary:")
        print(f"   - Workflow status: {result.get('workflow_status', 'unknown')}")
        print(f"   - Subtasks created: {len(result.get('subtasks', []))}")
        
        # Documents MUST NOT be None - fail fast
        documents = result.get('documents')
        if documents is None:
            raise RuntimeError(
                f"CRITICAL ERROR: Documents is None in final state!\n"
                f"This should never happen - workflow must provide empty list at minimum.\n"
                f"Final state keys: {list(result.keys())}"
            )
        
        print(f"   - Documents retrieved: {len(documents)}")
        
        if result.get("final_answer"):
            #answer_preview = result["final_answer"][:100] + "..." if len(result["final_answer"]) > 100 else result["final_answer"]
            answer_preview = result["final_answer"]
            print(f"   - Answer generated: {answer_preview}")
        
        # 더 상세한 정보 출력
        print("\n4. Detailed Analysis:")
        if result.get("metadata", {}).get("synthesis"):
            synthesis_meta = result["metadata"]["synthesis"]
            print(f"   - Sources used: {synthesis_meta.get('sources', [])[:5]}...")  # 처음 5개만
            print(f"   - Key points: {synthesis_meta.get('key_points', [])[:3]}...")  # 처음 3개만
            print(f"   - Confidence: {synthesis_meta.get('confidence', 0)}")
        
        # References 섹션 확인
        if result.get("final_answer"):
            if "References:" in result["final_answer"]:
                print("   - ✅ References section found in answer")
            else:
                print("   - ⚠️ References section NOT found in answer")
        
        # 참조된 문서 정보 확인
        print("\n5. Document Analysis (first 5 cited):")
        cited_nums = synthesis_meta.get('sources', [])[:5] if result.get("metadata", {}).get("synthesis") else []
        for num_str in cited_nums:
            try:
                # Remove brackets if present (e.g., '[1]' -> '1')
                cleaned_num = num_str.strip('[]')
                idx = int(cleaned_num) - 1  # 1-based to 0-based
                if 0 <= idx < len(documents):
                    doc = documents[idx]
                    print(f"   [{cleaned_num}] {doc.metadata.get('source', 'Unknown')} p.{doc.metadata.get('page', '?')} - {doc.page_content[:50]}...")
            except Exception as e:
                print(f"   Error processing document {num_str}: {e}")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_simple_workflow()
    sys.exit(0 if success else 1)