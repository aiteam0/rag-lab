"""
Retrieval Node
Phase 1의 하이브리드 검색 시스템과 연동하여 문서를 검색하는 노드
언어 감지, Dual Search Strategy, 이중 언어 검색 지원
"""

import os
import logging
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import time


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


class RerankResult(BaseModel):
    """문서 재순위화 결과"""
    ranked_doc_ids: List[str] = Field(
        description="문서 ID 리스트 (관련성 높은 순서)"
    )
    reasoning: str = Field(
        description="순위 결정 이유"
    )


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
        
    
    def _initialize(self):
        """동기 초기화 (한 번만 실행)"""
        if not self.initialized:
            self.db_manager = DatabaseManager()
            self.db_manager.initialize()
            self.hybrid_search = HybridSearch(self.db_manager.pool)
            self.initialized = True
    
    def _detect_language(self, query: str) -> LanguageDetection:
        """
        쿼리 언어 감지
        
        Args:
            query: 검색 쿼리
            
        Returns:
            언어 감지 결과
        """
        structured_llm = self.llm.with_structured_output(
            LanguageDetection
        )
        
        result = structured_llm.invoke(
            self.language_detection_prompt.format_messages(query=query)
        )
        
        return result
    
    def _dual_search_strategy(
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
        
        # Entity 필터가 있으면 entity 검색을 우선적으로 수행
        if entity_filter:
            # 1. Entity 필터로 먼저 검색 (우선순위 높음)
            entity_filter_dict = general_filter_dict.copy()
            entity_filter_dict["entity"] = entity_filter
            # Entity가 있을 수 있는 모든 카테고리 포함 (image/table + 똑딱이가 있는 text 카테고리)
            entity_filter_dict["categories"] = ["figure", "table", "paragraph", "heading1", "heading2", "heading3"]
            
            entity_search_filter = MVPSearchFilter(**entity_filter_dict)
            
            entity_results = self.hybrid_search.search(
                query=query,
                filter=entity_search_filter,
                language=language,
                top_k=top_k  # 전체 top_k 사용 (우선순위)
            )
            
            # Entity 검색 결과를 먼저 추가
            for result in entity_results:
                doc_id = result.get("id")
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_documents.append(self._convert_to_document(result))
            
            # 2. 일반 필터로 보충 검색 (Entity 없이) - 부족한 경우에만
            if len(all_documents) < top_k:
                general_filter = MVPSearchFilter(**general_filter_dict) if general_filter_dict else MVPSearchFilter()
                
                general_results = self.hybrid_search.search(
                    query=query,
                    filter=general_filter,
                    language=language,
                    top_k=top_k - len(all_documents)  # 부족한 만큼만
                )
                
                # 일반 검색 결과 추가 (중복 제거)
                for result in general_results:
                    doc_id = result.get("id")
                    if doc_id and doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        all_documents.append(self._convert_to_document(result))
        else:
            # Entity 필터가 없으면 일반 검색만 수행
            general_filter = MVPSearchFilter(**general_filter_dict) if general_filter_dict else MVPSearchFilter()
            
            general_results = self.hybrid_search.search(
                query=query,
                filter=general_filter,
                language=language,
                top_k=top_k
            )
            
            # 결과를 Document로 변환
            for result in general_results:
                doc_id = result.get("id")
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_documents.append(self._convert_to_document(result))
        
        return all_documents[:top_k]  # 최대 top_k개만 반환
    
    def _bilingual_search(
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
        results = self._dual_search_strategy(
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
        # source와 page 정보 추출
        source = result.get("source", "")
        page = result.get("page", 0)
        
        # page_image_path 생성 로직
        page_image_path = ""
        if source and page > 0:  # page가 1 이상일 때만
            # 파일명 추출 (경로와 확장자 제거)
            # 예: "data/gv80_owners_manual_TEST6P.pdf" → "gv80_owners_manual_TEST6P"
            filename = os.path.splitext(os.path.basename(source))[0]
            page_image_path = f"data/images/{filename}-page-{page}.png"
        
        # 메타데이터 구성
        metadata = {
            "source": source,
            "page": page,
            "category": result.get("category", ""),
            "id": result.get("id", ""),
            "caption": result.get("caption", ""),
            "entity": result.get("entity"),
            "page_image_path": page_image_path,  # 페이지 이미지 경로 추가
            "similarity": result.get("similarity"),
            "rank": result.get("rank"),
            "rrf_score": result.get("rrf_score"),
            "human_feedback": result.get("human_feedback", ""),  # Human feedback 추가
            # 통합 score 필드 - None이 아닌 값 우선 (우선순위: rrf > similarity > rank)
            # RRF는 이미 정규화됨 (0.0-1.0)
            "score": (
                result.get("rrf_score") or 
                result.get("similarity") or 
                result.get("rank") or 
                0.0
            )
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
        
        # 통합 score 기반 신뢰도 계산
        scores = []
        for doc in documents[:5]:  # 상위 5개만 고려
            score = doc.metadata.get("score", 0.0)
            if score and score > 0:
                scores.append(score)
        
        if scores:
            avg_score = sum(scores) / len(scores)
            confidence += avg_score

        return min(confidence, 1.0)
    
    def _rerank_documents(self, query: str, documents: List[Document], top_k: int = 20) -> List[Document]:
        """
        LLM을 사용한 문서 재순위화 - 모든 문서 평가
        
        Args:
            query: 사용자 쿼리
            documents: 검색된 문서들
            top_k: 반환할 상위 문서 수
        
        Returns:
            재순위화된 상위 문서들
        """
        if len(documents) <= top_k:
            return documents
        
        # 동적 preview 길이 계산 (토큰 제한 고려)
        # 전체 토큰을 약 50000자로 제한
        preview_length = min(2000, max(1000, 50000 // len(documents)))
        logger.info(f"[RERANK] Evaluating {len(documents)} docs with {preview_length} chars preview each")
        
        # 모든 문서 요약 생성
        doc_summaries = []
        for i, doc in enumerate(documents):
            summary = {
                "id": doc.metadata.get("id", f"doc_{i}"),
                "page": doc.metadata.get("page", 0),
                "category": doc.metadata.get("category", ""),
                "content_preview": doc.page_content[:preview_length],  # 동적 길이
                "score": doc.metadata.get("score", 0)
            }
            doc_summaries.append(summary)
        
        # Reranking 프롬프트
        rerank_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a document relevance expert for automotive manuals.
Your task is to rerank ALL provided documents based on their relevance to the user query.

CRITICAL RULES:
1. Evaluate ALL documents, not just a subset
2. Prioritize documents with SPECIFIC information matching the query
3. Deprioritize generic or vague content
4. Consider document category (table, figure, heading1 are often important)
5. Consider original retrieval score as a hint but not absolute
6. Return ONLY the document IDs WITHOUT brackets or prefixes

IMPORTANT: Return IDs exactly as shown between the brackets in [ID: xxx]
For example, if you see [ID: doc_0], return "doc_0"
If you see [ID: gv80_owners_manual_0001], return "gv80_owners_manual_0001"
DO NOT include "[ID: " or "]" in your response."""),
            
            ("human", """Query: {query}

Total documents to evaluate: {doc_count}

Documents:
{documents}

Return the top {top_k} most relevant document IDs in order.
Return ONLY the IDs, without any brackets or prefixes.
Focus on documents that directly answer the query.""")
        ])
        
        # LLM으로 재순위화
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0
        )
        
        structured_llm = llm.with_structured_output(RerankResult)
        
        # 문서 텍스트 포맷팅
        doc_text = "\n".join([
            f"[ID: {d['id']}] Page {d['page']}, {d['category']}, Score: {d['score']:.2f}\nContent: {d['content_preview']}..."
            for d in doc_summaries
        ])
        
        result = structured_llm.invoke(
            rerank_prompt.format_messages(
                query=query,
                doc_count=len(documents),
                documents=doc_text,
                top_k=top_k
            )
        )
        
        # 디버깅: LLM이 반환한 ID들 로깅
        logger.info(f"[RERANK] LLM returned {len(result.ranked_doc_ids)} IDs: {result.ranked_doc_ids[:5]}...")
        
        # 재순위화된 문서 반환
        doc_map = {doc.metadata.get("id", f"doc_{i}"): doc for i, doc in enumerate(documents)}
        
        # 디버깅: 실제 문서 ID들 로깅
        actual_ids = list(doc_map.keys())[:5]
        logger.info(f"[RERANK] Actual document IDs: {actual_ids}...")
        
        reranked_docs = []
        missing_ids = []
        
        for doc_id in result.ranked_doc_ids[:top_k]:
            if doc_id in doc_map:
                reranked_docs.append(doc_map[doc_id])
            else:
                # ID 매칭 실패 - 다양한 형식 시도
                # 1. 대괄호 제거
                cleaned_id = doc_id.strip("[]")
                if cleaned_id in doc_map:
                    reranked_docs.append(doc_map[cleaned_id])
                    continue
                
                # 2. "ID: " 프리픽스 제거
                if doc_id.startswith("ID: "):
                    cleaned_id = doc_id[4:]
                    if cleaned_id in doc_map:
                        reranked_docs.append(doc_map[cleaned_id])
                        continue
                
                # 3. "[ID: " 프리픽스와 "]" 제거
                if doc_id.startswith("[ID: ") and doc_id.endswith("]"):
                    cleaned_id = doc_id[5:-1]
                    if cleaned_id in doc_map:
                        reranked_docs.append(doc_map[cleaned_id])
                        continue
                
                # 4. 타입 변환 시도 - 문자열을 정수로
                if isinstance(doc_id, str) and doc_id.isdigit():
                    int_id = int(doc_id)
                    if int_id in doc_map:
                        reranked_docs.append(doc_map[int_id])
                        continue
                
                # 5. 타입 변환 시도 - 정수를 문자열로
                if isinstance(doc_id, int):
                    str_id = str(doc_id)
                    if str_id in doc_map:
                        reranked_docs.append(doc_map[str_id])
                        continue
                
                # 6. cleaned_id에 대해서도 타입 변환 시도
                if 'cleaned_id' in locals():
                    # cleaned_id가 숫자 문자열인 경우 정수로 변환
                    if isinstance(cleaned_id, str) and cleaned_id.isdigit():
                        int_cleaned_id = int(cleaned_id)
                        if int_cleaned_id in doc_map:
                            reranked_docs.append(doc_map[int_cleaned_id])
                            continue
                    # cleaned_id가 정수인 경우 문자열로 변환
                    elif isinstance(cleaned_id, int):
                        str_cleaned_id = str(cleaned_id)
                        if str_cleaned_id in doc_map:
                            reranked_docs.append(doc_map[str_cleaned_id])
                            continue
                
                missing_ids.append(doc_id)
        
        if missing_ids:
            logger.warning(f"[RERANK] Could not match {len(missing_ids)} IDs: {missing_ids[:3]}...")
        
        logger.info(f"[RERANK] {len(documents)} → {len(reranked_docs)} documents (reasoning: {result.reasoning[:100]}...)")
        return reranked_docs
    
    def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[RETRIEVAL] Node started")
        
        # Multi-turn 문서 초기화 검증 로직 (첫 번째 subtask에서만)
        current_subtask_idx = state.get("current_subtask_idx", 0)
        existing_docs = state.get("documents", [])
        logger.info(f"[RETRIEVAL] Subtask index: {current_subtask_idx}, Existing documents: {len(existing_docs)}")
        
        if current_subtask_idx == 0:  # 첫 번째 subtask 처리 시
            if len(existing_docs) > 0:
                logger.warning(f"[RETRIEVAL] Documents not cleared properly: {len(existing_docs)} existing documents found")
                logger.warning(f"[RETRIEVAL] This may cause multi-turn document accumulation issues")
                # Log first few document IDs for debugging
                doc_ids = [doc.metadata.get('id', 'unknown') for doc in existing_docs[:5]]
                logger.warning(f"[RETRIEVAL] First few document IDs: {doc_ids}")
            else:
                logger.info(f"[RETRIEVAL] Document state properly cleared for new RAG query")
        
        try:
            start_time = time.time()
            
            # 초기화
            logger.debug(f"[RETRIEVAL] Initializing database and search components...")
            self._initialize()
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
            language_detection = self._detect_language(query)
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
            
            # Multi-Query 병렬 검색 실행 (병렬성 향상)
            logger.info(f"[RETRIEVAL] Preparing {len(query_variations)} parallel search tasks")
            
            # ThreadPoolExecutor로 병렬 실행 (DB pool size의 30%)
            max_workers = 3  # DB pool이 10개이므로 3개 정도가 적절
            
            def search_task(idx: int, query_variant: str):
                """병렬 검색 태스크 - 각 쿼리별 개별 언어 감지"""
                try:
                    logger.debug(f"[RETRIEVAL] Executing task {idx}: '{query_variant[:50]}...'")
                    
                    # 각 쿼리 변형별로 개별 언어 감지
                    variant_language_detection = self._detect_language(query_variant)
                    logger.info(f"[RETRIEVAL] Task {idx} language: {variant_language_detection.language} (confidence: {variant_language_detection.confidence:.2f}) for query: '{query_variant[:50]}...'")
                    
                    # 감지된 언어로 검색 실행
                    result = self._bilingual_search(
                        query=query_variant,
                        filter_dict=filter_dict,
                        primary_language=variant_language_detection.language,  # 개별 감지된 언어 사용
                        top_k=self.default_top_k
                    )
                    
                    # 검색 통계 수집
                    stats = None
                    if hasattr(self.hybrid_search, 'last_search_stats'):
                        stats = self.hybrid_search.last_search_stats.copy()
                        # 언어 정보 추가 (집계에 필요)
                        if stats:
                            stats['detected_language'] = variant_language_detection.language
                    
                    return (result, stats)  # 튜플로 반환
                    
                except Exception as e:
                    # 예외를 로깅하고 다시 발생시킴 (executor에서 처리하도록)
                    error_type = type(e).__name__
                    logger.error(f"[RETRIEVAL] Task {idx} encountered error: {error_type}: {str(e)}")
                    raise  # 예외를 다시 발생시켜 executor에서 처리
            
            # 검색 태스크 파라미터 저장
            search_tasks = []
            for idx, query_variant in enumerate(query_variations):
                search_tasks.append((idx, query_variant))  # 파라미터만 저장
            
            # 모든 검색을 병렬로 실행 (향상된 병렬성)
            logger.info(f"[RETRIEVAL] Executing {len(search_tasks)} searches (max {max_workers} workers)...")
            
            # ThreadPoolExecutor로 병렬 실행
            results_or_errors = []
            all_search_stats = []  # 모든 검색 통계 수집
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(search_task, idx, query_variant) 
                          for idx, query_variant in search_tasks]
                
                for future in futures:
                    try:
                        result_tuple = future.result()
                        results_or_errors.append(result_tuple)
                    except Exception as e:
                        results_or_errors.append(e)
            
            # Process results and handle errors with better exception handling
            results = []
            connection_errors = []
            
            for idx, result_or_error in enumerate(results_or_errors):
                if isinstance(result_or_error, Exception):
                    error_type = type(result_or_error).__name__
                    error_msg = str(result_or_error)
                    
                    # Connection 관련 에러 특별 처리
                    if "ConnectionDoesNotExistError" in error_type or "connection" in error_msg.lower():
                        connection_errors.append(idx)
                        logger.error(f"[RETRIEVAL] Task {idx} failed with CONNECTION ERROR: {error_msg}")
                    else:
                        logger.error(f"[RETRIEVAL] Task {idx} failed with {error_type}: {error_msg}")
                    
                    results.append([])  # 실패한 변형은 빈 리스트
                else:
                    # 튜플 분해: (result, stats)
                    if isinstance(result_or_error, tuple) and len(result_or_error) == 2:
                        result, stats = result_or_error
                        logger.debug(f"[RETRIEVAL] Task {idx} succeeded with {len(result)} documents")
                        results.append(result)
                        if stats:
                            all_search_stats.append(stats)
                    else:
                        # 이전 버전 호환성 (튜플이 아닌 경우)
                        logger.debug(f"[RETRIEVAL] Task {idx} succeeded with {len(result_or_error)} documents")
                        results.append(result_or_error)
            
            # Connection 에러가 있으면 경고
            if connection_errors:
                logger.warning(f"[RETRIEVAL] Connection errors detected in tasks: {connection_errors}. Pool may be corrupted.")
            
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
                
                # 필터 없이 재시도하는 검색 함수
                def retry_search_task(idx: int, query_variant: str):
                    """필터 없이 재시도하는 검색"""
                    logger.debug(f"[RETRIEVAL] Retrying task {idx} without filter: '{query_variant[:50]}...'")
                    result = self._bilingual_search(
                        query=query_variant,
                        filter_dict=None,  # 필터 없이
                        primary_language=language_detection.language,
                        top_k=self.default_top_k
                    )
                    
                    # HybridSearch의 last_search_stats 가져오기 (있는 경우)
                    stats = None
                    if hasattr(self.hybrid_search, 'last_search_stats'):
                        stats = self.hybrid_search.last_search_stats.copy() if self.hybrid_search.last_search_stats else None
                        # 언어 정보 추가 (집계에 필요)
                        if stats:
                            # 언어 감지
                            variant_language_detection = detect_language(query_variant)
                            stats['detected_language'] = variant_language_detection.language
                    
                    return (result, stats)  # 튜플로 반환
                
                logger.info(f"[RETRIEVAL] Retrying {len(search_tasks)} searches without filter...")
                
                # 재시도 실행 (동일한 병렬성 유지)
                retry_results_or_errors = []
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    retry_futures = [executor.submit(retry_search_task, idx, query_variant) 
                                   for idx, query_variant in search_tasks]
                    
                    for future in retry_futures:
                        try:
                            result = future.result()
                            retry_results_or_errors.append(result)
                        except Exception as e:
                            retry_results_or_errors.append(e)
                
                # 재시도 결과 처리
                retry_results = []
                retry_stats = []
                for idx, result_or_error in enumerate(retry_results_or_errors):
                    if isinstance(result_or_error, Exception):
                        logger.error(f"[RETRIEVAL] Retry task {idx} failed: {str(result_or_error)}")
                        retry_results.append([])
                    else:
                        # 튜플 처리: (result, stats)
                        if isinstance(result_or_error, tuple) and len(result_or_error) == 2:
                            result, stats = result_or_error
                            logger.debug(f"[RETRIEVAL] Retry task {idx} succeeded with {len(result)} documents")
                            retry_results.append(result)
                            if stats:
                                retry_stats.append(stats)
                        else:
                            # 이전 버전 호환성 (튜플이 아닌 경우)
                            logger.debug(f"[RETRIEVAL] Retry task {idx} succeeded with {len(result_or_error)} documents")
                            retry_results.append(result_or_error)
                
                # 재시도 성공 여부 로깅
                retry_total_docs = sum(len(r) for r in retry_results if r)
                if retry_total_docs > 0:
                    logger.info(f"[RETRIEVAL] Retry without filter succeeded: {retry_total_docs} documents found")
                    results = retry_results  # 재시도 결과 사용
                    # 재시도 통계로 교체
                    if retry_stats:
                        all_search_stats = retry_stats
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
            
            # Reranking 적용 (문서가 10개 초과시)
            if len(documents) > 10:
                logger.info(f"[RETRIEVAL] Applying LLM reranking to {len(documents)} documents...")
                documents = self._rerank_documents(
                    query=state["query"],
                    documents=documents,
                    top_k=int(os.getenv("RERANK_TOP_K", "10"))
                )
                # Reranking 후 메타데이터 업데이트
                metadata["retrieval"]["documents_after_rerank"] = len(documents)
                metadata["retrieval"]["reranking_applied"] = True
                
                # 현재 서브태스크 문서도 업데이트
                if subtasks and current_idx < len(subtasks):
                    subtasks[current_idx]["documents"] = documents
            else:
                metadata["retrieval"]["reranking_applied"] = False
            
            # 언어별 키워드 집계
            korean_keywords = set()
            english_keywords = set()
            total_keyword_docs = 0
            total_semantic_docs = 0
            
            for stats in all_search_stats:
                if stats:
                    # 언어별 키워드 수집
                    detected_lang = stats.get('detected_language', stats.get('language', ''))
                    keywords = stats.get('extracted_keywords', [])
                    
                    if detected_lang == 'korean':
                        korean_keywords.update(keywords)
                    elif detected_lang == 'english':
                        english_keywords.update(keywords)
                    
                    # 검색 결과 수 집계
                    total_keyword_docs += stats.get('keyword_count', 0)
                    total_semantic_docs += stats.get('semantic_count', 0)
            
            # 통계 로깅
            if korean_keywords or english_keywords:
                logger.info(f"[RETRIEVAL] Aggregated keywords - Korean: {list(korean_keywords)[:5]}, English: {list(english_keywords)[:5]}")
                logger.info(f"[RETRIEVAL] Total search results - Keyword: {total_keyword_docs}, Semantic: {total_semantic_docs}")
            
            # 메시지 생성 - 검색 과정 상세 정보
            messages = []
            
            # 1. 서브태스크 정보 (간소화)
            if subtasks and current_idx < len(subtasks):
                current_subtask = subtasks[current_idx]
                subtask_desc = current_subtask.get("description", current_subtask.get("query", ""))
                messages.append(
                    AIMessage(content=f"🔎 [{current_idx+1}/{len(subtasks)}] {subtask_desc[:80]}... 검색 중")
                )
            else:
                messages.append(
                    AIMessage(content=f"🔎 검색 중: {query[:80]}...")
                )
            
            # 언어별 키워드 표시 (집계된 통계 사용)
            if korean_keywords:
                korean_kw_list = list(korean_keywords)[:4]
                korean_display = ', '.join(korean_kw_list)
                if len(korean_keywords) > 4:
                    korean_display += f" 외 {len(korean_keywords)-4}개"
                messages.append(
                    AIMessage(content=f"🔑 한국어: {korean_display}")
                )
            
            if english_keywords:
                english_kw_list = list(english_keywords)[:4]
                english_display = ', '.join(english_kw_list)
                if len(english_keywords) > 4:
                    english_display += f" 외 {len(english_keywords)-4}개"
                messages.append(
                    AIMessage(content=f"🔑 영어: {english_display}")
                )
            
            # 검색 결과 통계 표시
            if len(all_search_stats) > 0:
                if total_keyword_docs > 0:
                    messages.append(
                        AIMessage(content=f"🔍 {len(all_search_stats)}개 변형 검색 (키워드 {total_keyword_docs}개 + 의미 {total_semantic_docs}개 문서)")
                    )
                elif total_semantic_docs > 0:
                    messages.append(
                        AIMessage(content=f"🔍 {len(all_search_stats)}개 변형 검색 (키워드 매칭 없음, 의미 검색 {total_semantic_docs}개)")
                    )
            
            # 언어 감지, 쿼리 변형, 검색 전략 메시지 제거
            # 필터 정보는 중요한 경우만 표시
            if filter_dict:
                # 중요한 필터만 표시 (예: 특정 페이지, 카테고리)
                important_filters = []
                if filter_dict.get("page"):
                    important_filters.append(f"페이지 {filter_dict['page']}")
                if filter_dict.get("category"):
                    important_filters.append(f"카테고리 {filter_dict['category']}")
                if important_filters:
                    messages.append(
                        AIMessage(content=f"🔍 필터: {', '.join(important_filters)}")
                    )
            
            # 2. 검색 결과 표시
            if documents:
                unique_count = metadata.get("unique_documents", len(documents))
                # 통합 score 필드 사용 - None 안전 처리
                scores = [doc.metadata.get("score", 0.0) for doc in documents]
                valid_scores = [s for s in scores if s and s > 0]  # None과 0 체크
                
                if valid_scores:
                    avg_score = sum(valid_scores) / len(valid_scores)
                    messages.append(
                        AIMessage(content=f"📄 {unique_count}개 고유 문서 발견 (유사도 평균 {avg_score:.1%})")
                    )
                else:
                    messages.append(
                        AIMessage(content=f"📄 {unique_count}개 고유 문서 발견")
                    )
            else:
                messages.append(
                    AIMessage(content="⚠️ 검색 결과가 없습니다. 웹 검색을 시도합니다...")
                )
            
            result = {
                "messages": messages,  # 메시지 추가
                "documents": documents,  # 문서 반환 (state의 add reducer에 의해 누적됨, planning에서 초기화)
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
        logger.debug(f"[RETRIEVAL] Invoke called (sync)")
        
        # 동기 방식으로 직접 호출
        return self.__call__(state)
    
    def cleanup(self):
        """리소스 정리"""
        if self.db_manager:
            self.db_manager.close()
            self.initialized = False