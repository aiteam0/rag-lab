"""
Synthesis Node
검색된 문서들을 바탕으로 답변을 생성하는 노드
"""

import os
import logging
import time
import random
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv


from workflow.state import MVPWorkflowState

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class PageImageInfo(BaseModel):
    """페이지 이미지 정보"""
    path: str = Field(description="Image file path")
    page: int = Field(description="Page number")
    source: str = Field(description="Source document name")

class EntityReference(BaseModel):
    """Entity information that was referenced in the answer"""
    entity_type: str = Field(description="Type: 똑딱이, table, or figure")
    title: Optional[str] = Field(description="Entity title if available")
    details: Optional[str] = Field(description="Entity details or description")
    source_doc: str = Field(description="Source document reference [1], [2], etc.")

class SynthesisResult(BaseModel):
    """답변 생성 결과"""
    answer: str = Field(description="Generated answer with inline citations [1], [2], etc. MUST end with References table and page images if available")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    sources_used: List[str] = Field(description="List of source references used in format: '[1]', '[2]', etc.")
    key_points: List[str] = Field(description="Key points extracted from documents")
    references_table: str = Field(description="MANDATORY References table in format: | 참조번호 | 문서명 | 페이지 | 내용 요약 |")
    page_images: Optional[List[PageImageInfo]] = Field(default=None, description="Page images from referenced documents")
    human_feedback_used: Optional[List[str]] = Field(default=None, description="List of human feedback that was incorporated into the answer")
    entity_references: Optional[List[EntityReference]] = Field(default=None, description="Structured entity information (똑딱이/table/figure) referenced in answer")
    warnings: Optional[List[str]] = Field(default=None, description="Any warnings or cautions extracted from documents")


class SynthesisNode:
    """검색된 문서를 기반으로 답변을 생성하는 노드"""
    
    def __init__(self):
        """초기화"""
        # ChatOpenAI 인스턴스 직접 생성
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,  # 더 일관된 답변을 위해 낮은 temperature
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 답변 생성 프롬프트
        self.synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert assistant for an automobile manufacturing RAG system.
Your task is to generate comprehensive and accurate answers based on the retrieved documents.

CRITICAL - Information Priority Hierarchy:
1. **HIGHEST PRIORITY - Human Verified Content**: If a document has "Human Verified" information, this is the ground truth and should be used as the primary source
2. **HIGH PRIORITY - Structured Entity Data**: 
   - **PPT Embedded Documents (똑딱이)**: Special document type with structured metadata from PPT presentations
   - **Tables**: Structured tabular data with titles, details, and keywords
   - **Figures**: Visual information with descriptions and contextual data
3. **STANDARD PRIORITY - Document Content**: Regular document text is the baseline information source

Guidelines:
1. Base your answer ONLY on the provided documents
2. When human feedback exists, prioritize it over other sources
3. When entity information exists (tables/figures/똑딱이), use the structured data to provide precise details
4. **CRITICAL - 똑딱이 Entity Mention**: 
   - When a document has entity type "똑딱이", ALWAYS mention it's a "PPT 삽입 문서" or "PPT Embedded Document"
   - Include the document title from entity metadata when available
   - Mention that this is a specially structured document from PPT presentations
   - Example: "이 정보는 'PPT 삽입 문서(똑딱이)'인 [제목]에서 확인할 수 있습니다"
5. If information is not in the documents, say so clearly
6. Cite sources using reference numbers [1], [2], etc. in the main text
7. Structure your answer clearly with proper formatting
8. **CRITICAL: For Korean documents, preserve the EXACT original terms and expressions**
   - Use original Korean terms exactly as written
   - Maintain parenthetical expressions as-is
   - Do NOT paraphrase or reword key terms from the source documents
9. Include specific details like numbers, procedures, and specifications
10. If there are conflicting information, human feedback takes precedence
11. Use the same reference number for the same document throughout the answer
12. Place reference numbers immediately after the relevant statement
13. When quoting or referencing policy terms, use the exact wording from the source

Page Image Display Guidelines:
14. **IMPORTANT**: If retrieved documents have page images (page_image_path in metadata):
    - Collect all unique page images from cited documents
    - Display them at the END of your answer in a dedicated section
    - Group by source document and order by page number
    - Format: ![Source Page X](path) for markdown rendering
14. Page Image Section Format:
    ```
    ## 참조 페이지 이미지 (Referenced Page Images)
    
    ### {{source_name}}
    ![Page 1](data/images/filename-page-1.png)
    ![Page 3](data/images/filename-page-3.png)
    
    ### {{another_source}}
    ![Page 2](data/images/another-page-2.png)
    ```

Answer Structure:
- Start with a direct answer to the question
- Provide supporting details from documents with inline citations [1], [2]
- Include relevant warnings or cautions if mentioned
- **NEW**: Add "참조 페이지 이미지 (Referenced Page Images)" section if page images exist
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

Generate a comprehensive response with the following structure:
1. answer: Comprehensive answer with inline citations [1], [2], etc.
2. confidence: Your confidence score (0.0-1.0)
3. sources_used: List like ['[1]', '[2]', '[3]'] for all cited documents
4. key_points: Main points extracted from documents
5. references_table: MANDATORY markdown table with source information

Extract source filename and page from each document's metadata for proper references.""")
        ])
        
        # 문서 포맷팅 템플릿
        self.document_formatter_prompt = """
[{idx}] Document Reference:
- Source: {source}
- Page: {page}
- Category: {category}
- Content: {content}
{caption}
{entity_info}
{human_feedback}
{page_image_note}
---
Note: Use [{idx}] when citing this document in your answer.
"""
    
    def _invoke_with_retry(self, structured_llm, messages, max_retries=3):
        """
        LLM 호출에 exponential backoff retry 적용
        
        Args:
            structured_llm: with_structured_output()로 래핑된 LLM 인스턴스
            messages: 프롬프트 메시지
            max_retries: 최대 재시도 횟수 (기본값: 3)
            
        Returns:
            LLM 응답 결과
            
        Raises:
            Exception: 최대 재시도 후에도 실패한 경우
        """
        for attempt in range(max_retries + 1):  # 0부터 max_retries까지
            try:
                logger.info(f"[SYNTHESIS] LLM invoke attempt {attempt + 1}/{max_retries + 1}")
                result = structured_llm.invoke(messages)
                logger.info(f"[SYNTHESIS] LLM invoke succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # OpenAI API 서버 에러인지 확인
                is_server_error = any(phrase in error_msg for phrase in [
                    "server had an error",
                    "internal server error", 
                    "service unavailable",
                    "timeout",
                    "connection error",
                    "temporarily unavailable"
                ])
                
                if attempt == max_retries:
                    # 최종 시도에서 실패
                    logger.error(f"[SYNTHESIS] LLM invoke failed after {max_retries + 1} attempts: {str(e)}")
                    raise e
                
                if is_server_error:
                    # 서버 에러는 재시도
                    wait_time = (2 ** attempt) + random.uniform(0, 1)  # 1s, 2s, 4s + jitter
                    logger.warning(f"[SYNTHESIS] Server error detected (attempt {attempt + 1}): {str(e)}")
                    logger.info(f"[SYNTHESIS] Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                else:
                    # 서버 에러가 아닌 경우 즉시 실패
                    logger.error(f"[SYNTHESIS] Non-server error, not retrying: {str(e)}")
                    raise e
    
    def _format_entity_info(self, metadata: dict) -> str:
        """
        Entity 정보를 적절한 형식으로 포맷팅 (타입 안전성 보장)
        
        Args:
            metadata: 문서 메타데이터
            
        Returns:
            포맷팅된 entity 정보
        """
        entity = metadata.get("entity")
        if not entity:
            return ""
        
        # entity가 dictionary가 아닌 경우 안전하게 처리
        if not isinstance(entity, dict):
            # entity가 string이거나 다른 타입인 경우 기본 정보만 표시
            return f"- Entity Info: {str(entity)}\n"
        
        category = metadata.get("category", "")
        entity_type = entity.get("type", "")
        
        # '똑딱이' 타입인 경우: PPT 삽입 문서 정보 제공
        if entity_type == "똑딱이":
            entity_text = "- PPT Embedded Document (똑딱이):\n"
            title = entity.get("title")
            if title and isinstance(title, str):
                entity_text += f"  Title: {title}\n"
            details = entity.get("details")
            if details and isinstance(details, str):
                entity_text += f"  Details: {details}\n"
            keywords = entity.get("keywords")
            if keywords and isinstance(keywords, list):
                entity_text += f"  Keywords: {', '.join(str(k) for k in keywords)}\n"
            hypothetical_questions = entity.get("hypothetical_questions")
            if hypothetical_questions and isinstance(hypothetical_questions, list):
                # 최대 3개의 질문만 표시
                questions_to_show = hypothetical_questions[:3]
                entity_text += f"  Can Answer: {'; '.join(str(q) for q in questions_to_show)}\n"
            return entity_text.rstrip()
        
        # 테이블인 경우: 구조화된 정보 제공
        elif category == "table" and entity:
            entity_text = "- Table: "
            title = entity.get("title")
            if title and isinstance(title, str):
                entity_text += f"{title}\n"
            details = entity.get("details")
            if details and isinstance(details, str):
                entity_text += f"  Details: {details}\n"
            keywords = entity.get("keywords")
            if keywords and isinstance(keywords, list):
                entity_text += f"  Keywords: {', '.join(str(k) for k in keywords)}\n"
            return entity_text.rstrip()
        
        # 그림인 경우: 설명 포함
        elif category == "figure" and entity:
            entity_text = "- Figure: "
            title = entity.get("title")
            if title and isinstance(title, str):
                entity_text += f"{title}\n"
            details = entity.get("details")
            if details and isinstance(details, str):
                entity_text += f"  Description: {details}\n"
            return entity_text.rstrip()
        
        return ""
    
    def _collect_page_images(self, documents: List[Document], sources_used: List[str] = None) -> List[Dict[str, Any]]:
        """
        문서들에서 유니크한 페이지 이미지 수집
        
        Args:
            documents: 검색된 문서 리스트
            sources_used: 실제 인용된 문서 참조 번호 (예: ['[1]', '[2]'])
            
        Returns:
            페이지 이미지 정보를 담은 딕셔너리 리스트
        """
        # sources_used가 제공되면 해당 문서만 필터링
        if sources_used:
            try:
                # '[1]', '[2]' 형식에서 인덱스 추출 (1-based를 0-based로 변환)
                used_indices = []
                for source in sources_used:
                    # '[1]' -> 1 -> 0 (인덱스)
                    idx = int(source.strip('[]')) - 1
                    if 0 <= idx < len(documents):
                        used_indices.append(idx)
                
                # 인용된 인덱스의 문서만 사용
                filtered_documents = [documents[i] for i in used_indices]
                logger.info(f"[SYNTHESIS] Filtering page images: {len(documents)} docs → {len(filtered_documents)} cited docs")
            except (ValueError, IndexError) as e:
                logger.warning(f"[SYNTHESIS] Error parsing sources_used: {e}, using all documents")
                filtered_documents = documents
        else:
            filtered_documents = documents
        
        page_images = []
        seen_paths = set()
        
        for doc in filtered_documents:
            if not isinstance(doc, Document):
                continue
                
            metadata = doc.metadata or {}
            page_image_path = metadata.get("page_image_path", "")
            
            # 유효한 경로이고 중복되지 않은 경우만 추가
            if page_image_path and page_image_path not in seen_paths:
                seen_paths.add(page_image_path)
                
                # source 파일명 추출 (표시용)
                source = metadata.get("source", "")
                source_name = os.path.basename(source) if source else "Unknown"
                
                page_images.append({
                    "path": page_image_path,
                    "page": metadata.get("page", 0),
                    "source": source_name,
                    "category": metadata.get("category", "")
                })
        
        # 페이지 번호순으로 정렬
        page_images.sort(key=lambda x: (x["source"], x["page"]))
        
        return page_images
    
    def _collect_entity_references(self, documents: List[Document], doc_idx_map: Dict[int, str]) -> List[EntityReference]:
        """
        문서들에서 entity 정보 수집 (똑딱이, table, figure)
        
        Args:
            documents: 검색된 문서 리스트
            doc_idx_map: 문서 인덱스 to 참조번호 매핑 (e.g., {0: '[1]', 1: '[2]'})
            
        Returns:
            EntityReference 리스트
        """
        entity_refs = []
        
        for idx, doc in enumerate(documents):
            if not isinstance(doc, Document):
                continue
                
            metadata = doc.metadata or {}
            entity = metadata.get("entity")
            category = metadata.get("category", "")
            
            # entity가 존재하고 dictionary인 경우만 처리
            if entity and isinstance(entity, dict):
                entity_type = entity.get("type", "")
                
                # 똑딱이, table, figure 중 하나인 경우
                if entity_type == "똑딱이" or category in ["table", "figure"]:
                    ref = EntityReference(
                        entity_type=entity_type if entity_type == "똑딱이" else category,
                        title=entity.get("title") if isinstance(entity.get("title"), str) else None,
                        details=entity.get("details") if isinstance(entity.get("details"), str) else None,
                        source_doc=doc_idx_map.get(idx, f"[{idx+1}]")
                    )
                    entity_refs.append(ref)
        
        return entity_refs
    
    def _collect_human_feedback(self, documents: List[Document]) -> List[str]:
        """
        문서들에서 human feedback 수집
        
        Args:
            documents: 검색된 문서 리스트
            
        Returns:
            Human feedback 문자열 리스트
        """
        feedback_list = []
        
        for doc in documents:
            if not isinstance(doc, Document):
                continue
                
            metadata = doc.metadata or {}
            human_feedback = metadata.get("human_feedback")
            
            # human_feedback가 존재하고 비어있지 않은 경우
            if human_feedback and isinstance(human_feedback, str) and human_feedback.strip():
                feedback_list.append(human_feedback.strip())
        
        return feedback_list
    
    def _extract_warnings(self, documents: List[Document]) -> List[str]:
        """
        문서 내용에서 경고/주의사항 추출
        
        Args:
            documents: 검색된 문서 리스트
            
        Returns:
            경고/주의사항 문자열 리스트
        """
        warnings = []
        warning_keywords = ["경고", "주의", "위험", "warning", "caution", "danger", "주의사항", "안전"]
        
        for doc in documents:
            if not isinstance(doc, Document):
                continue
                
            content = doc.page_content.lower()
            
            # 경고 키워드가 포함된 문장 찾기
            for keyword in warning_keywords:
                if keyword in content.lower():
                    # 간단한 휴리스틱: 키워드 주변 문장 추출
                    sentences = doc.page_content.split('.')
                    for sentence in sentences:
                        if keyword in sentence.lower() and len(sentence.strip()) > 10:
                            warning_text = sentence.strip()
                            if warning_text not in warnings:  # 중복 제거
                                warnings.append(warning_text)
                            break  # 한 문서에서 하나의 경고만 추출
        
        return warnings[:5]  # 최대 5개까지만 반환 (너무 많은 경고 방지)
    
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
                    logger.warning(f"[SYNTHESIS] Failed to parse document string at index {idx}")
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
                logger.warning(f"[SYNTHESIS] Invalid document format at index {idx}: {type(doc)}")
                continue
            
            metadata = doc.metadata
            
            # 캡션이 있으면 추가
            caption_text = ""
            if metadata.get("caption"):
                caption_text = f"- Caption: {metadata['caption']}"
            
            # Entity 정보 포맷팅
            entity_info_text = self._format_entity_info(metadata)
            
            # Human feedback이 있으면 추가 (타입 안전성 보장)
            human_feedback_text = ""
            human_feedback = metadata.get("human_feedback")
            if human_feedback and isinstance(human_feedback, str) and human_feedback.strip():
                human_feedback_text = f"- Human Verified: {human_feedback}"
            
            # 페이지 이미지 경로가 있으면 노트 추가
            page_image_path = metadata.get("page_image_path", "")
            page_image_note = ""
            if page_image_path and isinstance(page_image_path, str) and page_image_path.strip():
                page_image_note = f"- Page Image Available: {page_image_path}"
            
            # 문서 내용 (truncate가 True일 때만 축약)
            content = doc.page_content[:500] if truncate else doc.page_content
            
            formatted_doc = self.document_formatter_prompt.format(
                idx=idx,
                source=metadata.get("source", "Unknown"),
                page=metadata.get("page", "N/A"),
                category=metadata.get("category", "Unknown"),
                content=content,
                caption=caption_text,
                entity_info=entity_info_text,
                human_feedback=human_feedback_text,
                page_image_note=page_image_note
            )
            
            # "똑딱이" entity type을 더 명확하게 강조
            if entity_info_text and "똑딱이" in entity_info_text:
                # PPT Embedded Document를 시각적으로 강조
                formatted_doc = formatted_doc.replace(
                    "- PPT Embedded Document (똑딱이):",
                    "- **[SPECIAL] PPT Embedded Document (똑딱이)**:"
                )
                # 문서 시작 부분에 특별 표시 추가
                formatted_doc = f"[📌 PPT 삽입 문서]\n{formatted_doc}"
            
            formatted_docs.append(formatted_doc)
        
        return "\n".join(formatted_docs)
    
    def _generate_answer_with_fallback(
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
            
            structured_llm = self.llm.with_structured_output(
                SynthesisResult
            )
            
            result = self._invoke_with_retry(
                structured_llm,
                self.synthesis_prompt.format_messages(
                    query=query,
                    documents=formatted_docs
                )
            )
            
            # sources_used를 기반으로 인용된 문서의 페이지 이미지만 수집
            page_images = self._collect_page_images(documents, sources_used=result.sources_used)
            
            # 페이지 이미지를 답변에 추가 및 page_images 필드 설정
            if page_images:
                # PageImageInfo 객체 리스트 생성
                page_image_infos = []
                for img in page_images:
                    page_image_infos.append(PageImageInfo(
                        path=img['path'],
                        page=img['page'],
                        source=img['source']
                    ))
                result.page_images = page_image_infos
                
                # 답변 텍스트에 접을 수 있는 이미지 섹션 추가
                image_count = len(page_images)
                image_section = "\n\n## 📎 참조 페이지 이미지\n"
                image_section += f"### 📄 페이지 이미지 ({image_count}개)\n\n"
                
                current_source = None
                for img in page_images:
                    if img['source'] != current_source:
                        current_source = img['source']
                        image_section += f"\n### 📄 {current_source}\n"
                    
                    image_section += f"![Page {img['page']}]({img['path']})\n"
                
                # 이미지 섹션 완료
                
                # 답변에 이미지 섹션 추가
                result.answer = result.answer + image_section
                logger.info(f"[SYNTHESIS] Added {len(page_images)} page images from cited documents to answer")
            
            # 새로운 필드 수집 및 설정
            # 1. Human feedback 수집
            human_feedback = self._collect_human_feedback(documents)
            if human_feedback:
                result.human_feedback_used = human_feedback
                logger.info(f"[SYNTHESIS] Found {len(human_feedback)} human feedback entries")
            
            # 2. Entity references 수집
            # 문서 인덱스 to 참조번호 매핑 생성
            doc_idx_map = {}
            for idx in range(len(documents)):
                doc_idx_map[idx] = f"[{idx+1}]"
            
            entity_refs = self._collect_entity_references(documents, doc_idx_map)
            if entity_refs:
                result.entity_references = entity_refs
                logger.info(f"[SYNTHESIS] Found {len(entity_refs)} entity references")
                for ref in entity_refs[:3]:  # 처음 3개만 로깅
                    logger.info(f"[SYNTHESIS]   - {ref.entity_type}: {ref.title}")
            
            # 3. 경고사항 추출
            warnings = self._extract_warnings(documents)
            if warnings:
                result.warnings = warnings
                logger.info(f"[SYNTHESIS] Extracted {len(warnings)} warnings")
            
            # 생성된 답변 로깅
            logger.info(f"[SYNTHESIS] === Generated Answer Summary ===")
            logger.info(f"[SYNTHESIS] Query: {query}")
            logger.info(f"[SYNTHESIS] Answer Length: {len(result.answer)} chars")
            logger.info(f"[SYNTHESIS] Confidence: {result.confidence:.2f}")
            logger.info(f"[SYNTHESIS] Sources Used: {result.sources_used}")
            logger.info(f"[SYNTHESIS] Key Points Count: {len(result.key_points)}")
            if result.key_points:
                logger.info(f"[SYNTHESIS] First Key Point: {result.key_points[0]}")
            logger.info(f"[SYNTHESIS] Full Answer:")
            logger.info(f"[SYNTHESIS] {result.answer}")
            logger.info(f"[SYNTHESIS] === End of Answer ===")
            
            return result
            
        except Exception as e:
            # Token 제한 에러인 경우 fallback
            if "maximum context length" in str(e).lower() or "token" in str(e).lower():
                print(f"Token limit exceeded, falling back to truncated documents")
                
                # 문서 축약하여 재시도
                formatted_docs = self._format_documents(documents, truncate=True)
                
                structured_llm = self.llm.with_structured_output(
                    SynthesisResult
                )
                
                result = self._invoke_with_retry(
                    structured_llm,
                    self.synthesis_prompt.format_messages(
                        query=query,
                        documents=formatted_docs
                    )
                )
                
                # Fallback에서도 sources_used를 기반으로 인용된 문서의 페이지 이미지만 수집
                page_images = self._collect_page_images(documents, sources_used=result.sources_used)
                
                if page_images:
                    # PageImageInfo 객체 리스트 생성
                    page_image_infos = []
                    for img in page_images:
                        page_image_infos.append(PageImageInfo(
                            path=img['path'],
                            page=img['page'],
                            source=img['source']
                        ))
                    result.page_images = page_image_infos
                    
                    # 답변 텍스트에 접을 수 있는 이미지 섹션 추가
                    image_count = len(page_images)
                    image_section = "\n\n## 📎 참조 페이지 이미지\n"
                    image_section += f"### 📄 페이지 이미지 ({image_count}개)\n\n"
                    
                    current_source = None
                    for img in page_images:
                        if img['source'] != current_source:
                            current_source = img['source']
                            image_section += f"\n### 📄 {current_source}\n"
                        
                        image_section += f"![Page {img['page']}]({img['path']})\n"
                    
                    # 이미지 섹션 완료
                    
                    # 답변에 이미지 섹션 추가
                    result.answer = result.answer + image_section
                    logger.info(f"[SYNTHESIS] Added {len(page_images)} page images from cited documents to answer (fallback)")
                
                # Fallback에서도 새로운 필드 수집 및 설정
                # 1. Human feedback 수집
                human_feedback = self._collect_human_feedback(documents)
                if human_feedback:
                    result.human_feedback_used = human_feedback
                    logger.info(f"[SYNTHESIS-FALLBACK] Found {len(human_feedback)} human feedback entries")
                
                # 2. Entity references 수집
                doc_idx_map = {}
                for idx in range(len(documents)):
                    doc_idx_map[idx] = f"[{idx+1}]"
                
                entity_refs = self._collect_entity_references(documents, doc_idx_map)
                if entity_refs:
                    result.entity_references = entity_refs
                    logger.info(f"[SYNTHESIS-FALLBACK] Found {len(entity_refs)} entity references")
                
                # 3. 경고사항 추출
                warnings = self._extract_warnings(documents)
                if warnings:
                    result.warnings = warnings
                    logger.info(f"[SYNTHESIS-FALLBACK] Extracted {len(warnings)} warnings")
                
                # Fallback 시에도 답변 로깅
                logger.warning(f"[SYNTHESIS] Generated answer using truncated documents (fallback)")
                logger.info(f"[SYNTHESIS] Answer Length: {len(result.answer)} chars")
                logger.info(f"[SYNTHESIS] Confidence: {result.confidence:.2f}")
                
                return result
            else:
                # 다른 에러는 그대로 전파
                raise e
    
    def __call__(self, state: MVPWorkflowState) -> Dict[str, Any]:
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
                    synthesis_result = self._generate_corrective_answer(
                        query, documents, hallucination_feedback, state.get("metadata", {})
                    )
                # 품질 체크 실패로 인한 재시도
                elif is_retry_from_quality:
                    logger.info(f"[SYNTHESIS] Using improved generation due to quality concerns")
                    logger.debug(f"[SYNTHESIS] Quality score: {quality_feedback.get('score', 0)}")
                    synthesis_result = self._generate_improved_answer(
                        query, documents, quality_feedback, state.get("metadata", {})
                    )
            else:
                # 첫 번째 시도
                logger.info(f"[SYNTHESIS] Generating answer using {len(documents)} documents...")
                synthesis_result = self._generate_answer_with_fallback(query, documents)
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
            
            # 메시지 생성 - 통합 및 간소화
            messages = []
            
            # 재시도 정보가 있는 경우에만 표시
            max_retries = int(os.getenv("CRAG_MAX_RETRIES", "3"))
            if retry_count > 0:
                retry_reason = ""
                if is_retry_from_hallucination:
                    retry_reason = "환각 검증 실패"
                elif is_retry_from_quality:
                    retry_reason = "품질 기준 미달"
                messages.append(
                    AIMessage(content=f"🔄 답변 재생성 중... (시도 {retry_count+1}/{max_retries}, 사유: {retry_reason})")
                )
            
            # 통합된 답변 생성 메시지
            messages.append(
                AIMessage(content=f"✍️ {len(documents)}개 문서에서 답변 생성 중... (신뢰도: {synthesis_result.confidence:.0%})")
            )
            
            # 서브태스크 업데이트
            if subtasks and current_idx < len(subtasks):
                subtasks[current_idx]["answer"] = final_answer
                subtasks[current_idx]["status"] = "synthesized"
                subtask_id = subtasks[current_idx].get("id", "no-id")[:8]
                logger.info(f"[SYNTHESIS] Updated subtask [{subtask_id}] status: 'retrieved' -> 'synthesized'")
                
                result = {
                    "messages": messages,  # 메시지 추가
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
                    "messages": messages,  # 메시지 추가
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
        return self.__call__(state)
    
    def _generate_corrective_answer(self, query: str, documents: List[Document], 
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
        # 문제가 된 주장들 포맷팅
        problematic_claims_text = "\n".join(f'  ✗ {claim}' for claim in problematic_claims) if problematic_claims else '  None identified'
        supported_claims_text = "\n".join(f'  ✓ {claim}' for claim in supported_claims) if supported_claims else '  None identified'
        suggestions_text = "\n".join(f'  → {suggestion}' for suggestion in suggestions) if suggestions else '  None provided'
        
        corrective_prompt = ChatPromptTemplate.from_messages([
            ("system", """CRITICAL: This is a RETRY due to hallucination concerns in the previous attempt.

PREVIOUS ISSUES:
- Hallucination score: {hallucination_score:.2f}
- Problematic claims that MUST BE AVOIDED:
{problematic_claims}

- Supported claims that CAN BE KEPT:
{supported_claims}

- Improvement suggestions:
{suggestions}

STRICT CORRECTIVE GUIDELINES:
1. BE EXTREMELY CONSERVATIVE - only state what is EXPLICITLY written in documents
2. DO NOT make any of the problematic claims listed above
3. Include reference numbers [1], [2], etc. for EVERY factual statement
4. IMPORTANT: When information is not available in documents, explicitly state:
   - "문서에 해당 정보가 없습니다" (Korean)
   - "This information is not available in the provided documents" (English)
5. Prioritize accuracy over completeness - it's better to provide less information that is certain
6. Use direct quotes when possible, with clear attribution using reference numbers
7. Clearly distinguish between:
   - What IS explicitly stated in documents (use: "문서에 따르면" or "According to the documents")
   - What is NOT in documents (use: "문서에 명시되지 않음" or "Not specified in documents")
   - What requires additional information (use: "추가 정보가 필요합니다" or "Additional information needed")
8. Include a complete References section at the end with all cited documents

ORIGINAL GUIDELINES (with emphasis on accuracy):
{template}""".format(
                hallucination_score=hallucination_feedback.get('score', 0),
                problematic_claims=problematic_claims_text,
                supported_claims=supported_claims_text,
                suggestions=suggestions_text,
                template=self.synthesis_prompt.messages[0].prompt.template
            )),
            ("human", """Query: {query}

Retrieved Documents:
{documents}

Generate a CORRECTED answer that avoids all hallucination issues.
Be conservative and cite sources explicitly.
Clearly state "문서에 정보가 없습니다" or "Information not available in documents" when relevant details are missing.""")
        ])
        
        # 더 낮은 temperature 사용 (보수적 생성)
        conservative_llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,  # 매우 낮은 temperature
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 구조화된 출력으로 답변 생성
        structured_llm = conservative_llm.with_structured_output(
            SynthesisResult
        )
        
        # 문서 포맷팅
        formatted_docs = self._format_documents(documents)
        
        try:
            result = self._invoke_with_retry(
                structured_llm,
                corrective_prompt.format_messages(
                    query=query,
                    documents=formatted_docs
                )
            )
            
            # sources_used를 기반으로 인용된 문서의 페이지 이미지만 수집
            page_images = self._collect_page_images(documents, sources_used=result.sources_used)
            
            # 페이지 이미지를 답변에 추가 및 page_images 필드 설정
            if page_images:
                # PageImageInfo 객체 리스트 생성
                page_image_infos = []
                for img in page_images:
                    page_image_infos.append(PageImageInfo(
                        path=img['path'],
                        page=img['page'],
                        source=img['source']
                    ))
                result.page_images = page_image_infos
                
                # 답변 텍스트에 접을 수 있는 이미지 섹션 추가
                image_count = len(page_images)
                image_section = "\n\n## 📎 참조 페이지 이미지\n"
                image_section += f"### 📄 페이지 이미지 ({image_count}개)\n\n"
                
                current_source = None
                for img in page_images:
                    if img['source'] != current_source:
                        current_source = img['source']
                        image_section += f"\n### 📄 {current_source}\n"
                    
                    image_section += f"![Page {img['page']}]({img['path']})\n"
                
                # 이미지 섹션 완료
                
                # 답변에 이미지 섹션 추가
                result.answer = result.answer + image_section
                logger.info(f"[SYNTHESIS] Added {len(page_images)} page images from cited documents to corrective answer")
            
            # 새로운 필드 수집 및 설정 (corrective answer에서도 동일하게)
            # 1. Human feedback 수집
            human_feedback = self._collect_human_feedback(documents)
            if human_feedback:
                result.human_feedback_used = human_feedback
                logger.info(f"[SYNTHESIS-CORRECTIVE] Found {len(human_feedback)} human feedback entries")
            
            # 2. Entity references 수집
            doc_idx_map = {}
            for idx in range(len(documents)):
                doc_idx_map[idx] = f"[{idx+1}]"
            
            entity_refs = self._collect_entity_references(documents, doc_idx_map)
            if entity_refs:
                result.entity_references = entity_refs
                logger.info(f"[SYNTHESIS-CORRECTIVE] Found {len(entity_refs)} entity references")
            
            # 3. 경고사항 추출
            warnings = self._extract_warnings(documents)
            if warnings:
                result.warnings = warnings
                logger.info(f"[SYNTHESIS-CORRECTIVE] Extracted {len(warnings)} warnings")
            
            logger.info(f"[SYNTHESIS] Corrective answer generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Corrective generation failed: {str(e)}")
            # Fallback to original method
            return self._generate_answer_with_fallback(query, documents)
    
    def _generate_improved_answer(self, query: str, documents: List[Document],
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
        missing_aspects_text = "\n".join(f'  ✓ {aspect}' for aspect in missing_aspects) if missing_aspects else '  None identified'
        suggestions_text = "\n".join(f'  → {suggestion}' for suggestion in suggestions) if suggestions else '  None provided'
        strengths_text = "\n".join(f'  • {strength}' for strength in strengths) if strengths else '  None identified'
        
        improvement_prompt = ChatPromptTemplate.from_messages([
            ("system", """IMPORTANT: This is a RETRY to improve answer quality based on evaluation feedback.

PREVIOUS QUALITY ASSESSMENT:
- Overall score: {score:.2f}
- Completeness: {completeness:.2f} (35% weight)
- Relevance: {relevance:.2f} (30% weight)  
- Clarity: {clarity:.2f} (20% weight)
- Usefulness: {usefulness:.2f} (15% weight)

MISSING ASPECTS TO ADDRESS:
{missing_aspects_text}

IMPROVEMENT SUGGESTIONS TO IMPLEMENT:
{suggestions_text}

STRENGTHS TO MAINTAIN:
{strengths_text}

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
{template}""".format(
                score=quality_feedback.get('score', 0),
                completeness=completeness,
                relevance=relevance,
                clarity=clarity,
                usefulness=usefulness,
                missing_aspects_text=missing_aspects_text,
                suggestions_text=suggestions_text,
                strengths_text=strengths_text,
                template=self.synthesis_prompt.messages[0].prompt.template
            )),
            ("human", """Query: {query}

Retrieved Documents:
{documents}

Generate an IMPROVED answer that addresses all feedback.
Focus on completeness, structure, and usefulness.""")
        ])
        
        # 구조화된 출력으로 답변 생성
        structured_llm = self.llm.with_structured_output(
            SynthesisResult
        )
        
        # 문서 포맷팅
        formatted_docs = self._format_documents(documents)
        
        try:
            result = self._invoke_with_retry(
                structured_llm,
                improvement_prompt.format_messages(
                    query=query,
                    documents=formatted_docs
                )
            )
            
            # sources_used를 기반으로 인용된 문서의 페이지 이미지만 수집
            page_images = self._collect_page_images(documents, sources_used=result.sources_used)
            
            # 페이지 이미지를 답변에 추가 및 page_images 필드 설정
            if page_images:
                # PageImageInfo 객체 리스트 생성
                page_image_infos = []
                for img in page_images:
                    page_image_infos.append(PageImageInfo(
                        path=img['path'],
                        page=img['page'],
                        source=img['source']
                    ))
                result.page_images = page_image_infos
                
                # 답변 텍스트에 접을 수 있는 이미지 섹션 추가
                image_count = len(page_images)
                image_section = "\n\n## 📎 참조 페이지 이미지\n"
                image_section += f"### 📄 페이지 이미지 ({image_count}개)\n\n"
                
                current_source = None
                for img in page_images:
                    if img['source'] != current_source:
                        current_source = img['source']
                        image_section += f"\n### 📄 {current_source}\n"
                    
                    image_section += f"![Page {img['page']}]({img['path']})\n"
                
                # 이미지 섹션 완료
                
                # 답변에 이미지 섹션 추가
                result.answer = result.answer + image_section
                logger.info(f"[SYNTHESIS] Added {len(page_images)} page images from cited documents to improved answer")
            
            # 새로운 필드 수집 및 설정 (improved answer에서도 동일하게)
            # 1. Human feedback 수집
            human_feedback = self._collect_human_feedback(documents)
            if human_feedback:
                result.human_feedback_used = human_feedback
                logger.info(f"[SYNTHESIS-IMPROVED] Found {len(human_feedback)} human feedback entries")
            
            # 2. Entity references 수집
            doc_idx_map = {}
            for idx in range(len(documents)):
                doc_idx_map[idx] = f"[{idx+1}]"
            
            entity_refs = self._collect_entity_references(documents, doc_idx_map)
            if entity_refs:
                result.entity_references = entity_refs
                logger.info(f"[SYNTHESIS-IMPROVED] Found {len(entity_refs)} entity references")
            
            # 3. 경고사항 추출
            warnings = self._extract_warnings(documents)
            if warnings:
                result.warnings = warnings
                logger.info(f"[SYNTHESIS-IMPROVED] Extracted {len(warnings)} warnings")
            
            logger.info(f"[SYNTHESIS] Improved answer generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Improved generation failed: {str(e)}")
            # Fallback to original method
            return self._generate_answer_with_fallback(query, documents)