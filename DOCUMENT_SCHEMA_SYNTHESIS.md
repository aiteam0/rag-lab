# Document Schema for Synthesis Node - Complete Reference

## Overview
The synthesis node in the multimodal-rag-wsl-v2 project processes LangChain Document objects containing text content and rich metadata. This document provides a comprehensive reference for the Document schema structure used throughout the workflow.

## Document Object Structure

### Base Structure
```python
Document(
    page_content: str,  # The main text content
    metadata: Dict[str, Any]  # Structured metadata dictionary
)
```

### Page Content Field
The `page_content` field contains the primary text that gets searched and synthesized:

- **For text types** (heading1-3, paragraph, list, caption, footnote, header, footer, reference):
  - Contains `original_markdown` formatted text
  - Preserves formatting for better readability
  
- **For non-text types** (table, figure, chart, equation):
  - Contains `original_text` plain text representation
  - May be simplified or extracted text from visual elements

## Metadata Schema

### Core Fields (Present in All Documents)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `source` | str | Original file path | `"data/디지털정부혁신_추진계획.pdf"` |
| `page` | int | Page number in source document | `3` |
| `category` | str | DDU category type | `"paragraph"`, `"table"`, `"figure"`, `"heading1"` |
| `id` | str | Unique element identifier | `"doc_001_para_042"` |
| `caption` | str/None | Caption or description text | `"Figure 1: System Architecture"` |
| `human_feedback` | str/None | User-provided corrections or enhancements | `"This table shows Q3 2024 data"` |

### Extended Metadata Fields

| Field | Type | Description | When Present |
|-------|------|-------------|--------------|
| `raw_output` | str | Original unprocessed content | Tables (markdown format) |
| `translation_text` | str/None | Translated version of content | When translation available |
| `translation_markdown` | str/None | Markdown-formatted translation | When translation available |
| `translation_html` | str/None | HTML-formatted translation | When translation available |
| `contextualize_text` | str/None | Contextual information added | When context enhancement done |
| `image_path` | str/None | Path to associated image file | Figures and visual elements |
| `coordinates` | Dict/None | Location coordinates in PDF | All elements |
| `processing_type` | str | How element was processed | All elements |
| `processing_status` | str | Processing completion status | All elements |
| `source_parser` | str | Parser that extracted element | All elements |
| `element_type` | str | High-level type classification | `"text"`, `"image"`, `"table"` |
| `page_image_path` | str/None | Path to page screenshot | When page image available |

### Entity Field Structure

The `entity` field is a nested dictionary containing structured information. Its structure varies by entity type:

#### Type: "똑딱이" (PPT Embedded Document)
```python
{
    "type": "똑딱이",
    "title": "정부혁신 추진 로드맵",  # Document title
    "details": "2024-2028 중장기 계획...",  # Content details
    "keywords": ["디지털정부", "혁신", "로드맵"],  # Searchable keywords
    "hypothetical_questions": [  # Potential user queries
        "정부혁신 로드맵은 무엇인가요?",
        "중장기 계획 내용을 알려주세요"
    ]
}
```

#### Type: "table"
```python
{
    "type": "table",
    "title": "2024년도 예산 집행 현황",  # Table title
    "details": "부서별 예산 집행률 및 잔액",  # Table description
    "keywords": ["예산", "집행", "2024"],  # Searchable keywords
    "hypothetical_questions": [  # Potential queries
        "2024년 예산 집행 현황은?",
        "부서별 예산 사용 내역을 보여줘"
    ]
}
```

#### Type: "figure"
```python
{
    "type": "figure",
    "title": "시스템 아키텍처 다이어그램",  # Figure title
    "description": "3-tier 아키텍처 구성도...",  # Visual description
    "keywords": ["아키텍처", "시스템", "구성도"],  # Optional
    "hypothetical_questions": [  # Optional
        "시스템 구조를 보여줘"
    ]
}
```

#### Type: "image"
```python
{
    "type": "image",
    "title": "제품 외관 이미지",
    "description": "GV80 전면부 고해상도 이미지"
}
```

## DDU Category Types

Complete list of supported categories (14 types):

1. **Text Categories**:
   - `heading1`, `heading2`, `heading3` - Hierarchical headings
   - `paragraph` - Body text
   - `list` - Bulleted or numbered lists
   - `caption` - Image/table captions
   - `footnote` - Page footnotes
   - `header` - Page headers
   - `footer` - Page footers
   - `reference` - Bibliography/references

2. **Visual Categories**:
   - `table` - Tabular data
   - `figure` - Diagrams and illustrations
   - `chart` - Graphs and charts
   - `equation` - Mathematical equations

## Processing Flow in Synthesis Node

### 1. Document Retrieval
Documents are retrieved from the database with all metadata intact:
```python
documents = retrieval_result.get("documents", [])
```

### 2. Priority-Based Content Selection
The synthesis node processes documents with this priority hierarchy:
```
1. HIGHEST: Human Feedback (if present)
2. HIGH: Structured Entity Data (똑딱이, tables, figures)
3. STANDARD: Raw page_content
```

### 3. Entity Information Formatting
The `_format_entity_info()` method (lines 182-198 in synthesis.py) creates structured representations:

```python
# For "똑딱이" type:
"- PPT Embedded Document (똑딱이): [title]
  Details: [details]
  Keywords: [keyword1, keyword2, ...]"

# For "table" type:
"- Table: [title]
  Details: [details]
  Keywords: [keyword1, keyword2, ...]"

# For "figure" type:
"- Figure: [title]
  Description: [description]"
```

### 4. Document Formatting
The `_format_documents()` method combines all information:
```python
formatted_doc = self.document_formatter_prompt.format(
    source=metadata.get("source", "Unknown"),
    page=metadata.get("page", "N/A"),
    content=doc.page_content,
    caption=metadata.get("caption", ""),
    human_feedback=human_feedback,  # Highest priority
    entity_info=entity_info_text,    # Structured data
    page_image_path=page_image_path
)
```

### 5. Special Handling for "똑딱이"
Documents with "똑딱이" entity type receive special emphasis:
- Prefixed with `[📌 PPT 삽입 문서]`
- Entity info marked as `**[SPECIAL] PPT Embedded Document (똑딱이)**`
- Mentioned explicitly in synthesis prompts

## Usage Examples

### Example 1: Regular Paragraph Document
```python
Document(
    page_content="디지털 정부혁신은 국민 중심의 서비스 개선을 목표로 합니다...",
    metadata={
        "source": "data/디지털정부혁신_추진계획.pdf",
        "page": 1,
        "category": "paragraph",
        "id": "dgov_para_001",
        "caption": None,
        "human_feedback": None,
        "entity": None
    }
)
```

### Example 2: Table with Entity Information
```python
Document(
    page_content="부서명 | 예산 | 집행률\n기획부 | 100억 | 85%...",
    metadata={
        "source": "data/디지털정부혁신_추진계획.pdf",
        "page": 5,
        "category": "table",
        "id": "dgov_table_003",
        "caption": "Table 3: Budget Execution Status",
        "entity": {
            "type": "table",
            "title": "2024 예산 집행 현황",
            "details": "부서별 예산 집행률",
            "keywords": ["예산", "집행률", "2024"],
            "hypothetical_questions": ["예산 집행 현황은?"]
        },
        "raw_output": "| 부서명 | 예산 | 집행률 |\n|--------|------|-------|\n..."
    }
)
```

### Example 3: PPT Embedded Document ("똑딱이")
```python
Document(
    page_content="정부혁신 5개년 로드맵 - Phase 1: 기반 구축...",
    metadata={
        "source": "data/디지털정부혁신_추진계획.pdf",
        "page": 3,
        "category": "figure",
        "id": "dgov_ddok_001",
        "caption": "정부혁신 로드맵 PPT 슬라이드",
        "entity": {
            "type": "똑딱이",
            "title": "디지털 정부혁신 5개년 로드맵",
            "details": "2024-2028 단계별 추진 계획",
            "keywords": ["로드맵", "5개년", "정부혁신"],
            "hypothetical_questions": [
                "정부혁신 로드맵의 단계는?",
                "5개년 계획 내용은?"
            ]
        },
        "image_path": "data/images/dgov_page3_roadmap.png"
    }
)
```

## Best Practices for Document Processing

1. **Always Check for Human Feedback First**
   - Human feedback overrides all other content
   - Indicates verified or corrected information

2. **Utilize Entity Information When Available**
   - Provides structured, searchable metadata
   - Contains pre-analyzed summaries and keywords
   - Includes hypothetical questions for better matching

3. **Special Attention to "똑딱이" Type**
   - These are key presentation materials
   - Often contain strategic or summary information
   - Should be prominently mentioned in answers

4. **Preserve Source Attribution**
   - Always maintain source file and page references
   - Critical for traceability and verification

5. **Handle Missing Fields Gracefully**
   - Use `.get()` method with defaults
   - Don't assume all fields are present
   - Check for None values before processing

## Integration Points

### Database Storage (PostgreSQL)
- Documents stored in `mvp_ddu_documents` table
- Entity field stored as JSONB for flexible querying
- Full-text search vectors include entity keywords

### Retrieval System
- Entity keywords enhance search matching
- Hypothetical questions improve query alignment
- Human feedback prioritized in ranking

### Synthesis Output
- Structured entity information formatted for readability
- "똑딱이" documents highlighted specially
- Human feedback clearly marked when present

### Quality Validation
- Hallucination check uses entity information as ground truth
- Answer grading considers entity coverage
- Human feedback treated as authoritative source

## Schema Version History

- **v1.0** (2024): Initial schema with basic metadata
- **v1.1** (2024): Added entity field for structured data
- **v1.2** (2024): Added human_feedback field
- **v1.3** (2025): Enhanced "똑딱이" entity type support
- **v1.4** (2025): Added hypothetical_questions to all entity types

## References

- Source Code: `/workflow/nodes/synthesis.py`
- Database Schema: `/ingest/models.py`
- Test Data: `/scripts/test_ddokddak_entity_mention.py`
- Configuration: `CLAUDE.md` (DDU Langchain Document Schema section)