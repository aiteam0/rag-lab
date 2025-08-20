"""
MVP Search Filter Implementation
Simplified to 5 core fields for efficient filtering
"""

from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


class MVPSearchFilter(BaseModel):
    """MVP용 간소화된 검색 필터 (5개 필드만 사용)"""
    
    # 핵심 필터 필드
    categories: Optional[List[str]] = Field(
        None, 
        description="DDU 카테고리 필터 (예: ['paragraph', 'table', 'figure'])"
    )
    pages: Optional[List[int]] = Field(
        None,
        description="페이지 번호 필터 (예: [1, 2, 3])"
    )
    sources: Optional[List[str]] = Field(
        None,
        description="소스 파일 필터 (예: ['manual.pdf'])"
    )
    caption: Optional[str] = Field(
        None,
        description="캡션 텍스트 검색 (LIKE 검색)"
    )
    entity: Optional[Dict[str, Any]] = Field(
        None,
        description="엔티티 JSONB 필터 - type, title, keywords 등 검색"
    )
    
    def to_sql_where_asyncpg(self) -> Tuple[str, List[Any]]:
        """
        asyncpg용 SQL WHERE 절과 파라미터 리스트 생성
        
        Returns:
            (WHERE 절 문자열 with $1, $2..., 파라미터 리스트) 튜플
        """
        conditions = []
        params = []
        param_count = 0
        
        # 카테고리 필터
        if self.categories:
            param_count += 1
            conditions.append(f"category = ANY(${param_count})")
            params.append(self.categories)
        
        # 페이지 필터
        if self.pages:
            param_count += 1
            conditions.append(f"page = ANY(${param_count})")
            params.append(self.pages)
        
        # 소스 필터
        if self.sources:
            param_count += 1
            conditions.append(f"source = ANY(${param_count})")
            params.append(self.sources)
        
        # 캡션 검색 (부분 일치)
        if self.caption:
            param_count += 1
            conditions.append(f"caption ILIKE ${param_count}")
            params.append(f"%{self.caption}%")
        
        # Entity JSONB 필터
        if self.entity:
            entity_conditions = []
            
            # type 필드 검색
            if 'type' in self.entity:
                param_count += 1
                entity_conditions.append(f"entity->>'type' = ${param_count}")
                params.append(self.entity['type'])
            
            # title 필드 검색 (부분 일치)
            if 'title' in self.entity:
                param_count += 1
                entity_conditions.append(f"entity->>'title' ILIKE ${param_count}")
                params.append(f"%{self.entity['title']}%")
            
            # keywords 배열 검색
            if 'keywords' in self.entity:
                if isinstance(self.entity['keywords'], list):
                    param_count += 1
                    entity_conditions.append(f"entity->'keywords' ?| ${param_count}")
                    params.append(self.entity['keywords'])
                elif isinstance(self.entity['keywords'], str):
                    param_count += 1
                    entity_conditions.append(f"entity->'keywords' ? ${param_count}")
                    params.append(self.entity['keywords'])
            
            # details 필드 검색 (부분 일치)
            if 'details' in self.entity:
                param_count += 1
                entity_conditions.append(f"entity->>'details' ILIKE ${param_count}")
                params.append(f"%{self.entity['details']}%")
            
            # 모든 entity 관련 조건을 AND로 결합
            if entity_conditions:
                conditions.append(f"({' AND '.join(entity_conditions)})")
        
        # WHERE 절 생성
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        return where_clause, params
    
    def to_sql_where(self) -> Tuple[str, Dict[str, Any]]:
        """
        SQL WHERE 절과 파라미터 생성
        
        Returns:
            (WHERE 절 문자열, 파라미터 딕셔너리) 튜플
        """
        conditions = []
        params = {}
        
        # 카테고리 필터
        if self.categories:
            conditions.append("category = ANY(%(categories)s)")
            params['categories'] = self.categories
        
        # 페이지 필터
        if self.pages:
            conditions.append("page = ANY(%(pages)s)")
            params['pages'] = self.pages
        
        # 소스 필터
        if self.sources:
            conditions.append("source = ANY(%(sources)s)")
            params['sources'] = self.sources
        
        # 캡션 검색 (부분 일치)
        if self.caption:
            conditions.append("caption ILIKE %(caption)s")
            params['caption'] = f"%{self.caption}%"
        
        # Entity JSONB 필터
        if self.entity:
            entity_conditions = []
            
            # type 필드 검색
            if 'type' in self.entity:
                entity_conditions.append("entity->>'type' = %(entity_type)s")
                params['entity_type'] = self.entity['type']
            
            # title 필드 검색 (부분 일치)
            if 'title' in self.entity:
                entity_conditions.append("entity->>'title' ILIKE %(entity_title)s")
                params['entity_title'] = f"%{self.entity['title']}%"
            
            # keywords 배열 검색
            if 'keywords' in self.entity:
                if isinstance(self.entity['keywords'], list):
                    # 배열의 각 키워드 중 하나라도 포함
                    entity_conditions.append("entity->'keywords' ?| %(entity_keywords)s")
                    params['entity_keywords'] = self.entity['keywords']
                elif isinstance(self.entity['keywords'], str):
                    # 단일 키워드 검색
                    entity_conditions.append("entity->'keywords' ? %(entity_keyword)s")
                    params['entity_keyword'] = self.entity['keywords']
            
            # details 필드 검색 (부분 일치)
            if 'details' in self.entity:
                entity_conditions.append("entity->>'details' ILIKE %(entity_details)s")
                params['entity_details'] = f"%{self.entity['details']}%"
            
            # 모든 entity 관련 조건을 AND로 결합
            if entity_conditions:
                conditions.append(f"({' AND '.join(entity_conditions)})")
        
        # WHERE 절 생성
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        return where_clause, params
    
    def is_empty(self) -> bool:
        """필터가 비어있는지 확인"""
        return not any([
            self.categories,
            self.pages,
            self.sources,
            self.caption,
            self.entity
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """필터를 딕셔너리로 변환 (None 값 제외)"""
        result = {}
        
        if self.categories:
            result['categories'] = self.categories
        if self.pages:
            result['pages'] = self.pages
        if self.sources:
            result['sources'] = self.sources
        if self.caption:
            result['caption'] = self.caption
        if self.entity:
            result['entity'] = self.entity
        
        return result
    
    @classmethod
    def from_query_params(cls, params: Dict[str, Any]) -> "MVPSearchFilter":
        """
        쿼리 파라미터에서 필터 생성
        
        Args:
            params: 쿼리 파라미터 딕셔너리
            
        Returns:
            MVPSearchFilter 인스턴스
        """
        # 페이지 파라미터 처리 (문자열 -> 정수 리스트)
        pages = None
        if 'pages' in params:
            if isinstance(params['pages'], str):
                # "1,2,3" 형식 처리
                pages = [int(p.strip()) for p in params['pages'].split(',')]
            elif isinstance(params['pages'], list):
                pages = [int(p) for p in params['pages']]
        
        # 카테고리 파라미터 처리
        categories = None
        if 'categories' in params:
            if isinstance(params['categories'], str):
                categories = [c.strip() for c in params['categories'].split(',')]
            elif isinstance(params['categories'], list):
                categories = params['categories']
        
        # 소스 파라미터 처리
        sources = None
        if 'sources' in params:
            if isinstance(params['sources'], str):
                sources = [s.strip() for s in params['sources'].split(',')]
            elif isinstance(params['sources'], list):
                sources = params['sources']
        
        return cls(
            categories=categories,
            pages=pages,
            sources=sources,
            caption=params.get('caption'),
            entity=params.get('entity')
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "categories": ["table", "figure"],
                "pages": [10, 11, 12],
                "sources": ["gv80_manual.pdf"],
                "caption": "엔진",
                "entity": {
                    "type": "table",
                    "keywords": ["연비", "성능"]
                }
            }
        }