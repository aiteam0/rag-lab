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
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv


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
        # ChatOpenAI 인스턴스 직접 생성
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
            # Document 객체 타입 검증 및 복원
            if isinstance(doc, str):
                # LangGraph가 Document를 string으로 직렬화한 경우
                try:
                    import json
                    doc_dict = json.loads(doc)
                    from langchain_core.documents import Document
                    doc = Document(
                        page_content=doc_dict.get("page_content", ""),
                        metadata=doc_dict.get("metadata", {})
                    )
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"[HALLUCINATION] Failed to parse document string at index {idx}")
                    continue
            elif isinstance(doc, dict):
                # LangGraph 직렬화로 dict가 된 경우
                from langchain_core.documents import Document
                doc = Document(
                    page_content=doc.get("page_content", ""),
                    metadata=doc.get("metadata", {})
                )
            elif not hasattr(doc, 'metadata') or not hasattr(doc, 'page_content'):
                # 잘못된 형식의 객체인 경우
                logger.warning(f"[HALLUCINATION] Invalid document format at index {idx}: {type(doc)}")
                continue
            
            metadata = doc.metadata
            
            # 기본 문서 정보
            doc_text = f"""
Document {idx}:
- Source: {metadata.get('source', 'Unknown')}
- Page: {metadata.get('page', 'N/A')}
- Category: {metadata.get('category', 'Unknown')}"""
            
            # Human feedback이 있으면 최우선으로 추가 (타입 안전성 보장)
            human_feedback = metadata.get('human_feedback')
            if human_feedback and isinstance(human_feedback, str) and human_feedback.strip():
                doc_text += f"\n- Human Verified Content: {human_feedback}"
            
            # Entity 정보가 있으면 구조화된 형태로 추가 (타입 안전성 보장)
            entity = metadata.get('entity')
            if entity:
                # entity가 dictionary가 아닌 경우 안전하게 처리
                if not isinstance(entity, dict):
                    doc_text += f"\n- Entity Info: {str(entity)}"
                else:
                    category = metadata.get('category', '')
                    entity_type = entity.get('type', '')
                    
                    # '똑딱이' 타입 처리
                    if entity_type == '똑딱이':
                        doc_text += "\n- PPT Embedded Document (똑딱이):"
                        title = entity.get('title')
                        if title and isinstance(title, str):
                            doc_text += f"\n  Title: {title}"
                        details = entity.get('details')
                        if details and isinstance(details, str):
                            doc_text += f"\n  Details: {details}"
                        keywords = entity.get('keywords')
                        if keywords and isinstance(keywords, list):
                            doc_text += f"\n  Keywords: {', '.join(str(k) for k in keywords)}"
                        hypothetical_questions = entity.get('hypothetical_questions')
                        if hypothetical_questions and isinstance(hypothetical_questions, list):
                            questions_to_show = hypothetical_questions[:3]
                            doc_text += f"\n  Can Answer: {'; '.join(str(q) for q in questions_to_show)}"
                    elif category == 'table' and entity:
                        doc_text += "\n- Table Information:"
                        title = entity.get('title')
                        if title and isinstance(title, str):
                            doc_text += f"\n  Title: {title}"
                        details = entity.get('details')
                        if details and isinstance(details, str):
                            doc_text += f"\n  Details: {details}"
                        keywords = entity.get('keywords')
                        if keywords and isinstance(keywords, list):
                            doc_text += f"\n  Keywords: {', '.join(str(k) for k in keywords)}"
                    elif category == 'figure' and entity:
                        doc_text += "\n- Figure Information:"
                        title = entity.get('title')
                        if title and isinstance(title, str):
                            doc_text += f"\n  Title: {title}"
                        details = entity.get('details')
                        if details and isinstance(details, str):
                            doc_text += f"\n  Description: {details}"
            
            # 캡션이 있으면 추가
            if metadata.get('caption'):
                doc_text += f"\n- Caption: {metadata['caption']}"
            
            # 원본 콘텐츠
            doc_text += f"\n- Full Content:\n{doc.page_content}\n---"
            
            formatted.append(doc_text)
        
        return "\n".join(formatted)
    
    def _check_entity_mentions(self, answer: str, documents: List[Document]) -> Dict[str, Any]:
        """
        답변에서 중요한 entity type들이 언급되었는지 확인
        
        Args:
            answer: 생성된 답변
            documents: 원본 문서들
            
        Returns:
            entity 언급 체크 결과
        """
        # 똑딱이 entity가 있는지 확인
        has_ddokddak = False
        ddokddak_titles = []
        
        for doc in documents:
            if not isinstance(doc, Document):
                continue
            
            metadata = doc.metadata or {}
            entity = metadata.get("entity", {})
            
            if isinstance(entity, dict):
                entity_type = entity.get("type", "")
                if entity_type == "똑딱이":
                    has_ddokddak = True
                    title = entity.get("title", "")
                    if title and title not in ddokddak_titles:
                        ddokddak_titles.append(title)
        
        # 똑딱이 entity가 있는 경우 답변에서 언급했는지 확인
        if has_ddokddak:
            # 답변에서 관련 키워드 언급 여부 확인
            mention_keywords = ["똑딱이", "PPT", "삽입 문서", "embedded", "프레젠테이션"]
            mentioned = any(keyword in answer for keyword in mention_keywords)
            
            if not mentioned:
                logger.warning(f"[HALLUCINATION] 똑딱이 entity가 {len(ddokddak_titles)}개 있지만 답변에서 언급되지 않음")
                logger.warning(f"[HALLUCINATION] 똑딱이 문서 제목: {', '.join(ddokddak_titles)}")
                
                return {
                    "has_special_entity": True,
                    "entity_mentioned": False,
                    "missing_entity_type": "똑딱이 (PPT 삽입 문서)",
                    "entity_titles": ddokddak_titles,
                    "warning_message": f"문서에 PPT 삽입 문서(똑딱이) {len(ddokddak_titles)}개가 포함되어 있으나 답변에서 언급되지 않았습니다."
                }
            else:
                logger.info(f"[HALLUCINATION] 똑딱이 entity가 적절히 언급됨")
                return {
                    "has_special_entity": True,
                    "entity_mentioned": True,
                    "entity_type": "똑딱이 (PPT 삽입 문서)"
                }
        
        return {
            "has_special_entity": False
        }
    
    def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
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
            structured_llm = self.llm.with_structured_output(
                HallucinationCheckResult
            )
            
            check_result = structured_llm.invoke(
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
            
            # Entity 언급 체크 (특히 똑딱이)
            entity_check = self._check_entity_mentions(answer_to_check, documents)
            if entity_check.get("has_special_entity"):
                metadata["entity_mention_check"] = entity_check
                
                # 똑딱이가 언급되지 않은 경우 경고
                if not entity_check.get("entity_mentioned", True):
                    warning_msg = entity_check.get("warning_message", "특수 entity가 답변에서 언급되지 않음")
                    logger.warning(f"[HALLUCINATION] {warning_msg}")
            
            # 경고 추가 (필요시)
            warnings = []
            if check_result.hallucination_score > 0.5:
                warnings.append(f"High hallucination score: {check_result.hallucination_score:.2f}")
            
            # 메시지 생성 - 환각 검증 과정 상세 정보
            messages = []
            
            # 1. 검증 시작
            messages.append(
                AIMessage(content="🔍 환각 검증을 시작합니다...")
            )
            
            # 2. 검증 항목별 점수
            total_claims = len(check_result.supported_claims) + len(check_result.problematic_claims)
            grounding_rate = (len(check_result.supported_claims) / total_claims * 100) if total_claims > 0 else 100
            
            messages.append(
                AIMessage(content=f"""📊 검증 결과 상세:
  • 전체 주장: {total_claims}개 검증
  • 문서 확인됨: {len(check_result.supported_claims)}개 ✅
  • 문서 미확인: {len(check_result.problematic_claims)}개 ⚠️
  • 문서 근거율: {grounding_rate:.0f}%
  • 환각 수준: {check_result.hallucination_score:.0%} (낮을수록 좋음)""")
            )
            
            # 3. 종합 점수와 기준
            messages.append(
                AIMessage(content=f"📈 환각 점수: {check_result.hallucination_score:.0%} (기준: <{self.threshold:.0%})")
            )
            
            # 4. 검증 결과
            retry_count = state.get("retry_count", 0)
            max_retries = int(os.getenv("CRAG_MAX_RETRIES", "3"))
            if quality_check["is_valid"]:
                messages.append(
                    AIMessage(content="✅ 환각 검증 통과 - 답변이 문서 내용과 일치합니다")
                )
            else:
                if needs_retry and retry_count < max_retries:
                    messages.append(
                        AIMessage(content=f"⚠️ 환각 감지 - 재생성 필요 (시도 {retry_count+1}/{max_retries})")
                    )
                else:
                    messages.append(
                        AIMessage(content="❌ 환각 검증 실패 - 최대 재시도 횟수 초과")
                    )
            
            return {
                "messages": messages,  # 메시지 추가
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
        logger.debug(f"[HALLUCINATION] Invoke called (sync wrapper)")
        return self.__call__(state)