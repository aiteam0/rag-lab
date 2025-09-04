# Entity System Analysis Report - "똑딱이" Integration

## Executive Summary
The current system is hardcoded to support only "image" and "table" entity types in specific categories (figure, table). With the introduction of "똑딱이" entity type in text-based categories (paragraph, heading1-3), significant changes are required across the workflow nodes while minimal changes are needed in ingest and retrieval modules.

## Current Entity Structure

### Original Entity Types
- **Type: "image"** → Category: "figure"
- **Type: "table"** → Category: "table"

### New Entity Type (After Transplantation)
- **Type: "똑딱이"** → Categories: "paragraph", "heading1", "heading2", "heading3"

### Entity Schema
```json
{
    "type": "string",  // "image", "table", or "똑딱이"
    "title": "string",
    "details": "string",
    "keywords": ["string"],
    "hypothetical_questions": ["string"],
    "raw_output": "string"
}
```

## Module-by-Module Analysis

### 1. INGEST MODULE ✅ (Minimal Changes)

#### `ingest/models.py`
- **Current**: EntityInfo class comment mentions only "image, table"
- **Impact**: LOW - Just a comment update
- **Required Change**: Update line 44 comment to include "똑딱이"

#### `ingest/database.py`
- **Current**: Uses JSONB for entity storage
- **Impact**: NONE - Already type-agnostic
- **Required Change**: None

#### `scripts/2_phase1_ingest_documents.py`
- **Current**: `extract_entity_text()` extracts all entity fields generically
- **Impact**: NONE - Already handles any entity structure
- **Required Change**: None

### 2. RETRIEVAL MODULE ✅ (Minor Changes)

#### `retrieval/search_filter.py`
- **Current**: JSONB queries for type, title, keywords, details
- **Impact**: NONE - Already flexible
- **Required Change**: None

#### `retrieval/hybrid_search.py`
- **Current**: Uses generic `extract_entity_text()` from ingest script
- **Impact**: NONE - Type-agnostic
- **Required Change**: None

### 3. WORKFLOW NODES ⚠️ (Major Changes)

#### `workflow/nodes/retrieval.py`
- **Current Issue**: Line 172 hardcodes `["image", "table"]` for entity searches
- **Impact**: HIGH - Won't find "똑딱이" entities
- **Required Change**:
  ```python
  # Line 172 - BEFORE:
  entity_filter_dict["categories"] = ["image", "table"]
  
  # AFTER (Option 1 - Include all categories with entities):
  entity_filter_dict["categories"] = ["figure", "table", "paragraph", "heading1", "heading2", "heading3"]
  
  # AFTER (Option 2 - Remove category restriction entirely):
  # Don't set categories at all when entity filter is present
  ```

#### `workflow/nodes/subtask_executor.py`
- **Current Issues**:
  1. Lines 228-230: Only maps to 'image' or 'table'
  2. Lines 347-356: Entity type validation only allows 'image' or 'table'
  3. Lines 259-260, 277-278: Examples only show 'image' or 'table'
  
- **Impact**: HIGH - Won't generate filters for "똑딱이" type
- **Required Changes**:
  ```python
  # Lines 228-231 - Add "똑딱이" mapping:
  2. Entity type: ONLY 'image', 'table', or '똑딱이'. Map similar terms:
     - 'figure', 'diagram', 'picture', 'illustration', '그림', '사진' → 'image'
     - 'chart', 'graph', '차트', '그래프' → 'image'
     - '똑딱이', '참조문서', 'reference', 'appendix', '삽입객체' → '똑딱이'
  
  # Lines 347-356 - Add "똑딱이" validation:
  elif result.entity_type == '똑딱이' and '똑딱이' in valid_types:
      pass  # 유지
  ```

#### `workflow/nodes/synthesis.py`
- **Current Issue**: `_format_entity_info()` only handles table/figure categories
- **Impact**: HIGH - Won't display "똑딱이" entity information
- **Required Change**:
  ```python
  def _format_entity_info(self, metadata: dict) -> str:
      entity = metadata.get("entity")
      if not entity:
          return ""
      
      if not isinstance(entity, dict):
          return f"- Entity Info: {str(entity)}\n"
      
      category = metadata.get("category", "")
      entity_type = entity.get("type", "")
      
      # Handle "똑딱이" type (in text categories)
      if entity_type == "똑딱이":
          entity_text = "- Document Entity (똑딱이):\n"
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
              entity_text += f"  Can Answer: {'; '.join(str(q) for q in hypothetical_questions[:3])}\n"
          return entity_text.rstrip()
      
      # Existing table handling...
      elif category == "table" and entity:
          # ... existing code ...
      
      # Existing figure handling...
      elif category == "figure" and entity:
          # ... existing code ...
  ```

#### `workflow/nodes/hallucination.py`
- **Current Issue**: Lines 165-183 only handle table/figure categories
- **Impact**: MEDIUM - Won't include "똑딱이" entity in grounding check
- **Required Change**: Similar to synthesis.py, add handling for "똑딱이" type

## Priority of Changes

### Critical (Must Fix) 🔴
1. `retrieval.py`: Entity search category restriction
2. `subtask_executor.py`: Entity type validation and mapping
3. `synthesis.py`: Entity display formatting

### Important (Should Fix) 🟡
1. `hallucination.py`: Entity grounding check
2. `subtask_executor.py`: Update prompt examples

### Nice to Have 🟢
1. `models.py`: Update comments

## Implementation Strategy

### Phase 1: Core Functionality (Minimal Changes)
1. **retrieval.py**: Remove or expand category restriction for entity searches
2. **subtask_executor.py**: Add "똑딱이" to valid entity types
3. **synthesis.py**: Add basic "똑딱이" entity formatting

### Phase 2: Full Support (Optimal)
1. **synthesis.py**: Rich formatting for "똑딱이" entities
2. **hallucination.py**: Complete entity grounding for all types
3. **subtask_executor.py**: Update all prompts and examples

## Testing Checklist

### After Implementation
- [ ] Verify "똑딱이" entities are ingested correctly
- [ ] Test entity filter generation with "똑딱이" type
- [ ] Confirm retrieval finds documents with "똑딱이" entities
- [ ] Check synthesis properly formats "똑딱이" entity information
- [ ] Validate hallucination check includes "똑딱이" entities
- [ ] Test with mixed entity types in single query

## Optimization Considerations

1. **Maintain Backward Compatibility**: Keep support for existing "image" and "table" types
2. **Generic Entity Handling**: Consider making entity handling type-agnostic where possible
3. **Dynamic Type Discovery**: Use DB queries to discover available types rather than hardcoding
4. **Caching**: Cache available entity types to avoid repeated DB queries

## Risks and Mitigation

### Risk 1: Performance Impact
- **Risk**: Including more categories in entity searches may slow queries
- **Mitigation**: Use indexed JSONB queries, limit top_k appropriately

### Risk 2: Unexpected Entity Types
- **Risk**: Future entity types may break hardcoded logic
- **Mitigation**: Implement generic entity handling where possible

### Risk 3: Display Issues
- **Risk**: Long "details" field in "똑딱이" entities may affect UI
- **Mitigation**: Implement truncation or summary display options

## Conclusion

The system requires targeted modifications primarily in the workflow nodes to support the new "똑딱이" entity type. The ingest and retrieval modules are largely ready due to their generic JSONB handling. The key challenge is updating the hardcoded assumptions about entity types and their associated categories throughout the workflow nodes.

**Total Files Requiring Changes**: 4-5 files
**Estimated Effort**: 2-3 hours
**Risk Level**: Medium (due to workflow logic changes)