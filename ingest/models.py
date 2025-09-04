"""
Simplified DDU Document Models for MVP
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# DDU 카테고리 정의
DDU_CATEGORIES = [
    "heading1",     # 제목 레벨 1
    "heading2",     # 제목 레벨 2  
    "heading3",     # 제목 레벨 3
    "paragraph",    # 일반 텍스트 단락
    "list",         # 리스트 항목
    "table",        # 테이블
    "figure",       # 그림/이미지
    "chart",        # 차트/그래프
    "equation",     # 수식
    "caption",      # 캡션
    "footnote",     # 각주
    "header",       # 페이지 헤더
    "footer",       # 페이지 푸터
    "reference"     # 참조문헌
]

# 텍스트 기반 카테고리
TEXT_CATEGORIES = [
    "heading1", "heading2", "heading3", 
    "paragraph", "list", "caption", 
    "footnote", "header", "footer", "reference"
]

# 이미지 기반 카테고리
IMAGE_CATEGORIES = ["image", "chart"]

# 테이블 카테고리
TABLE_CATEGORY = ["table"]


class EntityInfo(BaseModel):
    """Entity 정보 (image, table, 똑딱이)"""
    type: str = Field(description="Entity 타입: image, table, 똑딱이")
    title: Optional[str] = Field(None, description="Entity 제목")
    details: Optional[str] = Field(None, description="상세 설명")
    keywords: List[str] = Field(default_factory=list, description="관련 키워드")
    hypothetical_questions: List[str] = Field(
        default_factory=list, 
        description="답변 가능한 예상 질문들"
    )
    raw_output: Optional[str] = Field(None, description="LLM 원본 출력")


class DDUDocument(BaseModel):
    """간소화된 DDU 문서 모델 (MVP용)"""
    
    # 기본 식별자
    id: Optional[int] = Field(None, description="DB ID")
    
    # 핵심 메타데이터 (검색 필터용)
    source: str = Field(description="소스 파일명")
    page: Optional[int] = Field(None, description="페이지 번호")
    category: str = Field(description="DDU 카테고리")
    
    # 콘텐츠 필드
    page_content: Optional[str] = Field(None, description="원본 콘텐츠")
    translation_text: Optional[str] = Field(None, description="영어 번역")
    contextualize_text: Optional[str] = Field(None, description="한국어 컨텍스트")
    caption: Optional[str] = Field(None, description="캡션 (표/그림)")
    
    # 구조화 데이터
    entity: Optional[Dict[str, Any]] = Field(None, description="엔티티 정보")
    image_path: Optional[str] = Field(None, description="이미지 경로")
    
    # 추가 정보
    human_feedback: str = Field(default="", description="휴먼 피드백")
    created_at: Optional[datetime] = Field(None, description="생성 시간")
    updated_at: Optional[datetime] = Field(None, description="수정 시간")
    
    # 벡터 임베딩 (처리 후 추가)
    embedding_korean: Optional[List[float]] = Field(None, description="한국어 임베딩")
    embedding_english: Optional[List[float]] = Field(None, description="영어 임베딩")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "gv80_manual.pdf",
                "page": 10,
                "category": "paragraph",
                "page_content": "GV80은 제네시스의 첫 번째 SUV 모델입니다.",
                "translation_text": "The GV80 is Genesis's first SUV model.",
                "contextualize_text": "GV80 소개 - 제네시스 브랜드의 첫 SUV",
                "entity": None,
                "image_path": None
            }
        }
    
    def get_element_type(self) -> str:
        """요소 타입 반환 (text/image/table)"""
        if self.category in TEXT_CATEGORIES:
            return "text"
        elif self.category in IMAGE_CATEGORIES:
            return "image"
        elif self.category in TABLE_CATEGORY:
            return "table"
        else:
            return "unknown"
    
    def to_langchain_document(self) -> dict:
        """LangChain Document 형식으로 변환"""
        # 페이지 콘텐츠 결정
        if self.category in TEXT_CATEGORIES:
            content = self.page_content or ""
        else:
            content = self.contextualize_text or self.page_content or ""
        
        # 메타데이터 구성
        metadata = {
            "source": self.source,
            "page": self.page,
            "category": self.category,
            "id": self.id,
            "element_type": self.get_element_type(),
            "human_feedback": self.human_feedback
        }
        
        # 선택적 필드 추가
        if self.translation_text:
            metadata["translation_text"] = self.translation_text
        if self.contextualize_text:
            metadata["contextualize_text"] = self.contextualize_text
        if self.caption:
            metadata["caption"] = self.caption
        if self.entity:
            metadata["entity"] = self.entity
        if self.image_path:
            metadata["image_path"] = self.image_path
        
        return {
            "page_content": content,
            "metadata": metadata
        }
    
    def to_db_dict(self) -> dict:
        """데이터베이스 저장용 딕셔너리 변환"""
        data = {
            "source": self.source,
            "page": self.page,
            "category": self.category,
            "page_content": self.page_content,
            "translation_text": self.translation_text,
            "contextualize_text": self.contextualize_text,
            "caption": self.caption,
            "entity": self.entity,
            "image_path": self.image_path,
            "human_feedback": self.human_feedback
        }
        
        # 임베딩이 있으면 추가
        if self.embedding_korean:
            data["embedding_korean"] = self.embedding_korean
        if self.embedding_english:
            data["embedding_english"] = self.embedding_english
        
        return data