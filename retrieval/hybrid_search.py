"""
Hybrid Search Implementation
Combines semantic search (vector) and keyword search (FTS) using RRF
"""

import asyncio
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from kiwipiepy import Kiwi
import asyncpg
import numpy as np
from dotenv import load_dotenv
import spacy
from ingest.embeddings import DualLanguageEmbeddings
from retrieval.search_filter import MVPSearchFilter

load_dotenv()

logger = logging.getLogger(__name__)


class HybridSearch:
    """RRF 기반 하이브리드 검색 (시맨틱 + 키워드)"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        """
        Args:
            connection_pool: PostgreSQL 연결 풀
        """
        self.pool = connection_pool
        self.kiwi = Kiwi()
        
        # spaCy 영어 모델 로드 (한 번만 로드하여 성능 최적화)
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("[HYBRID] spaCy English model loaded successfully")
        except Exception as e:
            logger.warning(f"[HYBRID] Failed to load spaCy model: {e}. Falling back to simple keyword extraction.")
            self.nlp = None
            
        self.k = int(os.getenv("SEARCH_RRF_K", "60"))  # RRF 파라미터
        self.embeddings = DualLanguageEmbeddings()
        self.table_name = os.getenv("DB_TABLE_NAME", "mvp_ddu_documents")
    
    def _get_optimal_keyword_count(self, query: str) -> int:
        """
        쿼리 길이에 따른 최적 키워드 수 결정
        
        Args:
            query: 검색 쿼리
            
        Returns:
            최적 키워드 수
        """
        query_length = len(query.split())  # 단어 수 기준
        
        if query_length <= 3:
            return 2  # 짧은 쿼리는 2개
        elif query_length <= 6:
            return 3  # 중간 쿼리는 3개
        else:
            return 4  # 긴 쿼리는 4개
    
    async def search(
        self, 
        query: str, 
        filter: MVPSearchFilter,
        language: str = 'korean',
        top_k: int = None,
        semantic_weight: float = None,
        keyword_weight: float = None
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 실행
        
        Args:
            query: 검색 쿼리
            filter: 검색 필터
            language: 언어 ('korean' 또는 'english')
            top_k: 반환할 최대 문서 수 (None이면 .env 기본값 사용)
            semantic_weight: 시맨틱 검색 가중치 (None이면 .env 기본값 사용)
            keyword_weight: 키워드 검색 가중치 (None이면 .env 기본값 사용)
            
        Returns:
            검색 결과 리스트
        """
        # 기본값 설정
        if top_k is None:
            top_k = int(os.getenv("SEARCH_DEFAULT_TOP_K", "10"))
        if semantic_weight is None:
            semantic_weight = float(os.getenv("SEARCH_DEFAULT_SEMANTIC_WEIGHT", "0.5"))
        if keyword_weight is None:
            keyword_weight = float(os.getenv("SEARCH_DEFAULT_KEYWORD_WEIGHT", "0.5"))
        # 병렬 검색 실행
        semantic_task = self._semantic_search(query, filter, language, top_k * 2)
        keyword_task = self._keyword_search(query, filter, language, top_k * 2)
        
        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )
        
        # RRF 병합
        merged_results = self._rrf_merge(
            semantic_results, 
            keyword_results, 
            top_k,
            semantic_weight,
            keyword_weight
        )
        
        return merged_results
    
    async def _semantic_search(
        self, 
        query: str, 
        filter: MVPSearchFilter,
        language: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        벡터 유사도 검색
        
        Args:
            query: 검색 쿼리
            filter: 검색 필터
            language: 언어
            limit: 최대 결과 수
            
        Returns:
            검색 결과 리스트
        """
        # 쿼리 임베딩 생성
        query_embedding = await self.embeddings.embed_query(query, language)
        
        # 임베딩을 pgvector 형식 문자열로 변환
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        # 언어별 임베딩 컬럼 선택
        if language == 'korean':
            embedding_column = 'embedding_korean'
        else:
            embedding_column = 'embedding_english'
        
        # SQL 쿼리 구성 (asyncpg용)
        where_clause, params = filter.to_sql_where_asyncpg()
        
        # 파라미터 인덱스 조정 (embedding_str이 $1, limit이 $2이므로 필터 파라미터는 $3부터)
        if params:
            # WHERE 절의 $1, $2... 를 $3, $4...로 변경
            for i in range(len(params), 0, -1):
                where_clause = where_clause.replace(f"${i}", f"${i+2}")
        
        sql = f"""
        SELECT 
            id, source, page, category, page_content,
            translation_text, contextualize_text, caption, entity,
            image_path, human_feedback,
            1 - ({embedding_column} <=> $1::vector) as similarity
        FROM mvp_ddu_documents
        WHERE {where_clause}
            AND {embedding_column} IS NOT NULL
        ORDER BY {embedding_column} <=> $1::vector
        LIMIT $2
        """
        
        # 디버깅을 위한 WHERE 절 로깅
        logger.info(f"[HYBRID] Semantic search WHERE clause: {where_clause}")
        logger.info(f"[HYBRID] Semantic filter params: {params}")
        
        async with self.pool.acquire() as conn:
            # 모든 파라미터를 위치 인자로 전달
            all_params = [embedding_str, limit] + params
            logger.info(f"[HYBRID] Executing semantic search with {len(all_params)} params")
            results = await conn.fetch(sql, *all_params)
            logger.info(f"[HYBRID] Semantic search returned {len(results)} results")
        
        return [dict(r) for r in results]
    
    async def _keyword_search(
        self, 
        query: str, 
        filter: MVPSearchFilter,
        language: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        키워드 전문 검색
        
        Args:
            query: 검색 쿼리
            filter: 검색 필터
            language: 언어
            limit: 최대 결과 수
            
        Returns:
            검색 결과 리스트
        """
        # asyncpg용 WHERE 절 생성
        where_clause, params = filter.to_sql_where_asyncpg()
        
        # 언어별 검색 쿼리 생성
        if language == 'korean':
            # Kiwi 토크나이저로 키워드 추출
            keywords = self._extract_korean_keywords(query)
            logger.info(f"[HYBRID] Korean keywords extracted ({len(keywords)}): {keywords}")
            if not keywords:
                logger.warning(f"[HYBRID] No Korean keywords extracted from: '{query}'")
                return []
            # 정교한 검색 전략: 키워드 수에 따라 AND/OR 조합
            if len(keywords) <= 2:
                # 2개 이하면 모두 AND (엄격한 매칭)
                search_query = ' & '.join(keywords)
                logger.info(f"[HYBRID] Korean search query (AND only): '{search_query}'")
            else:
                # 3개 이상이면 첫 2개는 AND, 나머지는 OR (유연한 매칭)
                primary = ' & '.join(keywords[:2])
                optional = ' | '.join(keywords[2:])
                search_query = f"({primary}) | {optional}"
                logger.info(f"[HYBRID] Korean search query (mixed AND/OR): '{search_query}'")
            search_column = 'search_vector_korean'
        else:
            # 영어는 정교한 키워드 추출 사용
            keywords = self._extract_english_keywords(query)
            logger.info(f"[HYBRID] English keywords extracted ({len(keywords)}): {keywords}")
            if not keywords:
                logger.warning(f"[HYBRID] No English keywords extracted from: '{query}'")
                return []
            # 정교한 검색 전략: 키워드 수에 따라 AND/OR 조합
            if len(keywords) <= 2:
                # 2개 이하면 모두 AND (엄격한 매칭)
                search_query = ' & '.join(keywords)
                logger.info(f"[HYBRID] English search query (AND only): '{search_query}'")
            else:
                # 3개 이상이면 첫 2개는 AND, 나머지는 OR (유연한 매칭)
                primary = ' & '.join(keywords[:2])
                optional = ' | '.join(keywords[2:])
                search_query = f"({primary}) | {optional}"
                logger.info(f"[HYBRID] English search query (mixed AND/OR): '{search_query}'")
            search_column = 'search_vector_english'
        
        # 파라미터 인덱스 조정 (search_query가 $1, limit이 $2이므로 필터 파라미터는 $3부터)
        if params:
            for i in range(len(params), 0, -1):
                where_clause = where_clause.replace(f"${i}", f"${i+2}")
        
        sql = f"""
        SELECT 
            id, source, page, category, page_content,
            translation_text, contextualize_text, caption, entity,
            image_path, human_feedback,
            ts_rank({search_column}, to_tsquery('simple', $1)) as rank
        FROM mvp_ddu_documents
        WHERE {where_clause}
            AND {search_column} @@ to_tsquery('simple', $1)
        ORDER BY rank DESC
        LIMIT $2
        """
        
        # 디버깅을 위한 WHERE 절 로깅
        logger.info(f"[HYBRID] WHERE clause: {where_clause}")
        logger.info(f"[HYBRID] Filter params: {params}")
        
        async with self.pool.acquire() as conn:
            # 모든 파라미터를 위치 인자로 전달
            all_params = [search_query, limit] + params
            logger.info(f"[HYBRID] Executing keyword search with {len(all_params)} params")
            results = await conn.fetch(sql, *all_params)
            logger.info(f"[HYBRID] Keyword search returned {len(results)} results")
        
        return [dict(r) for r in results]
    
    def _extract_korean_keywords(self, text: str) -> List[str]:
        """
        Kiwi를 사용한 한국어 키워드 추출
        
        Args:
            text: 입력 텍스트
            
        Returns:
            키워드 리스트
        """
        try:
            result = self.kiwi.tokenize(text)
            
            # 명사(NN), 동사(VV), 형용사(VA), 고유명사(NNP) 추출
            keywords = []
            
            # Kiwi는 Token 객체의 리스트를 반환
            for token in result:
                # Token 객체에서 형태소 정보 추출
                if hasattr(token, 'tag') and hasattr(token, 'form'):
                    # 명사 우선, 동사/형용사는 보조
                    if token.tag.startswith('NN'):
                        # 2글자 이상의 명사만 추출 (조사 제거)
                        if len(token.form) >= 2:
                            keywords.append((token.form, 1.0))  # 명사는 가중치 1.0
                    elif token.tag.startswith(('VV', 'VA')):
                        # 중요 동사/형용사만 (3글자 이상)
                        if len(token.form) >= 3:
                            keywords.append((token.form, 0.7))  # 동사/형용사는 가중치 0.7
            
            # 중복 제거하면서 순서 유지 (가중치 고려)
            seen = set()
            unique_keywords = []
            for keyword, weight in keywords:
                if keyword not in seen:
                    seen.add(keyword)
                    unique_keywords.append(keyword)
            
            # 동적 키워드 수 결정 (쿼리 길이에 따라)
            max_keywords = self._get_optimal_keyword_count(text)
            limited_keywords = unique_keywords[:max_keywords]
            logger.debug(f"[HYBRID] Korean keyword count: {max_keywords} (from {len(unique_keywords)} candidates)")
            
            # 키워드가 너무 적으면 원본 쿼리 사용
            if len(limited_keywords) < 2:
                # 공백으로 분리하고 불용어 제거
                stop_words = {'의', '를', '을', '에', '와', '과', '로', '으로', '에서', '부터', '까지', '및', '또는'}
                words = [w for w in text.split() if w not in stop_words and len(w) >= 2]
                limited_keywords = words[:max_keywords]
            
            return limited_keywords
            
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            # 오류 시 원본 텍스트의 공백 분리 사용
            return text.split()
    
    def _extract_english_keywords(self, text: str) -> List[str]:
        """
        영어 키워드 추출 (spaCy를 사용한 지능적 품사 분석)
        한국어 Kiwi와 동일한 수준의 정교함 제공
        
        Args:
            text: 입력 텍스트
            
        Returns:
            키워드 리스트 (최대 3개)
        """
        try:
            # spaCy 모델이 로드되지 않았으면 간단한 폴백 처리
            if not self.nlp:
                return self._extract_english_keywords_simple(text)
            
            # spaCy로 텍스트 처리
            doc = self.nlp(text)
            
            # 키워드 후보 수집 (가중치 포함)
            keywords = []
            
            # spaCy의 품사 태그 기반 추출
            for token in doc:
                # 불용어, 구두점, 공백 제외
                if token.is_stop or token.is_punct or token.is_space:
                    continue
                
                # 2글자 이상만 고려
                if len(token.text) < 2:
                    continue
                
                # 품사별 가중치 부여 (한국어와 동일한 전략)
                weight = 0.0
                if token.pos_ == "PROPN":  # 고유명사 최우선
                    weight = 1.5
                    keywords.append((token.text.lower(), weight))
                elif token.pos_ == "NOUN":  # 일반 명사
                    weight = 1.0
                    keywords.append((token.text.lower(), weight))
                elif token.pos_ in ["ADJ", "VERB"] and len(token.text) >= 3:  # 형용사, 동사는 3글자 이상
                    weight = 0.7
                    keywords.append((token.text.lower(), weight))
            
            # 복합 명사구 추출 (추가 보너스)
            for chunk in doc.noun_chunks:
                # 2-3 단어로 구성된 명사구만
                chunk_text = chunk.text.lower()
                chunk_words = chunk_text.split()
                if 2 <= len(chunk_words) <= 3:
                    # 단일 단어로 처리하지 말고 중요 단어만 추출
                    for token in chunk:
                        if token.pos_ in ["NOUN", "PROPN", "ADJ"] and not token.is_stop:
                            if len(token.text) >= 2:
                                keywords.append((token.text.lower(), 1.2))  # 명사구 내 단어는 보너스 가중치
            
            # 중복 제거하면서 가중치 최대값 유지
            keyword_dict = {}
            for keyword, weight in keywords:
                if keyword not in keyword_dict or keyword_dict[keyword] < weight:
                    keyword_dict[keyword] = weight
            
            # 가중치 기준으로 정렬
            sorted_keywords = sorted(keyword_dict.items(), key=lambda x: x[1], reverse=True)
            
            # 동적 키워드 수 결정 (쿼리 길이에 따라)
            max_keywords = self._get_optimal_keyword_count(text)
            limited_keywords = [keyword for keyword, weight in sorted_keywords[:max_keywords]]
            logger.debug(f"[HYBRID] English keyword count: {max_keywords} (from {len(sorted_keywords)} candidates)")
            
            # 키워드가 너무 적으면 대안 처리
            if len(limited_keywords) < 2:
                # spaCy가 제대로 추출 못했을 경우 폴백
                return self._extract_english_keywords_simple(text)
            
            logger.info(f"[HYBRID] spaCy extracted keywords: {limited_keywords} from '{text}'")
            return limited_keywords
            
        except Exception as e:
            logger.warning(f"[HYBRID] spaCy keyword extraction error: {e}. Falling back to simple extraction.")
            return self._extract_english_keywords_simple(text)
    
    def _extract_english_keywords_simple(self, text: str) -> List[str]:
        """
        간단한 영어 키워드 추출 (spaCy 없이 폴백)
        
        Args:
            text: 입력 텍스트
            
        Returns:
            키워드 리스트 (최대 3개)
        """
        # 영어 불용어 목록
        english_stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'this', 'these', 'they', 'we', 'you',
            'have', 'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how'
        }
        
        # 공백으로 분리하고 소문자 변환
        words = text.lower().split()
        
        # 키워드 후보 수집
        keyword_candidates = []
        
        for word in words:
            # 구두점 제거
            clean_word = ''.join(c for c in word if c.isalnum())
            
            if not clean_word or clean_word in english_stop_words:
                continue
            
            # 길이 기반 필터링 (2글자 이상)
            if len(clean_word) >= 2:
                # 대문자로 시작했던 단어는 고유명사일 가능성 (보너스)
                score = len(clean_word) * (1.5 if word[0].isupper() else 1.0)
                keyword_candidates.append((clean_word, score))
        
        # 점수별로 정렬
        keyword_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 동적 키워드 수 결정 (쿼리 길이에 따라)
        max_keywords = self._get_optimal_keyword_count(text)
        
        # 중복 제거하면서 동적 개수만큼 선택
        seen = set()
        limited_keywords = []
        for keyword, score in keyword_candidates:
            if keyword not in seen:
                seen.add(keyword)
                limited_keywords.append(keyword)
                if len(limited_keywords) >= max_keywords:
                    break
        
        logger.info(f"[HYBRID] Simple extraction keywords: {limited_keywords} from '{text}'")
        return limited_keywords
    
    def _rrf_merge(
        self,
        semantic_results: List[Dict],
        keyword_results: List[Dict],
        top_k: int,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion 병합
        
        Args:
            semantic_results: 시맨틱 검색 결과
            keyword_results: 키워드 검색 결과
            top_k: 최종 반환할 문서 수
            semantic_weight: 시맨틱 검색 가중치
            keyword_weight: 키워드 검색 가중치
            
        Returns:
            병합된 결과 리스트
        """
        scores = {}
        doc_map = {}
        
        # 시맨틱 검색 점수 계산
        for rank, doc in enumerate(semantic_results, 1):
            doc_id = doc['id']
            # RRF 점수에 가중치 적용
            scores[doc_id] = scores.get(doc_id, 0) + (semantic_weight / (self.k + rank))
            doc_map[doc_id] = doc
            # 검색 타입 추가
            if 'search_types' not in doc_map[doc_id]:
                doc_map[doc_id]['search_types'] = []
            doc_map[doc_id]['search_types'].append('semantic')
        
        # 키워드 검색 점수 계산
        for rank, doc in enumerate(keyword_results, 1):
            doc_id = doc['id']
            # RRF 점수에 가중치 적용
            scores[doc_id] = scores.get(doc_id, 0) + (keyword_weight / (self.k + rank))
            
            # 문서 정보 저장 (없으면)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
                doc_map[doc_id]['search_types'] = []
            doc_map[doc_id]['search_types'].append('keyword')
        
        # 점수별 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
        
        # 최종 결과 구성
        final_results = []
        for doc_id in sorted_ids:
            doc = doc_map[doc_id]
            doc['rrf_score'] = scores[doc_id]
            doc['search_types'] = list(set(doc['search_types']))  # 중복 제거
            final_results.append(doc)
        
        return final_results

  # 사용하지 않음  
    # async def search_with_feedback(
    #     self, 
    #     query: str, 
    #     filter: MVPSearchFilter,
    #     language: str = 'korean',
    #     top_k: int = 10,
    #     prefer_feedback: bool = True
    # ) -> List[Dict[str, Any]]:
    #     """
    #     휴먼 피드백을 고려한 검색
        
    #     Args:
    #         query: 검색 쿼리
    #         filter: 검색 필터
    #         language: 언어
    #         top_k: 반환할 최대 문서 수
    #         prefer_feedback: 피드백이 있는 문서 우선
            
    #     Returns:
    #         검색 결과 리스트
    #     """
    #     # 기본 하이브리드 검색
    #     results = await self.search(query, filter, language, top_k * 2)
        
    #     if prefer_feedback:
    #         # 피드백 있는 문서와 없는 문서 분리
    #         with_feedback = []
    #         without_feedback = []
            
    #         for doc in results:
    #             if doc.get('human_feedback') and doc['human_feedback'].strip():
    #                 with_feedback.append(doc)
    #             else:
    #                 without_feedback.append(doc)
            
    #         # 피드백 있는 문서 우선, 나머지 채우기
    #         final_results = with_feedback[:top_k]
    #         remaining = top_k - len(final_results)
    #         if remaining > 0:
    #             final_results.extend(without_feedback[:remaining])
            
    #         return final_results
        
    #     return results[:top_k]