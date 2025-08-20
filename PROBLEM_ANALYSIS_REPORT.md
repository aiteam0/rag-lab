# RAG Workflow Problem Analysis Report

## Executive Summary
The RAG workflow fails due to two critical issues:
1. **Incorrect filter generation**: LLM incorrectly interprets "GV80" as a document source, creating a non-existent filter
2. **Error state persistence**: Retrieval errors persist in state, causing workflow failure even after successful web search

## Detailed Problem Analysis

### Issue 1: Retrieval Returns 0 Documents

#### Root Cause
The LLM in `SubtaskExecutorNode` incorrectly extracts "GV80 manual" as a `source_mentioned` from queries like "GV80 엔진 오일 교체 주기", then generates a filter `sources: ['gv80_manual.pdf']`.

#### Evidence
```
[SUBTASK_EXECUTOR] Extracted info:
  - source_mentioned: GV80 manual
[SUBTASK_EXECUTOR] Search filter generated:
  - sources: ['gv80_manual.pdf']
```

#### Impact
- Database contains source: `data/gv80_owners_manual_TEST6P.pdf`
- Filter searches for: `gv80_manual.pdf`
- Result: 0 documents found (mismatch)

### Issue 2: Workflow Fails After Successful Web Search

#### Root Cause
In `retrieval.py` line 506, when retrieval fails, it adds an `error` to state:
```python
return {
    "error": f"Retrieval failed: {str(e)}",
    "workflow_status": "failed",
    "warnings": [f"Search error: {str(e)}"]
}
```

This error persists in state even after `web_search` successfully retrieves 3 documents.

#### Evidence
In `graph.py` line 276-278, `_should_continue_subtasks` checks for errors:
```python
if state.get("error"):
    logger.warning(f"[CONDITIONAL] Found error in state: {state.get('error')}")
    return "failed"
```

#### Impact
- Web search succeeds with 3 documents
- Error from retrieval remains in state
- Workflow terminates prematurely

### Issue 3: Overly Restrictive Keyword Search

#### Root Cause
Keyword search uses AND operator for all terms:
```python
search_query = ' & '.join(keywords)  # "엔진 & 오일 & 교체 & 주기"
```

#### Impact
- Requires ALL keywords to be present in document
- Too restrictive for general queries
- Contributes to 0 results

## Solution Plan

### Phase 1: Fix Filter Generation (Critical)

#### Option A: Improve LLM Prompt (Recommended)
**File**: `workflow/nodes/subtask_executor.py`

1. Modify extraction prompt (line 156) to be more explicit:
```python
self.extraction_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a query analyzer for an automobile manufacturing RAG system.
Extract filtering information ONLY if EXPLICITLY mentioned in the query.

CRITICAL RULE: 
- "GV80" is a VEHICLE MODEL NAME, NOT a document source
- Only extract source if the user explicitly mentions a document name like "manual", "guide", "document"
- Examples:
  - "GV80 엔진 오일" → source: None (GV80 is the vehicle model)
  - "GV80 매뉴얼에서" → source: "GV80 manual" (explicitly mentions manual)
  - "owner's guide page 50" → source: "owner's guide", page: 50

[rest of prompt...]
""")
])
```

2. Add validation in `_generate_filter` to reject incorrect sources

#### Option B: Remove Source Filter Generation
**File**: `workflow/nodes/subtask_executor.py`

Simply don't generate source filters unless explicitly requested:
```python
# Line 301-302
if result.sources and not extraction.source_mentioned:
    result.sources = []  # Clear sources unless explicitly mentioned
```

### Phase 2: Fix Error State Persistence

#### Option A: Clear Error on Successful Web Search (Recommended)
**File**: `workflow/graph.py`

In `_web_search_node` (line 451), clear error if documents found:
```python
result = {
    "documents": all_documents,
    "metadata": metadata
}

# Clear error if we found documents
if len(web_documents) > 0:
    result["error"] = None  # Clear any previous errors
    result["workflow_status"] = "continuing"
    
logger.info(f"[WEB_SEARCH] Node completed successfully")
return result
```

#### Option B: Make Retrieval Non-Fatal
**File**: `workflow/nodes/retrieval.py`

Change line 454-460 to warning instead of error:
```python
if not documents and query_variations:
    logger.warning(f"[RETRIEVAL] No documents found, will try web search")
    return {
        "documents": [],  # Empty list instead of error
        "warnings": [f"No documents found in database for {len(query_variations)} variations"],
        "metadata": metadata
    }
```

### Phase 3: Improve Search Flexibility

#### Implement OR-based Search
**File**: `retrieval/hybrid_search.py`

Add parameter for search operator:
```python
def _extract_korean_keywords(self, text: str, operator: str = "OR") -> List[str]:
    # ...
    if operator == "OR":
        search_query = ' | '.join(keywords)  # OR operator
    else:
        search_query = ' & '.join(keywords)  # AND operator
```

## Implementation Priority

1. **Critical (Immediate)**:
   - Fix filter generation (Phase 1, Option A)
   - Fix error persistence (Phase 2, Option A)

2. **Important (Next)**:
   - Improve search flexibility (Phase 3)
   - Add filter validation

3. **Nice to Have**:
   - Better error recovery
   - Caching mechanism
   - Performance optimization

## Testing Plan

1. **Unit Tests**:
   - Test filter generation with "GV80" queries
   - Test error clearing in web_search
   - Test keyword extraction

2. **Integration Tests**:
   - Test full workflow with GV80 queries
   - Test web search fallback
   - Test error recovery

3. **Validation Queries**:
   ```python
   test_queries = [
       "GV80 엔진 오일 교체 주기",  # Should NOT generate source filter
       "GV80 매뉴얼에서 오일 교체",  # Should generate source filter
       "엔진 오일 권장 사양",  # General query
   ]
   ```

## Monitoring

Add these metrics:
- Filter generation accuracy
- Retrieval success rate
- Web search fallback rate
- Error recovery rate

## Conclusion

The workflow failure is caused by:
1. **Incorrect filter generation** treating "GV80" as a document source
2. **Error state persistence** preventing recovery after web search success
3. **Overly restrictive search** using AND operator for all keywords

The recommended solution:
1. Fix the LLM prompt to correctly identify vehicle models vs document sources
2. Clear error state when web search succeeds
3. Use more flexible search operators

These fixes will resolve the immediate issues and improve overall system robustness.