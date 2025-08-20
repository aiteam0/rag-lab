"""
Retrieval Node
Phase 1의 하이브리드 검색 시스템과 연동하여 문서를 검색하는 노드
언어 감지, Dual Search Strategy, 이중 언어 검색 지원
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import time
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

from workflow.state import MVPWorkflowState, SearchResult
from ingest.database import DatabaseManager
from retrieval.hybrid_search import HybridSearch
from retrieval.search_filter import MVPSearchFilter

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class LanguageDetection(BaseModel):
    """언어 감지 결과"""
    language: str = Field(description="Detected language: 'korean' or 'english'")
    confidence: float = Field(description="Detection confidence (0.0-1.0)")
    reason: str = Field(description="Reason for detection")


class RetrievalNode:
    """검색 노드 - Phase 1 시스템과 연동, 언어 감지 및 Dual Search 지원"""
    
    def __init__(self):
        """초기화"""
        self.db_manager = None
        self.hybrid_search = None
        self.initialized = False
        
        # LLM for language detection
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 언어 감지 프롬프트
        self.language_detection_prompt = ChatPromptTemplate.from_messages([
            ("system", """Detect the primary language of the query.
            
Rules:
1. If the query contains Korean characters (한글), it's 'korean'
2. If the query is entirely in English, it's 'english'
3. If mixed, determine the dominant language
4. Consider technical terms that might be in English even in Korean queries

Examples:
- "안전벨트 착용 방법" → korean (confidence: 1.0)
- "How to wear seatbelt" → english (confidence: 1.0)
- "엔진 오일 교체 방법" → korean (confidence: 0.9, English term 'oil' doesn't change primary language)
- "brake system 점검" → korean (confidence: 0.7, mixed but Korean context)"""),
            ("human", "Query: {query}\n\nDetect the language:")
        ])
        
        # 환경변수에서 설정 읽기
        self.default_top_k = int(os.getenv("SEARCH_DEFAULT_TOP_K", "10"))
        self.max_results = int(os.getenv("SEARCH_MAX_RESULTS", "20"))
        
    async def _initialize(self):
        """비동기 초기화 (한 번만 실행)"""
        if not self.initialized:
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            self.hybrid_search = HybridSearch(self.db_manager.pool)
            self.initialized = True
    
    async def _detect_language(self, query: str) -> LanguageDetection:
        """
        쿼리 언어 감지
        
        Args:
            query: 검색 쿼리
            
        Returns:
            언어 감지 결과
        """
        structured_llm = self.llm.with_structured_output(LanguageDetection)
        
        result = await structured_llm.ainvoke(
            self.language_detection_prompt.format_messages(query=query)
        )
        
        return result
    
    async def _dual_search_strategy(
        self,
        query: str,
        filter_dict: Optional[Dict],
        language: str = 'korean',
        top_k: int = 10
    ) -> List[Document]:
        """
        이중 검색 전략 실행
        
        1. Entity 필터를 분리
        2. 일반 필터로 모든 카테고리 검색
        3. Entity 필터가 있으면 image/table만 추가 검색
        4. 결과 병합 (중복 제거)
        
        Args:
            query: 검색 쿼리
            filter_dict: 필터 딕셔너리
            language: 검색 언어
            top_k: 반환할 문서 수
            
        Returns:
            검색된 문서들
        """
        all_documents = []
        seen_ids = set()
        
        # Entity 필터 분리 (원본 dict 변조 방지)
        entity_filter = None
        general_filter_dict = {}
        
        if filter_dict:
            entity_filter = filter_dict.get("entity", None)  # pop() 대신 get() 사용 (원본 보존)
            # entity를 제외한 나머지 필터만 복사
            general_filter_dict = {k: v for k, v in filter_dict.items() if k != "entity"}
        
        # 1. 일반 필터로 검색 (Entity 없이)
        general_filter = MVPSearchFilter(**general_filter_dict) if general_filter_dict else MVPSearchFilter()
        
        general_results = await self.hybrid_search.search(
            query=query,
            filter=general_filter,
            language=language,
            top_k=top_k
        )
        
        # 결과를 Document로 변환하고 중복 체크
        for result in general_results:
            doc_id = result.get("id")
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                all_documents.append(self._convert_to_document(result))
        
        # 2. Entity 필터가 있으면 image/table 카테고리로 추가 검색
        if entity_filter:
            entity_filter_dict = general_filter_dict.copy()
            entity_filter_dict["entity"] = entity_filter
            entity_filter_dict["categories"] = ["image", "table"]  # image/table만
            
            entity_search_filter = MVPSearchFilter(**entity_filter_dict)
            
            entity_results = await self.hybrid_search.search(
                query=query,
                filter=entity_search_filter,
                language=language,
                top_k=top_k // 2  # 절반만 추가 검색
            )
            
            # Entity 검색 결과 추가 (중복 제거)
            for result in entity_results:
                doc_id = result.get("id")
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_documents.append(self._convert_to_document(result))
        
        return all_documents[:top_k]  # 최대 top_k개만 반환
    
    async def _bilingual_search(
        self,
        query: str,
        filter_dict: Optional[Dict],
        primary_language: str,
        top_k: int = 10
    ) -> List[Document]:
        """
        단일 언어 검색 (감지된 언어로만 검색)
        
        각 쿼리별로 언어를 정확히 감지했으므로, 
        해당 언어로만 검색하여 정확도를 높임
        
        Args:
            query: 검색 쿼리
            filter_dict: 필터 딕셔너리
            primary_language: 감지된 언어
            top_k: 반환할 문서 수
            
        Returns:
            검색 결과
        """
        # 감지된 언어로만 검색 (이중 언어 검색 제거)
        # 한국어 쿼리는 한국어로만, 영어 쿼리는 영어로만 검색
        results = await self._dual_search_strategy(
            query=query,
            filter_dict=filter_dict,
            language=primary_language,
            top_k=top_k
        )
        
        logger.debug(f"[RETRIEVAL] Single language search completed: {primary_language}, {len(results)} results")
        
        return results
    
    def _convert_to_document(self, result: Dict) -> Document:
        """
        검색 결과를 LangChain Document로 변환
        
        Args:
            result: 검색 결과 딕셔너리
            
        Returns:
            LangChain Document
        """
        # 메타데이터 구성
        metadata = {
            "source": result.get("source", ""),
            "page": result.get("page", 0),
            "category": result.get("category", ""),
            "id": result.get("id", ""),
            "caption": result.get("caption", ""),
            "entity": result.get("entity"),
            "similarity": result.get("similarity"),
            "rank": result.get("rank"),
            "rrf_score": result.get("rrf_score")
        }
        
        # 페이지 콘텐츠 결정 (우선순위: contextualize_text > page_content > translation_text)
        page_content = (
            result.get("contextualize_text") or 
            result.get("page_content") or 
            result.get("translation_text") or 
            ""
        )
        
        return Document(
            page_content=page_content,
            metadata=metadata
        )
    
    def _calculate_confidence(self, documents: List[Document]) -> float:
        """
        검색 결과의 신뢰도 계산
        
        Args:
            documents: 검색된 문서들
            
        Returns:
            신뢰도 점수 (0.0-1.0)
        """
        if not documents:
            return 0.0
        
        confidence = 0.0
        
        # 유사도 기반
        similarities = []
        for doc in documents[:5]:  # 상위 5개만 고려
            if doc.metadata.get("similarity"):
                similarities.append(doc.metadata["similarity"])
        
        if similarities:
            avg_similarity = sum(similarities) / len(similarities)
            confidence += avg_similarity

        return min(confidence, 1.0)
    
    async def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[RETRIEVAL] Node started")
        
        try:
            start_time = time.time()
            
            # 초기화
            logger.debug(f"[RETRIEVAL] Initializing database and search components...")
            await self._initialize()
            logger.debug(f"[RETRIEVAL] Initialization completed")
            
            # 현재 서브태스크 가져오기
            subtasks = state.get("subtasks", [])
            current_idx = state.get("current_subtask_idx", 0)
            logger.debug(f"[RETRIEVAL] Subtasks: {len(subtasks)}, current_idx: {current_idx}")
            
            # 쿼리 변형 확인 (필수)
            query_variations = state.get("query_variations")  # state.py의 필드명과 일치
            
            # None 체크 - 즉시 실패
            if query_variations is None:
                logger.error(f"[RETRIEVAL] CRITICAL: query_variations is None in state")
                logger.error(f"[RETRIEVAL] State keys: {list(state.keys())}")
                raise ValueError(
                    "CRITICAL ERROR: query_variations is None. "
                    "This should never happen - SubtaskExecutor must set query_variations."
                )
            
            # 빈 리스트 체크 - 즉시 실패
            if not query_variations:
                logger.error(f"[RETRIEVAL] CRITICAL: query_variations is empty list")
                logger.error(f"[RETRIEVAL] State keys: {list(state.keys())}")
                raise ValueError(
                    "CRITICAL ERROR: query_variations is empty. "
                    "SubtaskExecutor must generate at least one query variation."
                )
            
            logger.debug(f"[RETRIEVAL] Query variations in state: {len(query_variations)} items")
            
            # 메인 쿼리 결정
            if not subtasks or current_idx >= len(subtasks):
                # 서브태스크가 없으면 원본 쿼리
                query = state["query"]
                logger.debug(f"[RETRIEVAL] Using original query: '{query}'")
            else:
                # 현재 서브태스크의 쿼리 사용
                current_subtask = subtasks[current_idx]
                query = current_subtask["query"]
                subtask_id = current_subtask.get("id", "no-id")[:8]
                logger.info(f"[RETRIEVAL] Using subtask [{subtask_id}] query: '{query}'")
                
                # 서브태스크의 쿼리 변형이 있으면 우선 사용
                if current_subtask.get("query_variations"):
                    subtask_variations = current_subtask["query_variations"]
                    query_variations = subtask_variations
                    logger.debug(f"[RETRIEVAL] Using subtask query variations: {len(subtask_variations)} items")
            
            # 기본 언어 감지 (원본 쿼리 기준) - 폴백용
            logger.debug(f"[RETRIEVAL] Detecting language for query: '{query}'")
            language_detection = await self._detect_language(query)
            logger.info(f"[RETRIEVAL] Default language detected: {language_detection.language} (confidence: {language_detection.confidence:.2f})")
            
            # 검색 필터 생성 (state에서 가져오거나 기본값)
            filter_dict = state.get("search_filter")
            if filter_dict:
                logger.info(f"[RETRIEVAL] Search filter received:")
                for key, value in filter_dict.items():
                    if value is not None:
                        logger.info(f"  - {key}: {value}")
            else:
                logger.info(f"[RETRIEVAL] No search filter (will search all documents)")
            
            # Multi-Query 병렬 검색 실행 (동시 실행 제한 추가)
            logger.info(f"[RETRIEVAL] Preparing {len(query_variations)} parallel search tasks")
            
            # Semaphore로 동시 실행 수 제한 (connection pool 고갈 방지)
            max_concurrent = 1  # 동시에 최대 1개까지만 실행 (database operation conflict 방지)
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def limited_search(idx: int, query_variant: str):
                """Semaphore로 제한된 검색 - 각 쿼리별 개별 언어 감지"""
                async with semaphore:
                    logger.debug(f"[RETRIEVAL] Executing task {idx}: '{query_variant[:50]}...'")
                    
                    # 각 쿼리 변형별로 개별 언어 감지
                    variant_language_detection = await self._detect_language(query_variant)
                    logger.info(f"[RETRIEVAL] Task {idx} language: {variant_language_detection.language} (confidence: {variant_language_detection.confidence:.2f}) for query: '{query_variant[:50]}...'")
                    
                    # 감지된 언어로 검색 실행
                    return await self._bilingual_search(
                        query=query_variant,
                        filter_dict=filter_dict,
                        primary_language=variant_language_detection.language,  # 개별 감지된 언어 사용
                        top_k=self.default_top_k
                    )
            
            # 검색 태스크 파라미터 저장 (coroutine 생성은 실행 시점에)
            search_tasks = []
            for idx, query_variant in enumerate(query_variations):
                search_tasks.append((idx, query_variant))  # 파라미터만 저장
            
            # 모든 검색을 병렬로 실행 (semaphore로 제한됨)
            logger.info(f"[RETRIEVAL] Executing {len(search_tasks)} searches (max {max_concurrent} concurrent)...")
            
            # gather with return_exceptions=True - coroutine을 실행 시점에 생성
            results_or_errors = await asyncio.gather(
                *[limited_search(idx, query_variant) for idx, query_variant in search_tasks],
                return_exceptions=True
            )
            
            # Process results and handle errors
            results = []
            for idx, result_or_error in enumerate(results_or_errors):
                if isinstance(result_or_error, Exception):
                    logger.error(f"[RETRIEVAL] Task {idx} failed: {str(result_or_error)}")
                    results.append([])  # 실패한 변형은 빈 리스트
                else:
                    logger.debug(f"[RETRIEVAL] Task {idx} succeeded with {len(result_or_error)} documents")
                    results.append(result_or_error)
            
            # Log overall status
            successful_tasks = sum(1 for r in results_or_errors if not isinstance(r, Exception))
            if successful_tasks == len(search_tasks):
                logger.info(f"[RETRIEVAL] All {len(search_tasks)} searches completed successfully")
            else:
                logger.warning(f"[RETRIEVAL] {successful_tasks}/{len(search_tasks)} searches succeeded")
            
            # 필터가 있을 때 모든 결과가 비어있으면 필터 없이 재시도
            total_docs_with_filter = sum(len(r) for r in results if r)
            if filter_dict and total_docs_with_filter == 0:
                logger.warning(f"[RETRIEVAL] All searches with filter returned 0 documents. Retrying without filter...")
                logger.info(f"[RETRIEVAL] Original filter was: {filter_dict}")
                
                # 필터 없이 재실행 (filter_dict를 None으로 변경)
                original_filter = filter_dict
                filter_dict = None  # 필터 제거
                
                # Semaphore 재사용하여 제한된 검색 재실행
                async def retry_limited_search(idx: int, query_variant: str):
                    """필터 없이 재시도하는 검색"""
                    async with semaphore:
                        logger.debug(f"[RETRIEVAL] Retrying task {idx} without filter: '{query_variant[:50]}...'")
                        return await self._bilingual_search(
                            query=query_variant,
                            filter_dict=None,  # 필터 없이
                            primary_language=language_detection.language,
                            top_k=self.default_top_k
                        )
                
                logger.info(f"[RETRIEVAL] Retrying {len(search_tasks)} searches without filter...")
                
                # 재시도 실행 - coroutine을 실행 시점에 생성
                retry_results_or_errors = await asyncio.gather(
                    *[retry_limited_search(idx, query_variant) for idx, query_variant in search_tasks],
                    return_exceptions=True
                )
                
                # 재시도 결과 처리
                retry_results = []
                for idx, result_or_error in enumerate(retry_results_or_errors):
                    if isinstance(result_or_error, Exception):
                        logger.error(f"[RETRIEVAL] Retry task {idx} failed: {str(result_or_error)}")
                        retry_results.append([])
                    else:
                        logger.debug(f"[RETRIEVAL] Retry task {idx} succeeded with {len(result_or_error)} documents")
                        retry_results.append(result_or_error)
                
                # 재시도 성공 여부 로깅
                retry_total_docs = sum(len(r) for r in retry_results if r)
                if retry_total_docs > 0:
                    logger.info(f"[RETRIEVAL] Retry without filter succeeded: {retry_total_docs} documents found")
                    results = retry_results  # 재시도 결과 사용
                    # 메타데이터에 재시도 정보 추가
                    if 'metadata' not in state:
                        state['metadata'] = {}
                    state['metadata']['retrieval_retry'] = {
                        'retried': True,
                        'original_filter': original_filter,
                        'retry_reason': 'filter_returned_zero_documents',
                        'retry_documents': retry_total_docs
                    }
                else:
                    logger.warning(f"[RETRIEVAL] Retry without filter also returned 0 documents")
            
            # 결과 처리 및 중복 제거
            logger.debug(f"[RETRIEVAL] Processing search results and removing duplicates...")
            all_documents = []
            seen_ids = set()
            
            for (idx, query_variant), variant_docs in zip(search_tasks, results):
                result_count = len(variant_docs)
                logger.debug(f"[RETRIEVAL] Query variant {idx} returned {result_count} documents")
                
                for doc in variant_docs:
                    # Document ID 생성 (metadata의 id 또는 content hash)
                    doc_id = doc.metadata.get("id")
                    if not doc_id:
                        # ID가 없으면 content의 처음 100자를 기준으로
                        doc_id = hash(doc.page_content[:100])
                    
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        # 메타데이터에 검색 변형 정보 추가
                        doc.metadata["search_variant_idx"] = idx
                        doc.metadata["search_variant_query"] = query_variant
                        all_documents.append(doc)
            
            # 최종 문서 리스트
            documents = all_documents
            
            # documents가 None이면 즉시 실패
            if documents is None:
                raise ValueError(
                    "CRITICAL ERROR: documents is None after search. "
                    "This should never happen - search must return empty list at minimum."
                )
            
            unique_count = len(seen_ids)
            total_retrieved = sum(len(result) for result in results)
            logger.info(f"[RETRIEVAL] Results: {total_retrieved} total → {unique_count} unique → {len(documents)} final documents")
            
            # 검색 결과 문서 상세 정보 로깅 (상위 3개만)
            for i, doc in enumerate(documents[:3]):
                source = doc.metadata.get('source', 'unknown')[:20]
                page = doc.metadata.get('page', 'N/A')
                category = doc.metadata.get('category', 'unknown')[:12]
                content_preview = doc.page_content[:45].replace('\n', ' ').strip()
                logger.info(f"[RETRIEVAL] Doc {i+1}: {source}:P.{page}:{category} - \"{content_preview}...\"")
            
            # CRITICAL: 최소한 하나의 결과라도 있어야 함 (에러 발생)
            if not documents and query_variations:
                logger.error(f"[RETRIEVAL] CRITICAL: No documents found for any of {len(query_variations)} query variations")
                raise ValueError(
                    f"CRITICAL ERROR: No documents retrieved from {len(query_variations)} query variations. "
                    f"Retrieval must return at least one document. "
                    f"This indicates a serious issue with the search system or data."
                )
            
            execution_time = time.time() - start_time
            logger.info(f"[RETRIEVAL] Search execution completed in {execution_time:.3f}s")
            
            # 실행 시간 기록
            execution_times = state.get("execution_time", {})
            execution_times["retrieval"] = execution_time
            
            # 메타데이터 업데이트
            metadata = state.get("metadata", {})
            metadata["retrieval"] = {
                "query": query,
                "query_variations_count": len(query_variations),
                "query_variations_used": query_variations,
                "detected_language": language_detection.language,
                "language_confidence": language_detection.confidence,
                "total_documents": len(documents),
                "unique_documents": len(seen_ids),
                "search_strategy": "multi_query_bilingual",
                "confidence": self._calculate_confidence(documents)
            }
            
            # 현재 서브태스크 업데이트 (있는 경우)
            if subtasks and current_idx < len(subtasks):
                subtasks[current_idx]["documents"] = documents
                subtasks[current_idx]["status"] = "retrieved"
                subtask_id = subtasks[current_idx].get("id", "no-id")[:8]
                logger.info(f"[RETRIEVAL] Updated subtask [{subtask_id}] status: 'executing' -> 'retrieved' ({len(documents)} docs)")
            
            confidence_score = self._calculate_confidence(documents)
            logger.info(f"[RETRIEVAL] Confidence score: {confidence_score:.3f}")
            
            result = {
                "documents": documents,  # 누적 추가됨
                "subtasks": subtasks,
                "search_language": language_detection.language,
                "confidence_score": confidence_score,
                "execution_time": execution_times,
                "metadata": metadata
            }
            logger.info(f"[RETRIEVAL] Node completed successfully - retrieved {len(documents)} documents")
            return result
            
        except Exception as e:
            logger.error(f"[RETRIEVAL] Node failed: {str(e)}")
            return {
                "error": f"Retrieval failed: {str(e)}",
                "workflow_status": "failed",
                "warnings": [f"Search error: {str(e)}"]
            }
    
    def invoke(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        logger.debug(f"[RETRIEVAL] Invoke called (sync wrapper)")
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            # 이미 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
            logger.debug(f"[RETRIEVAL] Event loop detected, creating task in current loop")
            # 현재 event loop에서 task 실행 (새 event loop 생성하지 않음)
            task = loop.create_task(self.__call__(state))
            # Task를 동기적으로 대기 (nest_asyncio 필요)
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(task)
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성하여 실행
            logger.debug(f"[RETRIEVAL] No event loop, creating new one")
            return asyncio.run(self.__call__(state))
    
    async def cleanup(self):
        """리소스 정리"""
        if self.db_manager:
            await self.db_manager.close()
            self.initialized = False