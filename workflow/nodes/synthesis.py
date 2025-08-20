"""
Synthesis Node
검색된 문서들을 바탕으로 답변을 생성하는 노드
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

from workflow.state import MVPWorkflowState

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class SynthesisResult(BaseModel):
    """답변 생성 결과"""
    answer: str = Field(description="Generated answer with inline citations [1], [2], etc. MUST end with References table")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    sources_used: List[str] = Field(description="List of source references used in format: '[1]', '[2]', etc.")
    key_points: List[str] = Field(description="Key points extracted from documents")
    references_table: str = Field(description="MANDATORY References table in format: | 참조번호 | 문서명 | 페이지 | 내용 요약 |")


class SynthesisNode:
    """검색된 문서를 기반으로 답변을 생성하는 노드"""
    
    def __init__(self):
        """초기화"""
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,  # 더 일관된 답변을 위해 낮은 temperature
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 답변 생성 프롬프트
        self.synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert assistant for an automobile manufacturing RAG system.
Your task is to generate comprehensive and accurate answers based on the retrieved documents.

Guidelines:
1. Base your answer ONLY on the provided documents
2. If information is not in the documents, say so clearly
3. Cite sources using reference numbers [1], [2], etc. in the main text
4. Structure your answer clearly with proper formatting
5. For Korean documents, maintain Korean terms where appropriate
6. Include specific details like numbers, procedures, and specifications
7. If there are conflicting information, mention both sources and explain
8. Use the same reference number for the same document throughout the answer
9. Place reference numbers immediately after the relevant statement

Answer Structure:
- Start with a direct answer to the question
- Provide supporting details from documents with inline citations [1], [2]
- Include relevant warnings or cautions if mentioned
- End with a "References" section listing all cited documents

References Format:
Create a numbered list at the end of your answer with this format:
References:
[1] filename.pdf, Page X - Brief description of content
[2] filename.pdf, Page Y - Brief description of content

Important:
- DO NOT make up information not in the documents
- DO NOT add personal opinions or assumptions
- DO maintain consistent reference numbering throughout
- DO include ALL cited documents in the References section
- DO use the document numbers provided in square brackets [1], [2], etc.

CRITICAL REQUIREMENT - STRUCTURED OUTPUT:
You are generating a structured output with these fields:
1. answer: Main answer with inline citations [1], [2], etc.
2. confidence: How confident you are (0.0-1.0)
3. sources_used: List of references like ['[1]', '[2]', '[3]']
4. key_points: Key points from the documents
5. references_table: MANDATORY table with format below

The references_table field MUST contain a markdown table:
| 참조번호 | 문서명 | 페이지 | 내용 요약 |
|---------|--------|--------|-----------|
| [1] | actual_filename.pdf | p.X | What this document contains |
| [2] | actual_filename.pdf | p.Y | What this document contains |

IMPORTANT: The references_table is a SEPARATE field from answer.
DO NOT put the References table in the answer field.
Put it in the references_table field."""),
            ("human", """Query: {query}

Retrieved Documents:
{documents}

Generate a structured response with ALL these fields:
1. answer: Comprehensive answer with inline citations [1], [2], etc.
2. confidence: Your confidence score (0.0-1.0)
3. sources_used: List like ['[1]', '[2]', '[3]'] for all cited documents
4. key_points: Main points extracted from documents
5. references_table: MANDATORY markdown table with this format:

| 참조번호 | 문서명 | 페이지 | 내용 요약 |
|---------|--------|--------|-----------|
| [1] | gv80_manual.pdf | p.245 | Engine oil change procedure |
| [2] | maintenance.pdf | p.52 | Oil specifications and capacity |

CRITICAL: The references_table field MUST be filled with the actual table.
Extract source filename and page from each document's metadata.
Generate your structured response now:""")
        ])
        
        # 문서 포맷팅 템플릿
        self.document_formatter_prompt = """
[{idx}] Document Reference:
- Source: {source}
- Page: {page}
- Category: {category}
- Content: {content}
{caption}
---
Note: Use [{idx}] when citing this document in your answer.
"""
    
    def _format_documents(self, documents: List[Document], truncate: bool = False) -> str:
        """
        문서들을 프롬프트용 텍스트로 포맷팅
        
        Args:
            documents: 문서 리스트
            truncate: True일 경우 문서 내용 축약 (fallback용)
            
        Returns:
            포맷팅된 문서 텍스트
        """
        if not documents:
            return "No documents available"
        
        formatted_docs = []
        for idx, doc in enumerate(documents, 1):
            metadata = doc.metadata
            
            # 캡션이 있으면 추가
            caption_text = ""
            if metadata.get("caption"):
                caption_text = f"- Caption: {metadata['caption']}"
            
            # 문서 내용 (truncate가 True일 때만 축약)
            content = doc.page_content[:500] if truncate else doc.page_content
            
            formatted_doc = self.document_formatter_prompt.format(
                idx=idx,
                source=metadata.get("source", "Unknown"),
                page=metadata.get("page", "N/A"),
                category=metadata.get("category", "Unknown"),
                content=content,
                caption=caption_text
            )
            formatted_docs.append(formatted_doc)
        
        return "\n".join(formatted_docs)
    
    async def _generate_answer_with_fallback(
        self, 
        query: str, 
        documents: List[Document]
    ) -> SynthesisResult:
        """
        답변 생성 (max token 에러 시 fallback 포함)
        
        Args:
            query: 질문
            documents: 문서 리스트
            
        Returns:
            생성된 답변 결과
        """
        # 먼저 전체 문서로 시도
        try:
            formatted_docs = self._format_documents(documents, truncate=False)
            
            structured_llm = self.llm.with_structured_output(SynthesisResult)
            
            result = await structured_llm.ainvoke(
                self.synthesis_prompt.format_messages(
                    query=query,
                    documents=formatted_docs
                )
            )
            return result
            
        except Exception as e:
            # Token 제한 에러인 경우 fallback
            if "maximum context length" in str(e).lower() or "token" in str(e).lower():
                print(f"Token limit exceeded, falling back to truncated documents")
                
                # 문서 축약하여 재시도
                formatted_docs = self._format_documents(documents, truncate=True)
                
                structured_llm = self.llm.with_structured_output(SynthesisResult)
                
                result = await structured_llm.ainvoke(
                    self.synthesis_prompt.format_messages(
                        query=query,
                        documents=formatted_docs
                    )
                )
                return result
            else:
                # 다른 에러는 그대로 전파
                raise e
    
    async def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """
        노드 실행
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            업데이트된 상태 필드
        """
        logger.info(f"[SYNTHESIS] Node started")
        
        try:
            # 현재 처리 중인 쿼리와 문서 결정
            subtasks = state.get("subtasks", [])
            current_idx = state.get("current_subtask_idx", 0)
            logger.debug(f"[SYNTHESIS] Subtasks: {len(subtasks)}, current_idx: {current_idx}")
            
            if subtasks and current_idx < len(subtasks):
                # 서브태스크 처리
                current_subtask = subtasks[current_idx]
                query = current_subtask["query"]
                # Retrieval Node에서 검색된 문서 그대로 사용
                documents = current_subtask.get("documents", [])
                subtask_id = current_subtask.get("id", "no-id")[:8]
                logger.info(f"[SYNTHESIS] Processing subtask [{subtask_id}]: '{query}'")
                logger.debug(f"[SYNTHESIS] Subtask has {len(documents)} documents")
            else:
                # 전체 쿼리 처리
                query = state["query"]
                # 전체 검색된 문서 그대로 사용
                documents = state.get("documents", [])
                logger.info(f"[SYNTHESIS] Processing full query: '{query}'")
                logger.debug(f"[SYNTHESIS] State has {len(documents)} documents")
            
            # documents가 None이면 즉시 실패
            if documents is None:
                raise ValueError(
                    "CRITICAL ERROR: documents is None in synthesis. "
                    "Retrieval node must provide documents list (can be empty but not None)."
                )
            
            # CRITICAL: documents가 빈 리스트면 즉시 실패
            if not documents:
                logger.error(f"[SYNTHESIS] CRITICAL: Empty documents list")
                raise ValueError(
                    "CRITICAL ERROR: Empty documents list in synthesis. "
                    "Retrieval must provide at least one document. "
                    "Cannot generate answer without source documents."
                )
            
            # 재시도 상황 감지 및 피드백 활용
            retry_count = state.get("retry_count", 0)
            hallucination_feedback = state.get("hallucination_check")
            quality_feedback = state.get("answer_grade")
            
            # 재시도 여부 확인 (피드백에서 needs_retry 확인)
            is_retry_from_hallucination = hallucination_feedback and hallucination_feedback.get("needs_retry", False)
            is_retry_from_quality = quality_feedback and quality_feedback.get("needs_retry", False)
            is_retry = is_retry_from_hallucination or is_retry_from_quality
            
            # 재시도인 경우 retry_count 증가
            if is_retry:
                retry_count = retry_count + 1
                logger.info(f"[SYNTHESIS] Retry attempt {retry_count} - analyzing feedback")
                
                # 환각 체크 실패로 인한 재시도
                if is_retry_from_hallucination:
                    logger.info(f"[SYNTHESIS] Using corrective generation due to hallucination concerns")
                    logger.debug(f"[SYNTHESIS] Hallucination score: {hallucination_feedback.get('score', 0)}")
                    synthesis_result = await self._generate_corrective_answer(
                        query, documents, hallucination_feedback, state.get("metadata", {})
                    )
                # 품질 체크 실패로 인한 재시도
                elif is_retry_from_quality:
                    logger.info(f"[SYNTHESIS] Using improved generation due to quality concerns")
                    logger.debug(f"[SYNTHESIS] Quality score: {quality_feedback.get('score', 0)}")
                    synthesis_result = await self._generate_improved_answer(
                        query, documents, quality_feedback, state.get("metadata", {})
                    )
            else:
                # 첫 번째 시도
                logger.info(f"[SYNTHESIS] Generating answer using {len(documents)} documents...")
                synthesis_result = await self._generate_answer_with_fallback(query, documents)
            logger.info(f"[SYNTHESIS] Answer generated with confidence: {synthesis_result.confidence:.3f}")
            
            # 사용된 소스와 키포인트 상세 정보 로깅
            sources_count = len(synthesis_result.sources_used)
            sources_preview = ', '.join(synthesis_result.sources_used[:3]) + ('...' if sources_count > 3 else '')
            logger.info(f"[SYNTHESIS] Used {sources_count} sources: [{sources_preview}]")
            
            if synthesis_result.key_points:
                points_count = len(synthesis_result.key_points)
                points_preview = ' | '.join([kp[:35] + '...' if len(kp) > 35 else kp for kp in synthesis_result.key_points[:2]])
                logger.info(f"[SYNTHESIS] {points_count} key points: {points_preview}")
            
            # 메타데이터 업데이트
            metadata = state.get("metadata", {})
            metadata["synthesis"] = {
                "documents_used": len(documents),
                "sources": synthesis_result.sources_used,
                "key_points": synthesis_result.key_points,
                "confidence": synthesis_result.confidence
            }
            logger.debug(f"[SYNTHESIS] Updated metadata with synthesis results")
            
            # References 테이블을 답변에 추가
            final_answer = synthesis_result.answer
            if hasattr(synthesis_result, 'references_table') and synthesis_result.references_table:
                # References 테이블이 별도 필드로 제공된 경우 답변 끝에 추가
                if "References:" not in final_answer:
                    final_answer = f"{final_answer}\n\n## References:\n{synthesis_result.references_table}"
            
            # 서브태스크 업데이트
            if subtasks and current_idx < len(subtasks):
                subtasks[current_idx]["answer"] = final_answer
                subtasks[current_idx]["status"] = "synthesized"
                subtask_id = subtasks[current_idx].get("id", "no-id")[:8]
                logger.info(f"[SYNTHESIS] Updated subtask [{subtask_id}] status: 'retrieved' -> 'synthesized'")
                
                result = {
                    "subtasks": subtasks,
                    "intermediate_answer": final_answer,
                    "confidence_score": synthesis_result.confidence,
                    "metadata": metadata,
                    "retry_count": retry_count  # 재시도 횟수 포함
                }
                logger.info(f"[SYNTHESIS] Node completed - intermediate answer generated")
                return result
            else:
                # 최종 답변
                result = {
                    "final_answer": final_answer,
                    "confidence_score": synthesis_result.confidence,
                    "metadata": metadata,
                    "retry_count": retry_count  # 재시도 횟수 포함
                }
                logger.info(f"[SYNTHESIS] Node completed - final answer generated")
                return result
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Node failed: {str(e)}")
            return {
                "error": f"Synthesis failed: {str(e)}",
                "workflow_status": "failed",
                "warnings": [f"Synthesis error: {str(e)}"]
            }
    
    def invoke(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """동기 실행 (LangGraph 호환성)"""
        logger.debug(f"[SYNTHESIS] Invoke called (sync wrapper)")
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            # 이미 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
            logger.debug(f"[SYNTHESIS] Event loop detected, using ThreadPoolExecutor")
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성하여 실행
            logger.debug(f"[SYNTHESIS] No event loop, creating new one")
            return asyncio.run(self.__call__(state))
        else:
            # 이미 이벤트 루프가 실행 중이면 별도 스레드에서 실행
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.__call__(state))
                return future.result()
    
    async def _generate_corrective_answer(self, query: str, documents: List[Document], 
                                         hallucination_feedback: Dict[str, Any], 
                                         metadata: Dict[str, Any]) -> SynthesisResult:
        """
        환각 체크 실패 시 보수적인 답변 생성
        
        Args:
            query: 사용자 쿼리
            documents: 검색된 문서들
            hallucination_feedback: 환각 체크 피드백
            metadata: 추가 메타데이터
            
        Returns:
            보수적으로 생성된 답변 결과
        """
        logger.info(f"[SYNTHESIS] Generating corrective answer to avoid hallucination")
        
        # 문제가 된 주장들과 제안사항 추출
        hallucination_meta = metadata.get("hallucination_check", {})
        problematic_claims = hallucination_meta.get("problematic_claims", [])
        supported_claims = hallucination_meta.get("supported_claims", [])
        suggestions = hallucination_feedback.get("suggestions", [])
        
        logger.debug(f"[SYNTHESIS] Problematic claims to avoid: {problematic_claims}")
        logger.debug(f"[SYNTHESIS] Improvement suggestions: {suggestions}")
        
        # 보수적인 프롬프트 생성
        corrective_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""CRITICAL: This is a RETRY due to hallucination concerns in the previous attempt.

PREVIOUS ISSUES:
- Hallucination score: {hallucination_feedback.get('score', 0):.2f}
- Problematic claims that MUST BE AVOIDED:
{chr(10).join(f'  ✗ {claim}' for claim in problematic_claims) if problematic_claims else '  None identified'}

- Supported claims that CAN BE KEPT:
{chr(10).join(f'  ✓ {claim}' for claim in supported_claims) if supported_claims else '  None identified'}

- Improvement suggestions:
{chr(10).join(f'  → {suggestion}' for suggestion in suggestions) if suggestions else '  None provided'}

STRICT CORRECTIVE GUIDELINES:
1. BE EXTREMELY CONSERVATIVE - only state what is EXPLICITLY written in documents
2. DO NOT make any of the problematic claims listed above
3. Include reference numbers [1], [2], etc. for EVERY factual statement
4. If uncertain about ANY detail, explicitly state "문서에 명시되지 않음" or "not specified in documents"
5. Prioritize accuracy over completeness - it's better to provide less information that is certain
6. Use direct quotes when possible, with clear attribution using reference numbers
7. Clearly distinguish between explicit information and any inferences
8. Include a complete References section at the end with all cited documents

ORIGINAL GUIDELINES (with emphasis on accuracy):
{self.synthesis_prompt.messages[0].prompt.template}"""),
            ("human", """Query: {query}

Retrieved Documents:
{documents}

Generate a CORRECTED answer that avoids all hallucination issues.
Be conservative and cite sources explicitly.""")
        ])
        
        # 더 낮은 temperature 사용 (보수적 생성)
        conservative_llm = ChatOpenAI(
            model=self.llm.model_name,
            temperature=0.1,  # 매우 낮은 temperature
            openai_api_key=self.llm.openai_api_key
        )
        
        # 구조화된 출력으로 답변 생성
        structured_llm = conservative_llm.with_structured_output(SynthesisResult)
        
        # 문서 포맷팅
        formatted_docs = self._format_documents(documents)
        
        try:
            result = await structured_llm.ainvoke(
                corrective_prompt.format_messages(
                    query=query,
                    documents=formatted_docs
                )
            )
            logger.info(f"[SYNTHESIS] Corrective answer generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Corrective generation failed: {str(e)}")
            # Fallback to original method
            return await self._generate_answer_with_fallback(query, documents)
    
    async def _generate_improved_answer(self, query: str, documents: List[Document],
                                       quality_feedback: Dict[str, Any],
                                       metadata: Dict[str, Any]) -> SynthesisResult:
        """
        품질 체크 실패 시 향상된 답변 생성
        
        Args:
            query: 사용자 쿼리
            documents: 검색된 문서들
            quality_feedback: 품질 평가 피드백
            metadata: 추가 메타데이터
            
        Returns:
            품질이 향상된 답변 결과
        """
        logger.info(f"[SYNTHESIS] Generating improved answer based on quality feedback")
        
        # 품질 평가 상세 정보 추출
        grade_meta = metadata.get("answer_grade", {})
        missing_aspects = grade_meta.get("missing_aspects", [])
        suggestions = quality_feedback.get("suggestions", [])
        strengths = grade_meta.get("strengths", [])
        
        # 점수별 개선 영역 파악
        completeness = grade_meta.get("completeness", 0)
        relevance = grade_meta.get("relevance", 0)
        clarity = grade_meta.get("clarity", 0)
        usefulness = grade_meta.get("usefulness", 0)
        
        logger.debug(f"[SYNTHESIS] Quality scores - C:{completeness:.2f} R:{relevance:.2f} Cl:{clarity:.2f} U:{usefulness:.2f}")
        logger.debug(f"[SYNTHESIS] Missing aspects: {missing_aspects}")
        logger.debug(f"[SYNTHESIS] Improvement suggestions: {suggestions}")
        
        # 품질 개선 프롬프트 생성
        improvement_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""IMPORTANT: This is a RETRY to improve answer quality based on evaluation feedback.

PREVIOUS QUALITY ASSESSMENT:
- Overall score: {quality_feedback.get('score', 0):.2f}
- Completeness: {completeness:.2f} (35% weight)
- Relevance: {relevance:.2f} (30% weight)  
- Clarity: {clarity:.2f} (20% weight)
- Usefulness: {usefulness:.2f} (15% weight)

MISSING ASPECTS TO ADDRESS:
{chr(10).join(f'  ✓ {aspect}' for aspect in missing_aspects) if missing_aspects else '  None identified'}

IMPROVEMENT SUGGESTIONS TO IMPLEMENT:
{chr(10).join(f'  → {suggestion}' for suggestion in suggestions) if suggestions else '  None provided'}

STRENGTHS TO MAINTAIN:
{chr(10).join(f'  • {strength}' for strength in strengths) if strengths else '  None identified'}

QUALITY IMPROVEMENT GUIDELINES:
1. COMPLETENESS: Address ALL missing aspects listed above
2. STRUCTURE: Organize answer with clear sections and formatting
   - Use headings for major topics
   - Use bullet points for lists
   - Use numbered steps for procedures
3. SPECIFICITY: Include concrete details
   - Exact specifications and numbers
   - Step-by-step procedures
   - Required tools and materials
   - Time estimates
4. USEFULNESS: Make the answer actionable
   - Clear instructions
   - Practical guidance
   - Safety warnings and cautions
5. CLARITY: Use clear, concise language
   - Define technical terms
   - Avoid ambiguity
   - Logical flow from general to specific

For vehicle manual queries, ensure you include:
- Safety warnings and precautions
- Required tools and materials
- Step-by-step procedures
- Time estimates
- Maintenance schedules if relevant
- Part numbers or specifications
- Troubleshooting tips if applicable
- Proper citations using reference numbers [1], [2], etc.
- Complete References section at the end

ORIGINAL GUIDELINES (with emphasis on completeness):
{self.synthesis_prompt.messages[0].prompt.template}"""),
            ("human", """Query: {query}

Retrieved Documents:
{documents}

Generate an IMPROVED answer that addresses all feedback.
Focus on completeness, structure, and usefulness.""")
        ])
        
        # 구조화된 출력으로 답변 생성
        structured_llm = self.llm.with_structured_output(SynthesisResult)
        
        # 문서 포맷팅
        formatted_docs = self._format_documents(documents)
        
        try:
            result = await structured_llm.ainvoke(
                improvement_prompt.format_messages(
                    query=query,
                    documents=formatted_docs
                )
            )
            logger.info(f"[SYNTHESIS] Improved answer generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Improved generation failed: {str(e)}")
            # Fallback to original method
            return await self._generate_answer_with_fallback(query, documents)