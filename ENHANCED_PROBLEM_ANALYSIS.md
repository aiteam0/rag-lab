# Enhanced Problem Analysis & Comprehensive Fix Plan

## 🔴 ROOT CAUSE IDENTIFIED

### The Core Problem: Metadata Not Passed to LLM

**Discovery**: While `MetadataHelper` fetches actual sources from DB, this information is **NEVER** passed to the LLM prompts!

#### Evidence from Code Analysis:

1. **MetadataHelper fetches sources** (line 98-105):
```python
sources = await conn.fetch(
    "SELECT DISTINCT source FROM mvp_ddu_documents ORDER BY source"
)
# Returns: ['data/gv80_owners_manual_TEST6P.pdf']
```

2. **But extraction_prompt only receives** (line 170-171):
```python
Available Categories: {categories}  ✅
Available Entity Types: {entity_types}  ✅
Available Sources: MISSING! ❌
```

3. **And filter_prompt only receives** (line 214):
```python
Available entity types: {entity_types}  ✅
Available sources: MISSING! ❌
```

### The Misleading Example Problem

**Line 206-207 provides harmful example**:
```
Query: "GV80 매뉴얼에서..."
Extraction: {source_mentioned: "GV80", ...}
Filter: {sources: ["gv80_manual.pdf"], ...}  ← WRONG!
```

This teaches LLM to:
- Convert "GV80" → "gv80_manual.pdf"
- But actual DB has: "data/gv80_owners_manual_TEST6P.pdf"

## 📊 Complete Bug Flow Analysis

### Current (Broken) Flow:
```
1. Query: "GV80 엔진 오일 교체 주기"
   ↓
2. MetadataHelper: Fetches real sources ✅
   → ['data/gv80_owners_manual_TEST6P.pdf']
   ↓
3. Extraction Prompt: Doesn't receive sources ❌
   → LLM guesses: source_mentioned = "GV80 manual"
   ↓
4. Filter Generation: Doesn't receive sources ❌
   → LLM follows bad example: sources = ["gv80_manual.pdf"]
   ↓
5. Database Search: WHERE source = 'gv80_manual.pdf'
   → 0 results (doesn't exist!)
   ↓
6. Retrieval fails → adds error to state
   ↓
7. Web search succeeds → 3 documents
   ↓
8. Error persists in state → workflow terminates ❌
```

## 🛠️ COMPREHENSIVE FIX PLAN v2.0

### Phase 1: Fix Metadata Passing (CRITICAL)

#### 1.1 Update extraction_prompt
```python
# Line 170-171, ADD:
Available Categories: {categories}
Available Entity Types: {entity_types}
Available Sources: {sources}  # ← ADD THIS!

# Line 243-245, ADD:
sources_str = ", ".join(metadata.get("available_sources", []))

# Line 249-251, UPDATE:
query=query,
categories=categories_str,
entity_types=entity_types_str,
sources=sources_str  # ← ADD THIS!
```

#### 1.2 Update filter_prompt
```python
# Line 214, ADD:
Available entity types: {entity_types}
Available sources: {sources}  # ← ADD THIS!

# Line 278-280, ADD:
sources_str = ", ".join(metadata.get("available_sources", []))

# Line 283-286, UPDATE:
extraction=extraction.model_dump(),
entity_types=entity_types_str,
sources=sources_str  # ← ADD THIS!
```

### Phase 2: Fix Prompt Instructions & Examples

#### 2.1 Clarify GV80 is a vehicle model
```python
# Line 157-167, UPDATE:
STRICT RULES:
...
3. Source: ONLY if specific document name is mentioned
   IMPORTANT: "GV80", "GV70", "GV90" etc. are VEHICLE MODELS, not document names!
   Examples of valid sources:
   - "manual", "guide", "document" → extract source
   - "GV80" alone → DO NOT extract as source (it's the vehicle model)
   - "GV80 매뉴얼" → extract source (explicitly mentions manual)
```

#### 2.2 Fix misleading examples
```python
# Line 205-207, UPDATE FROM:
Query: "GV80 매뉴얼에서 안전벨트 관련 그림 찾아줘"
Extraction: {source_mentioned: "GV80", ...}
Filter: {sources: ["gv80_manual.pdf"], ...}

# TO:
Query: "GV80 매뉴얼에서 안전벨트 관련 그림 찾아줘"
Extraction: {source_mentioned: "manual", ...}
Filter: {} (EMPTY - let search handle it, or match against available sources)

# OR if sources are provided:
Filter: {sources: ["data/gv80_owners_manual_TEST6P.pdf"], ...}
```

### Phase 3: Add Source Validation

#### 3.1 Validate against actual sources
```python
# In _generate_filter method, after line 301:
if result.sources:
    valid_sources = metadata.get("available_sources", [])
    validated_sources = []
    
    for source in result.sources:
        # Check exact match
        if source in valid_sources:
            validated_sources.append(source)
        else:
            # Try fuzzy matching
            for valid_source in valid_sources:
                if source.lower() in valid_source.lower():
                    validated_sources.append(valid_source)
                    break
    
    result.sources = validated_sources if validated_sources else []
```

### Phase 4: Fix Error State Persistence

#### 4.1 Clear error on web search success
```python
# In graph.py _web_search_node, after line 453:
if len(web_documents) > 0:
    result["error"] = None  # Clear previous errors
    result["workflow_status"] = "continuing"
```

#### 4.2 Alternative: Make retrieval non-fatal
```python
# In retrieval.py, line 454-460, REPLACE error with warning:
if not documents and query_variations:
    logger.warning(f"[RETRIEVAL] No documents found, will try web search")
    return {
        "documents": [],  # Empty list, not error
        "warnings": [f"No documents found for {len(query_variations)} variations"],
        "require_web_search": True  # Signal for web search
    }
```

### Phase 5: Improve Search Flexibility

#### 5.1 Add OR operator option for keywords
```python
# In hybrid_search.py, line 175:
# Change FROM:
search_query = ' & '.join(keywords)
# TO:
search_query = ' | '.join(keywords)  # OR operator for flexibility
# OR make it configurable:
operator = ' | ' if relaxed_search else ' & '
search_query = operator.join(keywords)
```

## 📋 Implementation Priority

### Critical (Must Fix Now):
1. ✅ Pass available_sources to LLM prompts (Phase 1)
2. ✅ Fix misleading examples (Phase 2.2)
3. ✅ Clear error state on web search (Phase 4.1)

### Important (Should Fix):
1. ⚡ Add source validation (Phase 3)
2. ⚡ Clarify GV80 is vehicle model (Phase 2.1)
3. ⚡ Use OR operator for keywords (Phase 5)

### Nice to Have:
1. 💡 Fuzzy matching for sources
2. 💡 Caching mechanism
3. 💡 Better error messages

## 🧪 Testing Strategy

### Test Cases:
```python
test_queries = [
    # Should NOT create source filter
    ("GV80 엔진 오일 교체 주기", None),
    
    # Should create source filter
    ("GV80 매뉴얼에서 오일 교체", ["data/gv80_owners_manual_TEST6P.pdf"]),
    
    # Should handle gracefully
    ("엔진 오일 권장 사양", None),
]
```

### Validation Points:
1. ✅ Source filter only when explicitly mentioned
2. ✅ Generated sources match DB sources
3. ✅ Web search recovery works
4. ✅ Keywords use OR operator

## 🎯 Expected Outcomes

After implementing these fixes:

1. **Query**: "GV80 엔진 오일 교체 주기"
   - ❌ OLD: Filter with non-existent source → 0 results
   - ✅ NEW: No filter → searches all documents → finds results

2. **Error Recovery**:
   - ❌ OLD: Error persists after web search → workflow fails
   - ✅ NEW: Error cleared on web search → workflow continues

3. **Search Quality**:
   - ❌ OLD: All keywords required (AND) → too restrictive
   - ✅ NEW: Any keyword matches (OR) → better coverage

## 📊 Root Cause Summary

The bug occurs because:
1. **Metadata not passed**: LLM doesn't know actual sources
2. **Bad examples**: Prompt teaches wrong conversion pattern
3. **No validation**: Generated sources not checked against DB
4. **Error persistence**: Retrieval errors block workflow
5. **Restrictive search**: AND operator too limiting

The fix is straightforward:
1. Pass the metadata to LLM
2. Fix the examples
3. Add validation
4. Clear errors appropriately
5. Use more flexible search

This comprehensive plan addresses all identified issues systematically.