"""
Subtask Executor Node
서브태스크 실행을 조율하는 노드 (쿼리 변형, 필터 생성 포함)
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import psycopg
from psycopg_pool import ConnectionPool
from concurrent.futures import ThreadPoolExecutor


from workflow.state import MVPWorkflowState
from retrieval.search_filter import MVPSearchFilter

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class QueryVariations(BaseModel):
    """쿼리 변형 결과"""
    variations: List[str] = Field(description="List of query variations (3 variations)")
    reasoning: str = Field(description="Reasoning for the variations")


class QueryExtraction(BaseModel):
    """쿼리에서 추출한 필터링 정보"""
    page_numbers: List[int] = Field(default_factory=list, description="Page numbers explicitly mentioned")
    categories_mentioned: List[str] = Field(default_factory=list, description="DDU categories mentioned")
    entity_type: Optional[str] = Field(None, description="Entity type ('image' or 'table') if mentioned")
    source_mentioned: Optional[str] = Field(None, description="Source file explicitly mentioned in query")
    keywords: List[str] = Field(default_factory=list, description="Key search keywords")
    specific_requirements: str = Field(default="", description="Specific requirements from query")


class DDUFilterGeneration(BaseModel):
    """DDU 필터 생성 결과"""
    categories: List[str] = Field(default_factory=list, description="DDU categories to filter")
    pages: List[int] = Field(default_factory=list, description="Page numbers to filter")
    sources: List[str] = Field(default_factory=list, description="Source files to filter (only if explicitly mentioned)")
    caption: Optional[str] = Field(None, description="Caption text to search")
    entity: Optional[Dict[str, Any]] = Field(None, description="Entity filter (type must be 'image', 'table', or '똑딱이')")
    reasoning: str = Field(default="", description="Reasoning for filter selection")


class MetadataHelper:
    """DB 메타데이터 헬퍼 (필수 연결, 최소 정보)"""
    
    def __init__(self):
        """초기화 - DB 연결 필수"""
        # DB 연결 정보 확인
        required_keys = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        
        if missing_keys:
            raise ValueError(
                f"Database configuration required. Missing: {missing_keys}\n"
                f"Please set these environment variables in .env file"
            )
        
        self.db_connection_string = (
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}"
            f"/{os.getenv('DB_NAME')}"
        )
        self._stats_cache = None
        self._cache_time = 0
    
    def get_metadata(self) -> Dict[str, Any]:
        """DB에서 최소한의 정확한 메타데이터만 조회"""
        try:
            with psycopg.connect(self.db_connection_string) as conn:
                with conn.cursor() as cur:
                    # 1. 사용 가능한 카테고리 (실제 존재하는 것만)
                    cur.execute(
                        """SELECT DISTINCT category 
                        FROM mvp_ddu_documents 
                        ORDER BY category"""
                    )
                    categories = cur.fetchall()
                    
                    # 2. 실제 존재하는 Entity 타입
                    cur.execute(
                        """SELECT DISTINCT entity->>'type' as type
                        FROM mvp_ddu_documents 
                        WHERE entity IS NOT NULL 
                        AND entity->>'type' IS NOT NULL
                        ORDER BY entity->>'type'"""
                    )
                    entity_types = cur.fetchall()
                    
                    # 3. Source 목록 (참고용)
                    cur.execute(
                        "SELECT DISTINCT source FROM mvp_ddu_documents ORDER BY source"
                    )
                    sources = cur.fetchall()
                    
                    return {
                        "categories": [r[0] for r in categories],
                        "entity_types": [r[0] for r in entity_types],
                        "available_sources": [r[0] for r in sources]
                    }
                
        except Exception as e:
            raise RuntimeError(f"Failed to fetch metadata from database: {str(e)}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 기본 통계 조회 (캐싱 포함)"""
        # 5분 캐싱 체크
        if self._stats_cache and (time.time() - self._cache_time < 300):
            return self._stats_cache
        
        try:
            with psycopg.connect(self.db_connection_string) as conn:
                with conn.cursor() as cur:
                    # 한 번의 쿼리로 모든 기본 정보 조회
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_docs,
                            COUNT(DISTINCT source) as source_count,
                            COUNT(DISTINCT category) as category_count,
                            MIN(page) as min_page,
                            MAX(page) as max_page,
                            COUNT(CASE WHEN embedding_korean IS NOT NULL THEN 1 END) as korean_emb,
                            COUNT(CASE WHEN embedding_english IS NOT NULL THEN 1 END) as english_emb
                        FROM mvp_ddu_documents
                    """)
                    stats = cur.fetchone()
                    
                    # 소스별 문서 수
                    cur.execute("""
                        SELECT source, COUNT(*) as count
                        FROM mvp_ddu_documents 
                        GROUP BY source
                        ORDER BY count DESC
                    """)
                    sources = dict(cur.fetchall())
                    
                    # 카테고리별 분포 (상위 5개)
                    cur.execute("""
                        SELECT category, COUNT(*) as count
                        FROM mvp_ddu_documents
                        GROUP BY category
                        ORDER BY count DESC
                        LIMIT 5
                    """)
                    categories = dict(cur.fetchall())
                    
                    self._stats_cache = {
                        "total_documents": stats[0],
                        "sources": sources,
                        "source_count": stats[1],
                        "category_count": stats[2],
                        "page_range": f"{stats[3]}-{stats[4]}" if stats[3] else "N/A",
                        "korean_embeddings": stats[5],
                        "english_embeddings": stats[6],
                        "top_categories": categories
                    }
                    self._cache_time = time.time()
                    return self._stats_cache
                    
        except Exception as e:
            logger.error(f"Failed to fetch system stats: {e}")
            # 에러 시 기본값 반환
            return {
                "total_documents": "unknown",
                "sources": {},
                "error": str(e)
            }


class SubtaskExecutorNode:
    """서브태스크 실행 노드 (개선된 버전)"""
    
    def __init__(self):
        """초기화"""
        # ChatOpenAI 인스턴스 직접 생성
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # DB 메타데이터 헬퍼 (필수)
        self.metadata_helper = MetadataHelper()
        
        # 쿼리 변형 프롬프트
        self.variation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query expansion expert for an automobile manufacturing RAG system.
Generate 3 variations of the given query to improve search coverage.

Guidelines:
1. Maintain the original intent
2. Use different phrasings and synonyms
3. Include both specific and general versions
4. Consider Korean and English variations if applicable
5. Think about what related information might be helpful

Examples:
- Original: "How to change engine oil"
  - Variation 1: "Engine oil replacement procedure"
  - Variation 2: "엔진 오일 교체 방법 및 주기"
  - Variation 3: "Steps for draining and refilling motor oil"

- Original: "안전벨트 착용 방법"
  - Variation 1: "How to fasten seatbelt correctly"
  - Variation 2: "시트벨트 올바른 사용법과 주의사항"
  - Variation 3: "Safety belt wearing instructions and adjustments"
"""),
            ("human", "Original query: {query}\n\nGenerate 3 variations:")
        ])
        
        # 쿼리 분석 프롬프트 (개선됨)
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query analyzer for an automobile manufacturing RAG system.
Extract filtering information ONLY if EXPLICITLY mentioned in the query.

STRICT RULES:
1. Page numbers: ONLY if explicitly stated (e.g., "page 10", "p.45", "50페이지")
2. Entity type: ONLY 'image', 'table', or '똑딱이'. Map similar terms:
   - 'figure', 'diagram', 'picture', 'illustration', '그림', '사진' → 'image'
   - 'chart', 'graph', '차트', '그래프' → 'image'
   - 'table', 'spreadsheet', '표', '테이블' → 'table'
   - '똑딱이', '똑딱이 타입', '똑딱이 문서', '참조문서', 'reference', 'appendix', '삽입객체' → '똑딱이'
3. Source: ONLY if document/manual/guide is EXPLICITLY mentioned
   - Extract source ONLY when these words appear: "매뉴얼", "manual", "guide", "설명서", "문서", "handbook"
   - DO NOT extract source from vehicle model names or product names alone
   - Examples:
     * "차량 엔진 오일" → NO source (no document mentioned)
     * "매뉴얼에서 오일 교체" → YES source (document explicitly mentioned)
     * "사용 설명서 50페이지" → YES source (document explicitly mentioned)
4. Categories: Map to exact DDU categories from the list provided
5. Be CONSERVATIVE - when in doubt, don't extract

Available Categories: {categories}
Available Entity Types: {entity_types}
Available Sources: {sources}"""),
            ("human", """Query: {query}

Extract ONLY explicitly mentioned filtering information:""")
        ])
        
        # 필터 생성 프롬프트 (강화된 프롬프트 엔지니어링)
        self.filter_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a CONSERVATIVE filter generator for an automobile manufacturing RAG system.
Create filters ONLY when they clearly help narrow down results.

STRICT FILTERING RULES:

DO CREATE FILTER when:
- Specific page is mentioned: "page 50" → pages: [50]
- Looking for tables: "show me tables" → entity: {{"type": "table"}} (NOT categories)
- Looking for images: "엔진 그림" → entity: {{"type": "image"}} (NOT categories)
- Looking for embedded docs: "똑딱이 문서" or "참조 문서" → entity: {{"type": "똑딱이"}} 
- Source EXPLICITLY mentioned with document words: "매뉴얼에서", "in the manual" → check available sources
- Specific category (NOT table/image): "heading" → categories: ["heading1"]

DON'T CREATE FILTER when:
- General queries: "how to change oil" → NO FILTER
- Broad topics: "safety features" → NO FILTER
- No specific mentions: "tell me about engine" → NO FILTER

EXAMPLES:

Query: "How to change engine oil"
Extraction: {{keywords: ["engine", "oil", "change"]}}
Filter: {{}} (EMPTY - let semantic search work)

Query: "Show me the maintenance schedule table on page 150"
Extraction: {{page_numbers: [150], entity_type: "table"}}
Filter: {{pages: [150], entity: {{"type": "table"}}}} (Use entity, NOT categories for table)

Query: "매뉴얼에서 안전벨트 관련 그림 찾아줘"
Extraction: {{source_mentioned: "manual", entity_type: "image", keywords: ["안전벨트"]}}
Filter: {{entity: {{"type": "image"}}}} (Source will be matched from available sources if needed)

Query: "What are the tire pressure specifications"
Extraction: {{keywords: ["tire", "pressure", "specifications"]}}
Filter: {{}} (EMPTY - no specific document or entity type mentioned)

Query: "PPT에 있는 참조문서 보여줘"
Extraction: {{entity_type: "똑딱이", keywords: []}}
Filter: {{entity: {{"type": "똑딱이"}}}} (Use entity for embedded documents)

Query: "특정 차량의 엔진 오일 교체 주기"
Extraction: {{keywords: ["차량", "엔진", "오일", "교체", "주기"]}}
Filter: {{}} (EMPTY - vehicle model is not a document source)

Query: "똑딱이 문서 알려줘"
Extraction: {{entity_type: "똑딱이", keywords: []}}
Filter: {{entity: {{"type": "똑딱이"}}}} (Direct mention of '똑딱이' type)

Remember: LESS IS MORE. Empty filter is better than wrong filter.

IMPORTANT RULES:
1. If source is mentioned, select ONLY from Available sources list.
2. Do not create new source names. If no exact match, leave sources empty.
3. NEVER use both 'categories' and 'entity' filters together - use ONLY ONE:
   - For tables: use entity: {{"type": "table"}} (NOT categories: ["table"])
   - For images: use entity: {{"type": "image"}} (NOT categories: ["figure"])
   - For embedded docs: use entity: {{"type": "똑딱이"}} (NOT categories: ["paragraph"])
   - This avoids overly restrictive filtering

Available entity types: {entity_types}
Available sources: {sources}"""),
            ("human", """Query: {query}
Extracted info: {extraction}

Generate MINIMAL filter (prefer empty over wrong):""")
        ])
    
    def _get_metadata_sync(self) -> Dict[str, Any]:
        """메타데이터를 동기 방식으로 가져오기"""
        # 이제 get_metadata()가 동기 메서드이므로 직접 호출
        return self.metadata_helper.get_metadata()
    
    def _generate_query_variations(self, query: str) -> List[str]:
        """쿼리 변형 생성"""
        structured_llm = self.llm.with_structured_output(
            QueryVariations
        )
        
        result = structured_llm.invoke(
            self.variation_prompt.format_messages(query=query)
        )
        
        # 원본 쿼리를 첫 번째로, 변형들을 추가
        return [query] + result.variations
    
    def _extract_query_info(self, query: str, metadata: Dict[str, Any]) -> QueryExtraction:
        """쿼리에서 필터링 정보 추출 (보수적)"""
        structured_llm = self.llm.with_structured_output(
            QueryExtraction
        )
        
        # 카테고리와 entity types, sources 문자열로 변환
        categories_str = ", ".join(metadata.get("categories", []))
        entity_types_str = ", ".join(metadata.get("entity_types", []))
        sources_str = ", ".join(metadata.get("available_sources", []))
        
        result = structured_llm.invoke(
            self.extraction_prompt.format_messages(
                query=query,
                categories=categories_str,
                entity_types=entity_types_str,
                sources=sources_str
            )
        )
        
        # Entity type 검증 (DB에 있는 타입만)
        valid_types = metadata.get("entity_types", [])
        if result.entity_type and result.entity_type not in valid_types:
            # 매핑 시도
            if result.entity_type == 'image' and 'image' in valid_types:
                pass  # 유지
            elif result.entity_type == 'table' and 'table' in valid_types:
                pass  # 유지
            elif result.entity_type == '똑딱이' and '똑딱이' in valid_types:
                pass  # 유지
            else:
                result.entity_type = None  # 유효하지 않으면 제거
        
        return result
    
    def _generate_filter(
        self,
        query: str,
        extraction: QueryExtraction,
        metadata: Dict[str, Any]
    ) -> Optional[MVPSearchFilter]:
        """최소한의 검색 필터 생성"""
        
        # 똑딱이 entity_type 강제 필터 생성
        if extraction.entity_type == '똑딱이' and '똑딱이' in metadata.get("entity_types", []):
            logger.info(f"[FILTER_OVERRIDE] Forcing '똑딱이' entity filter for query: {query}")
            return MVPSearchFilter(
                categories=None,
                pages=None,
                sources=None,
                caption=None,
                entity={'type': '똑딱이'}
            )
        
        structured_llm = self.llm.with_structured_output(
            DDUFilterGeneration,
            method="function_calling"
        )
        
        entity_types_str = ", ".join(metadata.get("entity_types", []))
        sources_str = ", ".join(metadata.get("available_sources", []))
        
        result = structured_llm.invoke(
            self.filter_prompt.format_messages(
                query=query,
                extraction=extraction.model_dump(),
                entity_types=entity_types_str,
                sources=sources_str
            )
        )
        
        # Debug logging
        logger.info(f"[FILTER_DEBUG] Query: {query}")
        logger.info(f"[FILTER_DEBUG] Extraction entity_type: {extraction.entity_type}")
        logger.info(f"[FILTER_DEBUG] Valid entity_types: {entity_types_str}")
        logger.info(f"[FILTER_DEBUG] Generated result.entity: {result.entity}")
        logger.info(f"[FILTER_DEBUG] Generated result.categories: {result.categories}")
        logger.info(f"[FILTER_DEBUG] Generated result.reasoning: {result.reasoning}")
        
        # Entity type 최종 검증
        valid_types = metadata.get("entity_types", [])
        if result.entity and 'type' in result.entity:
            if result.entity['type'] not in valid_types:
                result.entity = None  # 유효하지 않은 entity 제거
        
        # 카테고리 검증
        valid_categories = metadata.get("categories", [])
        if result.categories:
            result.categories = [c for c in result.categories if c in valid_categories]
        
        # Source 필터는 명시적 언급시만
        if result.sources and not extraction.source_mentioned:
            result.sources = []  # 명시적 언급 없으면 제거
        
        # 모든 필터가 비어있으면 None 반환
        if not any([result.categories, result.pages, result.sources, result.caption, result.entity]):
            return None
        
        # MVPSearchFilter 생성
        return MVPSearchFilter(
            categories=result.categories if result.categories else None,
            pages=result.pages if result.pages else None,
            sources=result.sources if result.sources else None,
            caption=result.caption,
            entity=result.entity
        )
    
    
    def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """노드 실행"""
        logger.info(f"[SUBTASK_EXECUTOR] Node started")
        
        
        try:
            # 현재 서브태스크 가져오기
            subtasks = state.get("subtasks", [])
            current_idx = state.get("current_subtask_idx", 0)
            logger.debug(f"[SUBTASK_EXECUTOR] Subtasks: {len(subtasks)}, current_idx: {current_idx}")
            
            if not subtasks or current_idx >= len(subtasks):
                # 서브태스크가 없거나 모두 완료됨
                logger.info(f"[SUBTASK_EXECUTOR] No more subtasks to process ({current_idx}/{len(subtasks)})")
                return {
                    "workflow_status": "completed",
                    "metadata": state.get("metadata", {})
                }
            
            current_subtask = subtasks[current_idx]
            query = current_subtask["query"]
            current_status = current_subtask.get("status", "pending")
            subtask_id = current_subtask.get("id", "no-id")[:8]
            logger.debug(f"[SUBTASK_EXECUTOR] Current subtask [{subtask_id}]: '{query}' (status: {current_status})")
            
            # retrieved 상태면 다음 서브태스크로 이동
            if current_status == "retrieved":
                logger.info(f"[SUBTASK_EXECUTOR] Subtask [{subtask_id}] already retrieved, moving to next")
                
                # 인덱스 증가
                new_idx = current_idx + 1
                logger.info(f"[SUBTASK_EXECUTOR] Advancing index: {current_idx} -> {new_idx}")
                
                # 다음 서브태스크가 있는지 확인
                if new_idx >= len(subtasks):
                    logger.info(f"[SUBTASK_EXECUTOR] All subtasks processed ({new_idx}/{len(subtasks)})")
                    return {
                        "current_subtask_idx": new_idx,
                        "workflow_status": "completed"
                    }
                
                # 다음 서브태스크 처리 준비
                next_subtask = subtasks[new_idx]
                next_query = next_subtask["query"]
                next_status = next_subtask.get("status", "pending")
                next_id = next_subtask.get("id", "no-id")[:8]
                logger.info(f"[SUBTASK_EXECUTOR] Preparing next subtask [{next_id}]: '{next_query}' (status: {next_status})")
                
                # 다음 서브태스크가 이미 query_variations를 가지고 있으면 사용
                if next_subtask.get("query_variations"):
                    logger.info(f"[SUBTASK_EXECUTOR] Next subtask already has query_variations")
                    return {
                        "current_subtask_idx": new_idx,
                        "query_variations": next_subtask["query_variations"]
                    }
                
                # 다음 서브태스크를 위한 query_variations 생성 필요
                # (아래 정상 처리 로직으로 진행)
                current_idx = new_idx
                current_subtask = next_subtask
                query = next_query
                current_status = next_status
                subtask_id = next_id
                logger.info(f"[SUBTASK_EXECUTOR] Will process next subtask [{subtask_id}]")
            
            # executing 상태면 이미 처리 중이므로 건너뛰기
            elif current_status == "executing":
                logger.info(f"[SUBTASK_EXECUTOR] Subtask [{subtask_id}] already executing")
                
                # query_variations가 있어야 함
                if not current_subtask.get("query_variations"):
                    raise ValueError(
                        f"Subtask [{subtask_id}] is in 'executing' state but has no query_variations. "
                        "This is an invalid state."
                    )
                
                return {
                    "query_variations": current_subtask["query_variations"]
                }
            
            # completed 상태는 건너뛰고 다음으로
            elif current_status == "completed":
                logger.warning(f"[SUBTASK_EXECUTOR] Subtask [{subtask_id}] already completed - this shouldn't happen")
                return {
                    "current_subtask_idx": current_idx + 1
                }
            
            # DB 메타데이터 가져오기 (필수)
            logger.debug(f"[SUBTASK_EXECUTOR] Fetching DB metadata...")
            # 동기 방식으로 메타데이터 가져오기
            metadata = self._get_metadata_sync()
            available_categories = metadata.get("categories", [])
            available_entity_types = metadata.get("entity_types", [])
            logger.debug(f"[SUBTASK_EXECUTOR] DB metadata: {len(available_categories)} categories, {len(available_entity_types)} entity types")
            
            # 1. 쿼리 변형 생성 (Multi-Query)
            logger.info(f"[SUBTASK_EXECUTOR] Generating query variations for: '{query}'")
            variations = self._generate_query_variations(query)
            logger.info(f"[SUBTASK_EXECUTOR] Generated {len(variations)} query variations")
            
            # 쿼리 변형 상세 정보 로깅
            for i, variation in enumerate(variations):
                var_preview = variation[:70] + ('...' if len(variation) > 70 else '')
                marker = "(original)" if i == 0 else f"(var{i})"
                logger.info(f"[SUBTASK_EXECUTOR] Query {i+1}: \"{var_preview}\" {marker}")
            
            # 2. 쿼리 정보 추출 (보수적)
            logger.debug(f"[SUBTASK_EXECUTOR] Extracting query information...")
            extraction = self._extract_query_info(query, metadata)
            logger.info(f"[SUBTASK_EXECUTOR] Extracted info:")
            logger.info(f"  - pages: {extraction.page_numbers}")
            logger.info(f"  - categories_mentioned: {extraction.categories_mentioned}")
            logger.info(f"  - entity_type: {extraction.entity_type}")
            logger.info(f"  - source_mentioned: {extraction.source_mentioned}")
            logger.info(f"  - keywords: {extraction.keywords}")
            logger.info(f"  - specific_requirements: {extraction.specific_requirements}")
            
            # 3. 최소 검색 필터 생성
            logger.debug(f"[SUBTASK_EXECUTOR] Generating search filter...")
            search_filter = self._generate_filter(query, extraction, metadata)
            filter_dict = search_filter.to_dict() if search_filter else None
            
            if filter_dict:
                logger.info(f"[SUBTASK_EXECUTOR] Search filter generated:")
                for key, value in filter_dict.items():
                    if value is not None:
                        logger.info(f"  - {key}: {value}")
            else:
                logger.info(f"[SUBTASK_EXECUTOR] No search filter generated (empty)")
            
            # 서브태스크 업데이트
            logger.debug(f"[SUBTASK_EXECUTOR] Updating subtask status to 'executing'")
            current_subtask["query_variations"] = variations
            current_subtask["extracted_info"] = {
                "pages": extraction.page_numbers,
                "categories": extraction.categories_mentioned,
                "entity_type": extraction.entity_type,
                "source": extraction.source_mentioned,
                "keywords": extraction.keywords,
                "requirements": extraction.specific_requirements
            }
            current_subtask["status"] = "executing"
            logger.info(f"[SUBTASK_EXECUTOR] Subtask [{subtask_id}] status updated: 'pending' -> 'executing'")
            
            # 메타데이터 업데이트
            task_metadata = state.get("metadata", {})
            task_metadata[f"subtask_{current_idx}"] = {
                "original_query": query,
                "variations": variations,
                "filter_applied": filter_dict,
                "available_categories": available_categories,
                "available_entity_types": available_entity_types
            }
            logger.debug(f"[SUBTASK_EXECUTOR] Updated task metadata for subtask_{current_idx}")
            
            # Only pass through documents when coming from planning (index 0)
            # to preserve the clearing signal. For other cases, don't include documents
            # to avoid duplication issues with the add reducer
            result = {
                "subtasks": subtasks,
                "current_subtask_idx": current_idx,  # 현재 처리 중인 서브태스크 인덱스 반환
                "search_filter": filter_dict,
                "metadata": task_metadata,
                "query_variations": variations  # Retrieval Node에서 사용 (state.py의 필드명과 일치)
            }
            
            # Only include documents field when it's the first subtask (to pass the clearing signal)
            if current_idx == 0 and len(state.get("documents", [])) == 0:
                result["documents"] = []  # Pass empty list to trigger clearing
                logger.info(f"[SUBTASK_EXECUTOR] Passing document clearing signal for first subtask")
            
            logger.info(f"[SUBTASK_EXECUTOR] Node completed successfully - prepared {len(variations)} variations for retrieval")
            return result
            
        except ValueError as e:
            # DB 연결 실패 등
            logger.error(f"[SUBTASK_EXECUTOR] Configuration error: {str(e)}")
            return {
                "error": f"Configuration error: {str(e)}",
                "workflow_status": "failed",
                "warnings": [f"Subtask executor configuration error: {str(e)}"]
            }
        except Exception as e:
            logger.error(f"[SUBTASK_EXECUTOR] Execution failed: {str(e)}")
            return {
                "error": f"Subtask execution failed: {str(e)}",
                "workflow_status": "failed",
                "warnings": [f"Subtask executor error: {str(e)}"]
            }
    
    def invoke(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        logger.debug(f"[SUBTASK_EXECUTOR] Invoke called (sync wrapper)")
        return self.__call__(state)