"""
Answer Grader Node (CRAG)
생성된 답변의 전체적인 품질을 평가하는 노드
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


class AnswerGradeResult(BaseModel):
    """답변 평가 결과"""
    overall_score: float = Field(description="Overall quality score (0.0-1.0)")
    completeness_score: float = Field(description="How completely the answer addresses the query (0.0-1.0)")
    relevance_score: float = Field(description="How relevant the answer is to the query (0.0-1.0)")
    clarity_score: float = Field(description="How clear and well-structured the answer is (0.0-1.0)")
    usefulness_score: float = Field(description="How useful/actionable the answer is (0.0-1.0)")
    missing_aspects: List[str] = Field(description="List of query aspects not addressed in the answer")
    improvement_suggestions: List[str] = Field(description="Specific suggestions to improve the answer")
    strengths: List[str] = Field(description="Strong points of the answer")
    reasoning: str = Field(description="Detailed reasoning for the assessment")


class AnswerGraderNode:
    """답변 품질 평가 노드 - CRAG 패턴"""
    
    def __init__(self):
        """초기화"""
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,  # 일관된 평가를 위해 temperature 0
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 답변 평가 임계값 (.env에서 읽기)
        self.threshold = float(os.getenv("CRAG_ANSWER_GRADE_THRESHOLD", "0.6"))
        
        # 답변 평가 프롬프트
        self.grading_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a quality evaluator for a RAG system specializing in automobile manufacturing documentation.
Your task is to evaluate the overall quality of generated answers.

Evaluation Criteria:

1. COMPLETENESS (0.0-1.0):
   - 1.0: Answer addresses ALL aspects of the query comprehensively
   - 0.7-0.9: Most aspects covered with good detail
   - 0.4-0.6: Some aspects covered but missing important details
   - 0.0-0.3: Major aspects missing or incomplete

2. RELEVANCE (0.0-1.0):
   - 1.0: Answer directly and precisely addresses the query
   - 0.7-0.9: Mostly relevant with minor digressions
   - 0.4-0.6: Partially relevant but includes unnecessary information
   - 0.0-0.3: Answer misses the point or addresses wrong topic

3. CLARITY (0.0-1.0):
   - 1.0: Crystal clear, well-structured, easy to follow
   - 0.7-0.9: Clear with minor structural issues
   - 0.4-0.6: Somewhat clear but could be better organized
   - 0.0-0.3: Confusing, poorly structured, hard to understand

4. USEFULNESS (0.0-1.0):
   - 1.0: Highly actionable with specific steps/information
   - 0.7-0.9: Useful with most necessary information
   - 0.4-0.6: Somewhat useful but lacks specifics
   - 0.0-0.3: Not useful, too vague or generic

Overall Score Calculation:
- Completeness: 35% weight
- Relevance: 30% weight
- Clarity: 20% weight
- Usefulness: 15% weight

Be specific in identifying:
- What aspects of the query were not addressed
- Concrete suggestions for improvement
- Strong points that should be maintained

For vehicle manual queries, pay special attention to:
- Safety warnings and cautions
- Specific procedures and steps
- Technical specifications
- Maintenance schedules
- Part numbers or references
- Proper citations with reference numbers [1], [2], etc.
- Completeness of References section at the end"""),
            ("human", """Original Query: {query}

Generated Answer:
{answer}

Source Documents Available:
{documents_summary}

Evaluate the answer quality comprehensively.
Identify strengths, weaknesses, and specific improvements needed.""")
        ])
        
    def _summarize_documents(self, documents: List[Document]) -> str:
        """
        문서 요약 생성 (평가 참고용)
        
        Args:
            documents: 문서 리스트
            
        Returns:
            문서 요약 텍스트
        """
        if not documents:
            return "No source documents available"
        
        summary = f"Total documents: {len(documents)}\n"
        
        # 카테고리별 문서 수 집계
        categories = {}
        sources = set()
        pages = set()
        
        for doc in documents:
            category = doc.metadata.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
            sources.add(doc.metadata.get("source", "unknown"))
            pages.add(doc.metadata.get("page", 0))
        
        summary += f"Sources: {', '.join(sources)}\n"
        summary += f"Pages covered: {len(pages)} pages\n"
        summary += "Document categories:\n"
        for category, count in categories.items():
            summary += f"  - {category}: {count} documents\n"
        
        # 상위 3개 문서의 주요 내용 포함
        summary += "\nKey content from top documents:\n"
        for idx, doc in enumerate(documents[:3], 1):
            content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            summary += f"{idx}. [{doc.metadata.get('category', 'unknown')}] {content_preview}\n"
        
        return summary
    
    def _calculate_overall_score(self, grade_result: AnswerGradeResult) -> float:
        """
        가중치를 적용한 전체 점수 계산
        
        Args:
            grade_result: 평가 결과
            
        Returns:
            전체 점수 (0.0-1.0)
        """
        weights = {
            "completeness": 0.35,
            "relevance": 0.30,
            "clarity": 0.20,
            "usefulness": 0.15
        }
        
        overall = (
            grade_result.completeness_score * weights["completeness"] +
            grade_result.relevance_score * weights["relevance"] +
            grade_result.clarity_score * weights["clarity"] +
            grade_result.usefulness_score * weights["usefulness"]
        )
        
        return min(overall, 1.0)
    
    async def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
        logger.info(f"[ANSWER_GRADER] Node started")
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        try:
            # 평가할 답변 가져오기
            answer_to_grade = state.get("intermediate_answer") or state.get("final_answer")
            
            if not answer_to_grade:
                return {
                    "answer_grade": {
                        "is_valid": False,
                        "score": 0.0,
                        "reason": "No answer to grade",
                        "suggestions": ["Generate answer first"],
                        "needs_retry": False
                    },
                    "warnings": ["No answer available for grading"]
                }
            
            # 원본 쿼리
            query = state["query"]
            
            # 사용된 문서들
            documents = state.get("documents", [])
            
            # CRITICAL: documents가 None이면 즉시 실패
            if documents is None:
                raise ValueError(
                    "CRITICAL ERROR: documents is None in answer grader. "
                    "Previous nodes must provide documents list, not None."
                )
            
            # CRITICAL: documents가 빈 리스트면 즉시 실패
            if not documents:
                raise ValueError(
                    "CRITICAL ERROR: Empty documents list in answer grader. "
                    "Retrieval must provide at least one document. "
                    "Cannot grade answer without source documents."
                )
            
            # 문서 요약 생성
            documents_summary = self._summarize_documents(documents)
            
            # LLM을 사용한 답변 평가
            structured_llm = self.llm.with_structured_output(AnswerGradeResult)
            
            grade_result = await structured_llm.ainvoke(
                self.grading_prompt.format_messages(
                    query=query,
                    answer=answer_to_grade,
                    documents_summary=documents_summary
                )
            )
            
            # 전체 점수 계산 (가중 평균)
            overall_score = self._calculate_overall_score(grade_result)
            
            # 4차원 품질 점수 상세 로깅
            logger.info(f"[ANSWER_GRADER] Overall: {overall_score:.3f} | Completeness: {grade_result.completeness_score:.3f} | Relevance: {grade_result.relevance_score:.3f} | Clarity: {grade_result.clarity_score:.3f}")
            logger.info(f"[ANSWER_GRADER] Usefulness: {grade_result.usefulness_score:.3f}")
            
            if grade_result.missing_aspects:
                missing_count = len(grade_result.missing_aspects)
                missing_preview = ' | '.join([aspect[:25] + '...' if len(aspect) > 25 else aspect for aspect in grade_result.missing_aspects[:2]])
                logger.info(f"[ANSWER_GRADER] {missing_count} missing aspects: {missing_preview}")
            
            if grade_result.improvement_suggestions:
                suggestions_count = len(grade_result.improvement_suggestions)
                logger.info(f"[ANSWER_GRADER] {suggestions_count} improvement suggestions available")
            
            # 재시도 필요 여부 결정
            needs_retry = overall_score < self.threshold
            
            # 개선이 필요한 주요 영역 식별
            low_scores = []
            if grade_result.completeness_score < 0.6:
                low_scores.append(f"Completeness: {grade_result.completeness_score:.2f}")
            if grade_result.relevance_score < 0.6:
                low_scores.append(f"Relevance: {grade_result.relevance_score:.2f}")
            if grade_result.clarity_score < 0.6:
                low_scores.append(f"Clarity: {grade_result.clarity_score:.2f}")
            if grade_result.usefulness_score < 0.6:
                low_scores.append(f"Usefulness: {grade_result.usefulness_score:.2f}")
            
            # QualityCheckResult 형식으로 변환
            quality_check: QualityCheckResult = {
                "is_valid": overall_score >= self.threshold,
                "score": overall_score,
                "reason": grade_result.reasoning,
                "suggestions": grade_result.improvement_suggestions,
                "needs_retry": needs_retry
            }
            
            # 메타데이터 업데이트
            metadata = state.get("metadata", {})
            metadata["answer_grade"] = {
                "overall_score": overall_score,
                "completeness": grade_result.completeness_score,
                "relevance": grade_result.relevance_score,
                "clarity": grade_result.clarity_score,
                "usefulness": grade_result.usefulness_score,
                "missing_aspects": grade_result.missing_aspects,
                "strengths": grade_result.strengths,
                "low_scores": low_scores,
                "threshold": self.threshold
            }
            
            # 경고 추가 (필요시)
            warnings = []
            if overall_score < 0.5:
                warnings.append(f"Low answer quality: {overall_score:.2f}")
            if grade_result.missing_aspects:
                warnings.append(f"Missing aspects: {', '.join(grade_result.missing_aspects[:3])}")
            
            return {
                "answer_grade": quality_check,
                "should_retry": needs_retry,
                "metadata": metadata,
                "warnings": warnings  # Always return list, never None
            }
            
        except Exception as e:
            logger.error(f"[ANSWER_GRADER] Node failed: {str(e)}")
            return {
                "error": f"Answer grading failed: {str(e)}",
                "workflow_status": "failed",
                "warnings": [f"Grading error: {str(e)}"]
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