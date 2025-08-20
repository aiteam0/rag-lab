"""
Pickle File Loader for DDU Documents
Handles loading and processing of existing pickle data
"""

import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from .models import DDUDocument, TEXT_CATEGORIES
import json


class DDUPickleLoader:
    """DDU Pickle 파일 로더"""
    
    def __init__(self, file_path: str):
        """
        Args:
            file_path: Pickle 파일 경로
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Pickle file not found: {file_path}")
    
    def load_raw(self) -> List[Any]:
        """
        원본 pickle 데이터 로드
        
        Returns:
            원본 데이터 리스트
        """
        with open(self.file_path, 'rb') as f:
            data = pickle.load(f)
        return data
    
    def load_documents(self) -> List[DDUDocument]:
        """
        Pickle 파일에서 DDUDocument 객체 리스트로 변환
        
        Returns:
            DDUDocument 객체 리스트
        """
        raw_documents = self.load_raw()
        ddu_documents = []
        
        for doc in raw_documents:
            # LangChain Document 형식 처리
            if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                ddu_doc = self._convert_langchain_to_ddu(doc)
                if ddu_doc:
                    ddu_documents.append(ddu_doc)
            # 딕셔너리 형식 처리
            elif isinstance(doc, dict):
                ddu_doc = self._convert_dict_to_ddu(doc)
                if ddu_doc:
                    ddu_documents.append(ddu_doc)
        
        return ddu_documents
    
    def _convert_langchain_to_ddu(self, doc: Document) -> Optional[DDUDocument]:
        """
        LangChain Document를 DDUDocument로 변환
        
        Args:
            doc: LangChain Document 객체
            
        Returns:
            DDUDocument 객체 또는 None
        """
        try:
            metadata = doc.metadata
            
            # 필수 필드 확인
            if not metadata.get('source') or not metadata.get('category'):
                return None
            
            # Entity 정보 처리
            entity = metadata.get('entity')
            if entity and isinstance(entity, str):
                # JSON 문자열인 경우 파싱
                try:
                    entity = json.loads(entity)
                except:
                    pass
            
            # DDUDocument 생성
            ddu_doc = DDUDocument(
                source=metadata.get('source'),
                page=metadata.get('page'),
                category=metadata.get('category'),
                page_content=doc.page_content if metadata.get('category') in TEXT_CATEGORIES else metadata.get('original_text', doc.page_content),
                translation_text=metadata.get('translation_text'),
                contextualize_text=metadata.get('contextualize_text'),
                caption=metadata.get('caption'),
                entity=entity,
                image_path=metadata.get('image_path'),
                human_feedback=metadata.get('human_feedback', '')
            )
            
            return ddu_doc
            
        except Exception as e:
            print(f"Error converting document: {e}")
            return None
    
    def _convert_dict_to_ddu(self, doc_dict: Dict[str, Any]) -> Optional[DDUDocument]:
        """
        딕셔너리를 DDUDocument로 변환
        
        Args:
            doc_dict: 문서 딕셔너리
            
        Returns:
            DDUDocument 객체 또는 None
        """
        try:
            # page_content와 metadata가 있는 경우
            if 'page_content' in doc_dict and 'metadata' in doc_dict:
                metadata = doc_dict['metadata']
                page_content = doc_dict['page_content']
            else:
                # 직접 필드가 있는 경우
                metadata = doc_dict
                page_content = doc_dict.get('page_content', doc_dict.get('original_text', ''))
            
            # 필수 필드 확인
            if not metadata.get('source') or not metadata.get('category'):
                return None
            
            # DDUDocument 생성
            ddu_doc = DDUDocument(
                source=metadata.get('source'),
                page=metadata.get('page'),
                category=metadata.get('category'),
                page_content=page_content,
                translation_text=metadata.get('translation_text'),
                contextualize_text=metadata.get('contextualize_text'),
                caption=metadata.get('caption'),
                entity=metadata.get('entity'),
                image_path=metadata.get('image_path'),
                human_feedback=metadata.get('human_feedback', '')
            )
            
            return ddu_doc
            
        except Exception as e:
            print(f"Error converting dict: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        로드된 문서의 통계 정보 반환
        
        Returns:
            통계 정보 딕셔너리
        """
        documents = self.load_documents()
        
        # 카테고리별 통계
        category_stats = {}
        for doc in documents:
            category = doc.category
            category_stats[category] = category_stats.get(category, 0) + 1
        
        # 소스별 통계
        source_stats = {}
        for doc in documents:
            source = doc.source
            source_stats[source] = source_stats.get(source, 0) + 1
        
        # 페이지 범위
        pages = [doc.page for doc in documents if doc.page is not None]
        page_range = {
            "min": min(pages) if pages else None,
            "max": max(pages) if pages else None
        }
        
        # Entity 타입 통계
        entity_types = {}
        for doc in documents:
            if doc.entity and isinstance(doc.entity, dict):
                entity_type = doc.entity.get('type')
                if entity_type:
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        return {
            "total_documents": len(documents),
            "categories": category_stats,
            "sources": source_stats,
            "page_range": page_range,
            "entity_types": entity_types,
            "has_translation": sum(1 for doc in documents if doc.translation_text),
            "has_contextualize": sum(1 for doc in documents if doc.contextualize_text),
            "has_caption": sum(1 for doc in documents if doc.caption)
        }
    
    @staticmethod
    def validate_pickle_file(file_path: str) -> bool:
        """
        Pickle 파일 유효성 검증
        
        Args:
            file_path: 검증할 파일 경로
            
        Returns:
            유효 여부
        """
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # 리스트 형식 확인
            if not isinstance(data, list):
                return False
            
            # 최소 하나 이상의 문서
            if len(data) == 0:
                return False
            
            # 첫 번째 문서 구조 확인
            first_doc = data[0]
            if hasattr(first_doc, 'metadata'):
                # LangChain Document 형식
                return hasattr(first_doc, 'page_content')
            elif isinstance(first_doc, dict):
                # 딕셔너리 형식
                return 'source' in first_doc or 'metadata' in first_doc
            
            return False
            
        except Exception as e:
            print(f"Validation error: {e}")
            return False