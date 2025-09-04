#!/usr/bin/env python3
"""
Test FILTER_OVERRIDE logic
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.subtask_executor import QueryExtraction
from retrieval.search_filter import MVPSearchFilter
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# 모의 메타데이터
metadata = {
    'entity_types': ['똑딱이', 'image', 'table']
}

# 모의 추출 결과
extraction = QueryExtraction(
    page_numbers=[],
    categories_mentioned=[],
    entity_type='똑딱이',
    source_mentioned=None,
    keywords=['똑딱이', '문서'],
    specific_requirements=""
)

print(f"Entity type: {extraction.entity_type}")
print(f"Metadata entity_types: {metadata.get('entity_types', [])}")

# 조건 체크
if extraction.entity_type == '똑딱이' and '똑딱이' in metadata.get("entity_types", []):
    print("✅ FILTER_OVERRIDE condition met! Would force '똑딱이' filter")
    filter_result = MVPSearchFilter(
        categories=None,
        pages=None,
        sources=None,
        caption=None,
        entity={'type': '똑딱이'}
    )
    print(f"Generated filter: {filter_result.to_dict()}")
else:
    print("❌ Condition not met")