"""
Hallucination Check Node (CRAG)
생성된 답변이 문서 내용과 일치하는지 검증하는 노드
"""

import os
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

from workflow.state import MVPWorkflowState, QualityCheckResult

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class HallucinationCheckResult(BaseModel):
    """환각 체크 결과"""
    is_grounded: bool = Field(description="Whether the answer is grounded in the documents")
    hallucination_score: float = Field(description="Hallucination score (0.0=no hallucination, 1.0=complete hallucination)")
    problematic_claims: List[str] = Field(description="List of claims not supported by documents")
    supported_claims: List[str] = Field(description="List of claims supported by documents")
    reasoning: str = Field(description="Detailed reasoning for the assessment")


class HallucinationCheckNode:
    """답변의 환각(hallucination) 체크 노드 - CRAG 패턴"""
    
    def __init__(self):
        """초기화"""
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,  # 일관된 평가를 위해 temperature 0
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 환각 체크 임계값 (.env에서 읽기)
        self.threshold = float(os.getenv("CRAG_HALLUCINATION_THRESHOLD", "0.7"))
        
        # 환각 체크 프롬프트
        self.hallucination_check_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a strict fact-checker for a RAG system.
Your task is to verify if the generated answer is fully grounded in the provided documents.

CRITICAL DISTINCTION - NOT Hallucinations:
✓ Stating "information is not in the documents" or "documents don't specify"
✓ Admitting lack of specific details
✓ Saying "cannot determine from provided documents"
✓ Being conservative about what can be claimed
✓ Reference numbers like [1], [2], etc. are citation markers, NOT content
✓ "References" section at the end is proper citation format
These are GOOD, GROUNDED responses that should be marked as valid.

Evaluation Process:
1. Extract all factual claims from the answer
2. Check each claim against the source documents
3. Identify unsupported claims (hallucinations)
4. Calculate hallucination score

Hallucination Score Guidelines:
- 0.0: All claims are directly supported by documents OR answer correctly states information is not available
- 0.1-0.3: Minor unsupported details that don't affect main answer
- 0.4-0.6: Some unsupported claims but core answer is correct
- 0.7-0.9: Major unsupported claims that affect answer quality
- 1.0: Answer is completely fabricated

Be STRICT in evaluation of positive claims:
- Claims must be EXPLICITLY stated or clearly implied in documents
- Reasonable inferences are acceptable only if strongly supported
- Technical specifications must match exactly
- Numbers, dates, procedures must be precise

Mark as problematic ONLY if answer makes false positive claims:
- Specific numbers not in documents (but claiming they are)
- Procedures or steps not mentioned (but presented as fact)
- Technical details not verified (but stated as true)
- Conclusions not supported by evidence (but claimed as certain)

Remember: An answer that admits "I don't have that information" is being honest, not hallucinating."""),
            ("human", """Original Query: {query}

Generated Answer:
{answer}

Source Documents:
{documents}

Evaluate if the answer is grounded in the documents.
List all claims and check each against the sources.""")
        ])
    
    def _format_documents_for_checking(self, documents: List[Document]) -> str:
        """
        체크용 문서 포맷팅
        
        Args:
            documents: 문서 리스트
            
        Returns:
            포맷팅된 문서 텍스트
        """
        if not documents:
            return "No source documents available"
        
        formatted = []
        for idx, doc in enumerate(documents, 1):
            metadata = doc.metadata
            formatted.append(f"""
Document {idx}:
- Source: {metadata.get('source', 'Unknown')}
- Page: {metadata.get('page', 'N/A')}
- Category: {metadata.get('category', 'Unknown')}
- Full Content:
{doc.page_content}
---""")
        
        return "\n".join(formatted)
    
    async def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[HALLUCINATION] Node started")
        
        try:
            # 체크할 답변 가져오기
            answer_to_check = state.get("intermediate_answer") or state.get("final_answer")
            
            if not answer_to_check:
                return {
                    "hallucination_check": {
                        "is_valid": False,
                        "score": 1.0,
                        "reason": "No answer to check",
                        "suggestions": ["Generate answer first"],
                        "needs_retry": False
                    },
                    "warnings": ["No answer available for hallucination check"]
                }
            
            # 원본 쿼리
            query = state["query"]
            
            # 사용된 문서들
            documents = state.get("documents", [])
            
            # CRITICAL: documents가 None이면 즉시 실패
            if documents is None:
                raise ValueError(
                    "CRITICAL ERROR: documents is None in hallucination check. "
                    "Previous nodes must provide documents list, not None."
                )
            
            # CRITICAL: documents가 빈 리스트면 즉시 실패
            if not documents:
                raise ValueError(
                    "CRITICAL ERROR: Empty documents list in hallucination check. "
                    "Retrieval must provide at least one document. "
                    "Cannot verify answer without source documents."
                )
            
            # 문서 포맷팅
            formatted_docs = self._format_documents_for_checking(documents)
            
            # LLM을 사용한 환각 체크
            structured_llm = self.llm.with_structured_output(HallucinationCheckResult)
            
            check_result = await structured_llm.ainvoke(
                self.hallucination_check_prompt.format_messages(
                    query=query,
                    answer=answer_to_check,
                    documents=formatted_docs
                )
            )
            
            # 재시도 필요 여부 결정
            needs_retry = check_result.hallucination_score > self.threshold
            
            # 환각 체크 결과 상세 정보 로깅
            logger.info(f"[HALLUCINATION] Score: {check_result.hallucination_score:.3f} | Grounded: {check_result.is_grounded}")
            if check_result.problematic_claims:
                problem_count = len(check_result.problematic_claims)
                problems_preview = ' | '.join([claim[:30] + '...' if len(claim) > 30 else claim for claim in check_result.problematic_claims[:2]])
                logger.info(f"[HALLUCINATION] {problem_count} problematic claims: {problems_preview}")
            if check_result.supported_claims:
                supported_count = len(check_result.supported_claims)
                logger.info(f"[HALLUCINATION] {supported_count} supported claims verified")
            
            # QualityCheckResult 형식으로 변환
            # is_valid는 환각 점수가 threshold 이하면 True (is_grounded는 참고용)
            quality_check: QualityCheckResult = {
                "is_valid": check_result.hallucination_score <= self.threshold,
                "score": 1.0 - check_result.hallucination_score,  # 신뢰도 점수로 변환
                "reason": check_result.reasoning,
                "suggestions": check_result.problematic_claims if check_result.problematic_claims else [],
                "needs_retry": needs_retry
            }
            
            # 메타데이터 업데이트
            metadata = state.get("metadata", {})
            metadata["hallucination_check"] = {
                "hallucination_score": check_result.hallucination_score,
                "is_grounded": check_result.is_grounded,
                "problematic_claims": check_result.problematic_claims,
                "supported_claims": check_result.supported_claims,
                "threshold": self.threshold
            }
            
            # 경고 추가 (필요시)
            warnings = []
            if check_result.hallucination_score > 0.5:
                warnings.append(f"High hallucination score: {check_result.hallucination_score:.2f}")
            
            return {
                "hallucination_check": quality_check,
                "should_retry": needs_retry,
                "metadata": metadata,
                "warnings": warnings  # Always return list, never None
            }
            
        except Exception as e:
            logger.error(f"[HALLUCINATION] Node failed: {str(e)}")
            return {
                "error": f"Hallucination check failed: {str(e)}",
                "workflow_status": "failed",
                "warnings": [f"Hallucination check error: {str(e)}"]
            }
    
    def invoke(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            # 이미 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성하여 실행
            return asyncio.run(self.__call__(state))
        else:
            # 이미 이벤트 루프가 실행 중이면 별도 스레드에서 실행
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.__call__(state))
                return future.result()