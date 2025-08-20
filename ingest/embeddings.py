"""
Dual Language Embeddings for Korean/English
Uses OpenAI text-embedding-3-small model
"""

from langchain_openai import OpenAIEmbeddings
from typing import List, Tuple, Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()


class DualLanguageEmbeddings:
    """한국어/영어 이중 임베딩 처리"""
    
    def __init__(self):
        """OpenAI 임베딩 모델 초기화"""
        self.embeddings = OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            dimensions=int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
        )
    
    async def embed_document(self, doc: Dict[str, Any]) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        """
        문서에 대한 한국어/영어 임베딩 생성
        
        Args:
            doc: 문서 딕셔너리 (DDUDocument.to_db_dict() 형식)
            
        Returns:
            (한국어 임베딩, 영어 임베딩) 튜플
        """
        # 한국어 텍스트 조합
        korean_text = self._combine_korean_text(doc)
        
        # 영어 텍스트
        english_text = doc.get('translation_text', '')
        
        # 임베딩 생성
        korean_embedding = None
        english_embedding = None
        
        if korean_text and english_text:
            # 배치로 두 언어 임베딩 생성
            embeddings = await self.embeddings.aembed_documents([korean_text, english_text])
            korean_embedding = embeddings[0]
            english_embedding = embeddings[1]
        elif korean_text:
            # 한국어만 임베딩
            korean_embedding = await self.embeddings.aembed_query(korean_text)
        elif english_text:
            # 영어만 임베딩
            english_embedding = await self.embeddings.aembed_query(english_text)
        
        return korean_embedding, english_embedding
    
    def embed_document_sync(self, doc: Dict[str, Any]) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        """
        동기 버전: 문서에 대한 한국어/영어 임베딩 생성
        
        Args:
            doc: 문서 딕셔너리
            
        Returns:
            (한국어 임베딩, 영어 임베딩) 튜플
        """
        # 한국어 텍스트 조합
        korean_text = self._combine_korean_text(doc)
        
        # 영어 텍스트
        english_text = doc.get('translation_text', '')
        
        # 임베딩 생성
        korean_embedding = None
        english_embedding = None
        
        if korean_text and english_text:
            # 배치로 두 언어 임베딩 생성
            embeddings = self.embeddings.embed_documents([korean_text, english_text])
            korean_embedding = embeddings[0]
            english_embedding = embeddings[1]
        elif korean_text:
            # 한국어만 임베딩
            korean_embedding = self.embeddings.embed_query(korean_text)
        elif english_text:
            # 영어만 임베딩
            english_embedding = self.embeddings.embed_query(english_text)
        
        return korean_embedding, english_embedding
    
    async def embed_query(self, query: str, language: str = "korean") -> List[float]:
        """
        쿼리 임베딩 생성
        
        Args:
            query: 검색 쿼리
            language: "korean" 또는 "english"
            
        Returns:
            쿼리 임베딩 벡터
        """
        return await self.embeddings.aembed_query(query)
    
    def embed_query_sync(self, query: str, language: str = "korean") -> List[float]:
        """
        동기 버전: 쿼리 임베딩 생성
        
        Args:
            query: 검색 쿼리
            language: "korean" 또는 "english"
            
        Returns:
            쿼리 임베딩 벡터
        """
        return self.embeddings.embed_query(query)
    
    def _combine_korean_text(self, doc: Dict[str, Any]) -> str:
        """
        한국어 텍스트 조합 (contextualize_text + page_content + caption)
        
        Args:
            doc: 문서 딕셔너리
            
        Returns:
            조합된 한국어 텍스트
        """
        texts = []
        
        # contextualize_text 우선
        if doc.get('contextualize_text'):
            texts.append(doc['contextualize_text'])
        
        # page_content 추가
        if doc.get('page_content'):
            texts.append(doc['page_content'])
        
        # caption 추가 (있으면)
        if doc.get('caption'):
            texts.append(doc['caption'])
        
        # entity의 키워드 추가 (있으면)
        if doc.get('entity') and isinstance(doc['entity'], dict):
            keywords = doc['entity'].get('keywords', [])
            if keywords:
                texts.append(' '.join(keywords))
        
        return ' '.join(texts).strip()
    
    async def batch_embed_documents(
        self, 
        documents: List[Dict[str, Any]], 
        batch_size: int = 10
    ) -> List[Tuple[Optional[List[float]], Optional[List[float]]]]:
        """
        문서 배치 임베딩 생성
        
        Args:
            documents: 문서 딕셔너리 리스트
            batch_size: 배치 크기
            
        Returns:
            (한국어 임베딩, 영어 임베딩) 튜플 리스트
        """
        results = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            
            # 각 문서의 텍스트 준비
            korean_texts = []
            english_texts = []
            
            for doc in batch:
                korean_texts.append(self._combine_korean_text(doc))
                english_texts.append(doc.get('translation_text', ''))
            
            # 배치 임베딩 생성
            korean_embeddings = []
            english_embeddings = []
            
            # 한국어 임베딩
            valid_korean = [t for t in korean_texts if t]
            if valid_korean:
                korean_emb_results = await self.embeddings.aembed_documents(valid_korean)
                korean_idx = 0
                for text in korean_texts:
                    if text:
                        korean_embeddings.append(korean_emb_results[korean_idx])
                        korean_idx += 1
                    else:
                        korean_embeddings.append(None)
            else:
                korean_embeddings = [None] * len(batch)
            
            # 영어 임베딩
            valid_english = [t for t in english_texts if t]
            if valid_english:
                english_emb_results = await self.embeddings.aembed_documents(valid_english)
                english_idx = 0
                for text in english_texts:
                    if text:
                        english_embeddings.append(english_emb_results[english_idx])
                        english_idx += 1
                    else:
                        english_embeddings.append(None)
            else:
                english_embeddings = [None] * len(batch)
            
            # 결과 조합
            for k_emb, e_emb in zip(korean_embeddings, english_embeddings):
                results.append((k_emb, e_emb))
        
        return results