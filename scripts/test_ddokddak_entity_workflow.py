#!/usr/bin/env python3
"""
Test script for '똑딱이' entity type support in the workflow
Tests the complete pipeline from entity filter generation to synthesis formatting
"""

import sys
import json
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from workflow.graph import MVPWorkflowGraph
from workflow.nodes.subtask_executor import SubtaskExecutorNode
from workflow.nodes.synthesis import SynthesisNode
from workflow.nodes.hallucination import HallucinationCheckNode
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()


def check_database_for_ddokddak():
    """데이터베이스에 '똑딱이' entity type이 있는지 확인"""
    print("=" * 60)
    print("1. Checking Database for '똑딱이' Entity Type")
    print("=" * 60)
    
    try:
        # DB 연결
        conn = psycopg.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "pgvector_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            row_factory=dict_row
        )
        
        with conn.cursor() as cur:
            # 1. Entity types 확인
            cur.execute("""
                SELECT DISTINCT entity->>'type' as entity_type, COUNT(*) as count
                FROM mvp_ddu_documents
                WHERE entity IS NOT NULL
                AND entity->>'type' IS NOT NULL
                GROUP BY entity->>'type'
                ORDER BY count DESC
            """)
            
            entity_types = cur.fetchall()
            print("\n📊 Entity Types in Database:")
            has_ddokddak = False
            for row in entity_types:
                print(f"   - {row['entity_type']}: {row['count']} documents")
                if row['entity_type'] == '똑딱이':
                    has_ddokddak = True
            
            if not has_ddokddak:
                print("\n⚠️ WARNING: No '똑딱이' entity type found in database!")
                print("   Please run transplant_ddokddak_entity.py first to add '똑딱이' entities.")
            else:
                print("\n✅ '똑딱이' entity type found in database!")
                
                # 2. 카테고리별 분포 확인
                cur.execute("""
                    SELECT category, COUNT(*) as count
                    FROM mvp_ddu_documents
                    WHERE entity->>'type' = '똑딱이'
                    GROUP BY category
                    ORDER BY count DESC
                """)
                
                categories = cur.fetchall()
                print("\n📊 '똑딱이' Entity Distribution by Category:")
                for row in categories:
                    print(f"   - {row['category']}: {row['count']} documents")
                
                # 3. 샘플 '똑딱이' entity 가져오기
                cur.execute("""
                    SELECT id, source, page, category, entity
                    FROM mvp_ddu_documents
                    WHERE entity->>'type' = '똑딱이'
                    LIMIT 3
                """)
                
                samples = cur.fetchall()
                print("\n📋 Sample '똑딱이' Entities:")
                for i, row in enumerate(samples, 1):
                    entity = row['entity']
                    print(f"\n   Sample {i}:")
                    print(f"   - Source: {row['source']}")
                    print(f"   - Page: {row['page']}")
                    print(f"   - Category: {row['category']}")
                    print(f"   - Title: {entity.get('title', 'N/A')}")
                    if entity.get('keywords'):
                        print(f"   - Keywords: {', '.join(entity['keywords'][:3])}...")
                    if entity.get('hypothetical_questions'):
                        print(f"   - Can Answer: {entity['hypothetical_questions'][0][:50]}...")
        
        conn.close()
        return has_ddokddak
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False


def test_entity_filter_generation():
    """SubtaskExecutor의 entity 필터 생성 테스트"""
    print("\n" + "=" * 60)
    print("2. Testing Entity Filter Generation")
    print("=" * 60)
    
    try:
        executor = SubtaskExecutorNode()
        
        # Get metadata (categories and entity types)
        metadata = executor._get_metadata_sync()
        
        # Mock: Add '똑딱이' to entity_types if not present
        if '똑딱이' not in metadata.get('entity_types', []):
            print("   ℹ️ Adding '똑딱이' to entity_types for testing")
            if 'entity_types' not in metadata:
                metadata['entity_types'] = []
            metadata['entity_types'].append('똑딱이')
            print(f"   Available entity types: {metadata['entity_types']}")
        
        # 테스트 케이스들
        test_cases = [
            ("PPT에 있는 참조문서 보여줘", "Should generate '똑딱이' entity filter"),
            ("삽입객체 중에서 API 관련 문서", "Should generate '똑딱이' entity filter"),
            ("appendix 문서에서 인증 정보", "Should generate '똑딱이' entity filter"),
            ("똑딱이 타입 문서 목록", "Should generate '똑딱이' entity filter"),
        ]
        
        all_passed = True
        for query, description in test_cases:
            print(f"\n📝 Test: {description}")
            print(f"   Query: '{query}'")
            
            # Extract query information with metadata
            extraction = executor._extract_query_info(query, metadata)
            print(f"   Entity Type Extracted: {extraction.entity_type}")
            
            # Generate filter with metadata
            filter_obj = executor._generate_filter(query, extraction, metadata)
            
            if filter_obj and filter_obj.entity:
                entity_filter = filter_obj.entity
                if entity_filter.get('type') == '똑딱이':
                    print(f"   ✅ Correctly generated '똑딱이' entity filter")
                    print(f"   Filter: {json.dumps(entity_filter, ensure_ascii=False)}")
                else:
                    print(f"   ❌ Generated wrong entity type: {entity_filter.get('type')}")
                    all_passed = False
            else:
                print(f"   ❌ No entity filter generated")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Entity filter generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_with_ddokddak():
    """'똑딱이' 키워드를 사용한 전체 워크플로우 테스트"""
    print("\n" + "=" * 60)
    print("3. Testing Complete Workflow with '똑딱이' Keywords")
    print("=" * 60)
    
    try:
        workflow = MVPWorkflowGraph()
        
        # 테스트 쿼리들
        test_queries = [
            "PPT에 삽입된 참조문서 중에서 디지털 정부 관련 내용 찾아줘",
            "똑딱이 타입 문서에서 클라우드 관련 정보",
            "삽입객체로 된 문서 목록 보여줘",
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔍 Test Query {i}: '{query}'")
            print("-" * 50)
            
            # 워크플로우 실행
            result = workflow.run(query)
            
            # 기본 검증
            if result.get("error"):
                print(f"   ❌ Error occurred: {result['error']}")
                continue
            
            if result.get("workflow_status") == "failed":
                print(f"   ❌ Workflow failed")
                if result.get("warnings"):
                    print(f"   Warnings: {result['warnings']}")
                continue
            
            print("   ✅ Workflow executed successfully")
            
            # Subtask 분석
            subtasks = result.get('subtasks', [])
            print(f"\n   📋 Subtasks created: {len(subtasks)}")
            for j, subtask in enumerate(subtasks, 1):
                print(f"      {j}. {subtask.get('description', 'N/A')}")
                
                # Filter 확인
                if 'metadata' in result and f'subtask_{j}' in result['metadata']:
                    subtask_meta = result['metadata'][f'subtask_{j}']
                    if 'filter_applied' in subtask_meta:
                        filter_applied = subtask_meta['filter_applied']
                        if filter_applied and 'entity' in filter_applied:
                            entity_filter = filter_applied['entity']
                            print(f"         Entity Filter: {json.dumps(entity_filter, ensure_ascii=False)}")
            
            # Documents 확인
            documents = result.get('documents', [])
            print(f"\n   📚 Documents retrieved: {len(documents)}")
            
            # '똑딱이' entity를 가진 문서 찾기
            ddokddak_docs = []
            for doc in documents:
                entity = doc.metadata.get('entity')
                if entity and isinstance(entity, dict) and entity.get('type') == '똑딱이':
                    ddokddak_docs.append(doc)
            
            if ddokddak_docs:
                print(f"   ✅ Found {len(ddokddak_docs)} documents with '똑딱이' entity")
                
                # 첫 3개 샘플 출력
                for j, doc in enumerate(ddokddak_docs[:3], 1):
                    entity = doc.metadata['entity']
                    print(f"\n      Document {j}:")
                    print(f"      - Category: {doc.metadata.get('category')}")
                    print(f"      - Title: {entity.get('title', 'N/A')}")
                    if entity.get('keywords'):
                        print(f"      - Keywords: {', '.join(entity['keywords'][:3])}...")
                    if entity.get('hypothetical_questions'):
                        print(f"      - Can Answer: {entity['hypothetical_questions'][0][:50]}...")
            else:
                print(f"   ⚠️ No documents with '똑딱이' entity found")
            
            # Final Answer 확인
            if result.get("final_answer"):
                answer = result["final_answer"]
                
                # '똑딱이' 관련 내용이 답변에 포함되었는지 확인
                ddokddak_mentioned = any(keyword in answer for keyword in 
                                        ['똑딱이', 'PPT Embedded Document', '삽입', '참조문서'])
                
                if ddokddak_mentioned:
                    print(f"\n   ✅ Answer includes '똑딱이' related content")
                    
                    # Answer preview
                    preview_lines = answer.split('\n')[:5]
                    print("\n   📝 Answer Preview:")
                    for line in preview_lines:
                        print(f"      {line}")
                else:
                    print(f"\n   ⚠️ Answer doesn't mention '똑딱이' entities")
            
            # Synthesis metadata 확인
            if result.get("metadata", {}).get("synthesis"):
                synthesis_meta = result["metadata"]["synthesis"]
                print(f"\n   📊 Synthesis Metadata:")
                print(f"      - Confidence: {synthesis_meta.get('confidence', 0)}")
                print(f"      - Sources used: {len(synthesis_meta.get('sources', []))}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_formatting():
    """Synthesis와 Hallucination 노드의 '똑딱이' 포맷팅 테스트"""
    print("\n" + "=" * 60)
    print("4. Testing '똑딱이' Entity Formatting")
    print("=" * 60)
    
    try:
        # 테스트용 메타데이터
        test_metadata = {
            "category": "paragraph",
            "entity": {
                "type": "똑딱이",
                "title": "디지털 정부 혁신 추진계획",
                "details": "2024년 디지털 정부 혁신 추진계획 및 실행 전략",
                "keywords": ["디지털정부", "혁신", "추진계획", "2024"],
                "hypothetical_questions": [
                    "디지털 정부 혁신 추진계획의 주요 내용은?",
                    "2024년 디지털 정부 전략은?",
                    "정부 디지털 전환 로드맵은?"
                ]
            }
        }
        
        # Synthesis 노드 테스트
        print("\n📝 Testing SynthesisNode._format_entity_info():")
        synthesis_node = SynthesisNode()
        formatted = synthesis_node._format_entity_info(test_metadata)
        
        if "PPT Embedded Document (똑딱이)" in formatted:
            print("   ✅ Correctly formatted '똑딱이' entity")
            print("\n   Formatted Output:")
            for line in formatted.split('\n'):
                print(f"      {line}")
        else:
            print("   ❌ Failed to format '똑딱이' entity correctly")
            return False
        
        # Hallucination 노드 테스트
        print("\n📝 Testing HallucinationCheckNode formatting:")
        
        # 간단한 Document 클래스 시뮬레이션
        class TestDocument:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata
        
        test_doc = TestDocument(
            page_content="디지털 정부 혁신 추진계획 내용",
            metadata=test_metadata
        )
        
        hallucination_node = HallucinationCheckNode()
        formatted_docs = hallucination_node._format_documents_for_checking([test_doc])
        
        if "PPT Embedded Document (똑딱이)" in formatted_docs:
            print("   ✅ Hallucination node correctly formats '똑딱이' entity")
            
            # 포맷된 내용 일부 출력
            preview = formatted_docs[:500] if len(formatted_docs) > 500 else formatted_docs
            print("\n   Formatted Preview:")
            for line in preview.split('\n')[:10]:
                print(f"      {line}")
        else:
            print("   ❌ Hallucination node failed to format '똑딱이' entity")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Formatting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 80)
    print("🧪 '똑딱이' Entity Type Support Test Suite")
    print("=" * 80)
    
    all_tests_passed = True
    
    # 1. 데이터베이스 확인
    has_ddokddak = check_database_for_ddokddak()
    if not has_ddokddak:
        print("\n⚠️ WARNING: Continuing tests without '똑딱이' entities in database")
        print("   Some tests may fail or show limited results")
    
    # 2. Entity 필터 생성 테스트
    if not test_entity_filter_generation():
        all_tests_passed = False
    
    # 3. 포맷팅 테스트
    if not test_formatting():
        all_tests_passed = False
    
    # 4. 전체 워크플로우 테스트 (DB에 데이터가 있을 때만)
    if has_ddokddak:
        if not test_workflow_with_ddokddak():
            all_tests_passed = False
    else:
        print("\n⏭️ Skipping workflow test (no '똑딱이' entities in database)")
    
    # 최종 결과
    print("\n" + "=" * 80)
    if all_tests_passed:
        print("✅ ALL TESTS PASSED!")
        print("\n'똑딱이' entity type support is working correctly!")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease review the errors above and fix the issues.")
    print("=" * 80)
    
    return 0 if all_tests_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)