#!/usr/bin/env python3
"""
DDokDDak Entity Transplanter
DDokDDak(똑딱이) JSON 파일의 메타데이터를 DDU documents에 이식하는 스크립트

Usage:
    # 기본 실행 (환경변수 사용)
    uv run python scripts/transplant_ddokddak_entity.py
    
    # 커스텀 파일 지정
    uv run python scripts/transplant_ddokddak_entity.py --ddokddak-json <path> --ddu-pickle <path>
    
Example:
    # 기본 실행
    uv run python scripts/transplant_ddokddak_entity.py
    
    # 특정 파일 지정
    uv run python scripts/transplant_ddokddak_entity.py \
        --ddokddak-json data/ddokddak_custom.json \
        --ddu-pickle data/custom_ddu.pkl
"""

# ============================================================================
# 환경 변수 설정 (DEFAULT VALUES)
# ============================================================================
DEFAULT_DDOKDDAK_JSON = "data/ddokddak_디지털정부혁신_추진계획_TEST3P_20250902_150632.json"
DEFAULT_DDU_PICKLE = "data/merged_ddu_documents.pkl"
DEFAULT_OUTPUT_PICKLE = "data/transplanted_ddu_documents.pkl"
DEFAULT_OUTPUT_JSON = "data/transplanted_ddu_documents.json"  # JSON 출력 경로

# 이식 대상 카테고리 설정
ALLOWED_CATEGORIES = ['paragraph', 'heading1', 'heading2', 'heading3']

# 실행 모드 설정
DEFAULT_DRY_RUN = False  # False: 실제 저장, True: 검증만
DEFAULT_VERBOSE = True   # 상세 출력 여부
DEFAULT_SAVE_JSON = True  # JSON도 함께 저장

# ============================================================================

import json
import pickle
import sys
import os
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수에서 값 읽기 (override defaults if set)
DDOKDDAK_JSON = os.getenv("TRANSPLANT_DDOKDDAK_JSON", DEFAULT_DDOKDDAK_JSON)
DDU_PICKLE = os.getenv("TRANSPLANT_DDU_PICKLE", DEFAULT_DDU_PICKLE)
OUTPUT_PICKLE = os.getenv("TRANSPLANT_OUTPUT_PICKLE", DEFAULT_OUTPUT_PICKLE)
OUTPUT_JSON = os.getenv("TRANSPLANT_OUTPUT_JSON", DEFAULT_OUTPUT_JSON)
DRY_RUN = os.getenv("TRANSPLANT_DRY_RUN", str(DEFAULT_DRY_RUN)).lower() == "true"
VERBOSE = os.getenv("TRANSPLANT_VERBOSE", str(DEFAULT_VERBOSE)).lower() == "true"
SAVE_JSON = os.getenv("TRANSPLANT_SAVE_JSON", str(DEFAULT_SAVE_JSON)).lower() == "true"

# Langchain Document import
try:
    from langchain.schema import Document
except ImportError:
    from langchain_core.documents import Document


class DdokddakEntityTransplanter:
    """DDokDDak 메타데이터를 DDU documents에 이식하는 클래스"""
    
    # 이식 대상 카테고리 (전역 설정 사용)
    ALLOWED_CATEGORIES = ALLOWED_CATEGORIES
    
    def __init__(self, ddokddak_json_path: str, ddu_pickle_path: str):
        """
        초기화 및 데이터 검증
        
        Args:
            ddokddak_json_path: DDokDDak JSON 파일 경로
            ddu_pickle_path: DDU documents pickle 파일 경로
        
        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            ValueError: 데이터 검증 실패시
        """
        print(f"\n{'='*60}")
        print("DDokDDak Entity Transplanter 초기화")
        print(f"{'='*60}")
        
        # 파일 존재 확인
        if not os.path.exists(ddokddak_json_path):
            raise FileNotFoundError(f"DDokDDak JSON file not found: {ddokddak_json_path}")
        if not os.path.exists(ddu_pickle_path):
            raise FileNotFoundError(f"DDU pickle file not found: {ddu_pickle_path}")
        
        # 데이터 로드 및 검증
        print(f"📄 Loading DDokDDak: {Path(ddokddak_json_path).name}")
        self.ddokddak_data = self._load_and_validate_ddokddak(ddokddak_json_path)
        
        print(f"📦 Loading DDU documents: {Path(ddu_pickle_path).name}")
        self.ddu_documents = self._load_ddu_pickle(ddu_pickle_path)
        print(f"   Total DDU documents: {len(self.ddu_documents)}")
        
        # 통계 초기화
        self.transplant_stats = {
            'success': 0,
            'skipped': 0,
            'matched_docs': 0,
            'by_category': defaultdict(int)
        }
        
        # 메타데이터 정보 출력
        self._print_metadata_info()
    
    def _load_and_validate_ddokddak(self, json_path: str) -> Dict[str, Any]:
        """
        DDokDDak 데이터 로드 및 검증
        
        Args:
            json_path: JSON 파일 경로
            
        Returns:
            검증된 DDokDDak 데이터
            
        Raises:
            ValueError: 검증 실패시
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 기본 구조 확인
        if 'metadata' not in data:
            raise ValueError(f"Missing 'metadata' in DDokDDak JSON")
        if 'result' not in data:
            raise ValueError(f"Missing 'result' in DDokDDak JSON")
        
        # source_page None 체크
        source_page = data['metadata'].get('source_page')
        if source_page is None:
            raise ValueError(
                f"source_page cannot be None in DDokDDak JSON\n"
                f"  File: {json_path}"
            )
        
        # 필수 필드 체크
        required_fields = ['title', 'keywords', 'hypothetical_questions']
        missing_fields = []
        for field in required_fields:
            if field not in data['result'] or not data['result'][field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(
                f"Missing or empty required fields in DDokDDak JSON:\n"
                f"  Fields: {', '.join(missing_fields)}\n"
                f"  File: {json_path}"
            )
        
        print(f"✅ DDokDDak validation passed")
        return data
    
    def _load_ddu_pickle(self, pickle_path: str) -> List[Document]:
        """
        DDU pickle 파일 로드
        
        Args:
            pickle_path: Pickle 파일 경로
            
        Returns:
            DDU documents 리스트
        """
        with open(pickle_path, 'rb') as f:
            documents = pickle.load(f)
        
        # 타입 확인
        if not isinstance(documents, list):
            raise ValueError(f"DDU pickle must contain a list, got {type(documents)}")
        
        if documents and not hasattr(documents[0], 'metadata'):
            raise ValueError(f"DDU documents must have metadata attribute")
        
        return documents
    
    def _print_metadata_info(self):
        """DDokDDak 메타데이터 정보 출력"""
        print(f"\n📋 DDokDDak Metadata:")
        print(f"   Source file: {self.ddokddak_data['metadata']['source_file']}")
        print(f"   Source page: {self.ddokddak_data['metadata']['source_page']}")
        print(f"   Title: {self.ddokddak_data['result']['title']}")
        print(f"   Keywords: {len(self.ddokddak_data['result']['keywords'])} items")
        print(f"   Questions: {len(self.ddokddak_data['result']['hypothetical_questions'])} items")
        
        # 처음 3개 키워드 출력
        keywords = self.ddokddak_data['result']['keywords'][:3]
        print(f"   Sample keywords: {', '.join(keywords)}...")
    
    def find_matching_documents(self) -> List[Document]:
        """
        정확한 파일명과 페이지로 매칭되는 DDU 문서 찾기
        
        Returns:
            매칭된 DDU documents 리스트
            
        Raises:
            ValueError: 매칭되는 문서가 없을 때
        """
        source_file = self.ddokddak_data['metadata']['source_file']
        source_page = self.ddokddak_data['metadata']['source_page']
        
        print(f"\n🔍 Finding matching documents...")
        print(f"   Target file: {source_file}")
        print(f"   Target page: {source_page}")
        
        matches = []
        
        # 각 DDU 문서 확인
        for ddu in self.ddu_documents:
            ddu_source = ddu.metadata.get('source', '')
            ddu_page = ddu.metadata.get('page')
            
            # 정확한 매칭 (파일명에 data/ prefix가 있을 수 있음)
            source_match = (
                ddu_source == source_file or 
                ddu_source == f"data/{source_file}" or
                ddu_source.endswith(f"/{source_file}")
            )
            
            if source_match and ddu_page == source_page:
                matches.append(ddu)
        
        # 매칭 실패시 에러
        if not matches:
            # 디버깅을 위해 첫 5개 문서의 source 출력
            print("\n❌ No matching documents found!")
            print("\nFirst 5 DDU document sources for debugging:")
            for i, ddu in enumerate(self.ddu_documents[:5]):
                print(f"   {i+1}. source: {ddu.metadata.get('source')}, page: {ddu.metadata.get('page')}")
            
            raise ValueError(
                f"No matching DDU documents found for:\n"
                f"  File: {source_file}\n"
                f"  Page: {source_page}\n"
                f"  Please check if the file name and page number are correct."
            )
        
        print(f"✅ Found {len(matches)} matching documents")
        
        # 카테고리별 분류
        category_counts = defaultdict(int)
        for doc in matches:
            category = doc.metadata.get('category', 'unknown')
            category_counts[category] += 1
        
        print(f"\n📊 Matching documents by category:")
        for cat, count in sorted(category_counts.items()):
            status = "✅" if cat in self.ALLOWED_CATEGORIES else "⏭️"
            print(f"   {status} {cat}: {count}")
        
        self.transplant_stats['matched_docs'] = len(matches)
        return matches
    
    def transform_entity(self, ddokddak_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        DDokDDak 데이터를 DDU entity 형식으로 변환 (길이 제한 없음)
        
        Args:
            ddokddak_result: DDokDDak result 데이터
            
        Returns:
            DDU entity 형식의 딕셔너리
        """
        return {
            "type": "똑딱이",  # 고정값
            "title": ddokddak_result.get("title", ""),
            "details": ddokddak_result.get("details", ""),  # 길이 제한 없음
            "keywords": ddokddak_result.get("keywords", []),
            "hypothetical_questions": ddokddak_result.get("hypothetical_questions", []),
            "raw_output": ddokddak_result.get("raw_output", "")  # 길이 제한 없음
        }
    
    def transplant_entities(self) -> Dict[str, Any]:
        """
        메인 이식 실행
        
        Returns:
            이식 통계
        """
        print(f"\n{'='*60}")
        print("🔄 Starting Entity Transplant")
        print(f"{'='*60}")
        
        try:
            # 1. 매칭 문서 찾기 (실패시 에러)
            matched_documents = self.find_matching_documents()
            
            # 2. Entity 변환
            new_entity = self.transform_entity(self.ddokddak_data['result'])
            print(f"\n📝 Entity prepared for transplant")
            print(f"   Type: {new_entity['type']}")
            print(f"   Title: {new_entity['title'][:50]}...")
            
            # 3. 각 매칭된 문서 처리
            print(f"\n🚀 Processing {len(matched_documents)} documents...")
            
            for i, ddu_doc in enumerate(matched_documents, 1):
                category = ddu_doc.metadata.get('category', 'unknown')
                doc_id = ddu_doc.metadata.get('id', f'doc_{i}')
                
                # 허용된 카테고리만 처리
                if category in self.ALLOWED_CATEGORIES:
                    # 기존 entity 백업 (있는 경우)
                    if 'entity' in ddu_doc.metadata and ddu_doc.metadata['entity']:
                        ddu_doc.metadata['original_entity'] = ddu_doc.metadata['entity']
                    
                    # Entity 이식
                    ddu_doc.metadata['entity'] = new_entity
                    
                    # 통계 업데이트
                    self.transplant_stats['success'] += 1
                    self.transplant_stats['by_category'][category] += 1
                    
                    print(f"   ✅ [{i}/{len(matched_documents)}] Transplanted to {category} (ID: {doc_id})")
                else:
                    self.transplant_stats['skipped'] += 1
                    print(f"   ⏭️  [{i}/{len(matched_documents)}] Skipped {category} (not allowed)")
            
            print(f"\n✅ Transplant completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Transplant failed: {e}")
            raise
        
        return self.transplant_stats
    
    def save_results(self, output_path: str, save_json: bool = False, json_path: str = None):
        """
        결과 저장 (pickle 및 선택적으로 JSON)
        
        Args:
            output_path: 출력 pickle 파일 경로
            save_json: JSON도 저장할지 여부
            json_path: JSON 파일 경로 (None이면 output_path 기반으로 생성)
        """
        print(f"\n💾 Saving results...")
        
        # Pickle 저장
        # 백업 생성
        if os.path.exists(output_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{output_path}.backup_{timestamp}"
            shutil.copy(output_path, backup_path)
            print(f"   📁 Backup created: {Path(backup_path).name}")
        
        # 수정된 데이터 저장
        with open(output_path, 'wb') as f:
            pickle.dump(self.ddu_documents, f)
        
        print(f"   ✅ Saved pickle to: {Path(output_path).name}")
        
        # 파일 크기 정보
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        print(f"   📊 Pickle size: {file_size:.2f} MB")
        
        # JSON 저장 (선택적)
        if save_json:
            if json_path is None:
                # pickle 경로를 기반으로 JSON 경로 생성
                json_path = str(Path(output_path).with_suffix('.json'))
            
            print(f"\n   📝 Converting to JSON...")
            
            # Document 객체를 dict로 변환
            json_documents = []
            for doc in self.ddu_documents:
                doc_dict = {
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                }
                json_documents.append(doc_dict)
            
            # JSON 파일로 저장
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_documents, f, ensure_ascii=False, indent=2)
            
            print(f"   ✅ Saved JSON to: {Path(json_path).name}")
            
            # JSON 파일 크기
            json_size = os.path.getsize(json_path) / (1024 * 1024)  # MB
            print(f"   📊 JSON size: {json_size:.2f} MB")
    
    def generate_report(self):
        """이식 결과 보고서 출력"""
        print(f"\n{'='*60}")
        print("📊 TRANSPLANT REPORT")
        print(f"{'='*60}")
        
        print(f"\n📈 Summary:")
        print(f"   Matched documents: {self.transplant_stats['matched_docs']}")
        print(f"   Successfully transplanted: {self.transplant_stats['success']}")
        print(f"   Skipped (wrong category): {self.transplant_stats['skipped']}")
        
        if self.transplant_stats['success'] > 0:
            success_rate = (self.transplant_stats['success'] / self.transplant_stats['matched_docs']) * 100
            print(f"   Success rate: {success_rate:.1f}%")
        
        if self.transplant_stats['by_category']:
            print(f"\n📋 By Category:")
            for cat, count in sorted(self.transplant_stats['by_category'].items()):
                print(f"   • {cat}: {count}")
        
        print(f"\n{'='*60}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='DDokDDak Entity Transplanter - 똑딱이 메타데이터를 DDU documents에 이식',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
환경 변수 설정 (.env 파일 또는 환경변수):
  TRANSPLANT_DDOKDDAK_JSON  - DDokDDak JSON 파일 경로
  TRANSPLANT_DDU_PICKLE     - DDU pickle 파일 경로
  TRANSPLANT_OUTPUT_PICKLE  - 출력 pickle 파일 경로
  TRANSPLANT_OUTPUT_JSON    - 출력 JSON 파일 경로
  TRANSPLANT_DRY_RUN       - 검증만 수행 (true/false)
  TRANSPLANT_VERBOSE       - 상세 출력 (true/false)
  TRANSPLANT_SAVE_JSON     - JSON도 함께 저장 (true/false)

Examples:
  # 기본 실행 (환경변수 사용)
  uv run python scripts/transplant_ddokddak_entity.py
  
  # 커스텀 파일 지정
  uv run python scripts/transplant_ddokddak_entity.py \\
    --ddokddak-json data/custom.json \\
    --ddu-pickle data/custom.pkl
  
  # Dry run 모드
  uv run python scripts/transplant_ddokddak_entity.py --dry-run
  
  # Batch processing
  for json in data/ddokddak_*.json; do
    uv run python scripts/transplant_ddokddak_entity.py --ddokddak-json "$json"
  done
        """
    )
    
    # 모든 인자를 선택적으로 만들고 기본값 제공
    parser.add_argument(
        '--ddokddak-json',
        default=DDOKDDAK_JSON,
        help=f'DDokDDak JSON 파일 경로 (default: {DDOKDDAK_JSON})'
    )
    parser.add_argument(
        '--ddu-pickle',
        default=DDU_PICKLE,
        help=f'DDU documents pickle 파일 경로 (default: {DDU_PICKLE})'
    )
    parser.add_argument(
        '--output-pickle',
        default=OUTPUT_PICKLE,
        help=f'출력 pickle 파일 경로 (default: {OUTPUT_PICKLE})'
    )
    parser.add_argument(
        '--output-json',
        default=OUTPUT_JSON,
        help=f'출력 JSON 파일 경로 (default: {OUTPUT_JSON})'
    )
    parser.add_argument(
        '--save-json',
        action='store_true',
        default=SAVE_JSON,
        help=f'JSON 파일도 함께 저장 (default: {SAVE_JSON})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=DRY_RUN,
        help=f'검증만 수행, 결과 저장하지 않음 (default: {DRY_RUN})'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=VERBOSE,
        help=f'상세 출력 모드 (default: {VERBOSE})'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🧬 DDokDDak Entity Transplanter")
    print("="*60)
    print(f"Version: 1.1.0")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 현재 설정 출력
    if args.verbose:
        print("\n📋 Current Configuration:")
        print(f"   DDokDDak JSON: {args.ddokddak_json}")
        print(f"   DDU Pickle: {args.ddu_pickle}")
        print(f"   Output Pickle: {args.output_pickle}")
        print(f"   Output JSON: {args.output_json}")
        print(f"   Save JSON: {args.save_json}")
        print(f"   Dry Run: {args.dry_run}")
        print(f"   Verbose: {args.verbose}")
        print(f"   Allowed Categories: {', '.join(ALLOWED_CATEGORIES)}")
    
    try:
        # 1. Transplanter 초기화 (검증 포함)
        transplanter = DdokddakEntityTransplanter(
            args.ddokddak_json,
            args.ddu_pickle
        )
        
        # 2. Entity 이식 실행
        stats = transplanter.transplant_entities()
        
        # 3. 결과 저장 (dry-run이 아닌 경우)
        if not args.dry_run:
            transplanter.save_results(
                args.output_pickle,
                save_json=args.save_json,
                json_path=args.output_json
            )
        else:
            print("\n⚠️  Dry-run mode: Results not saved")
        
        # 4. 보고서 출력
        transplanter.generate_report()
        
        print("\n✨ All done!")
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ File Error: {e}")
        return 1
        
    except ValueError as e:
        print(f"\n❌ Validation Error: {e}")
        return 1
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())