# Synthesis Schema Gap Analysis Report

## Executive Summary
Analysis of synthesis node reveals significant gaps between what the prompts instruct the LLM to include and what the SynthesisResult schema captures. While page images are now successfully included (solved), critical metadata about human feedback, entity information, and warnings are being lost after synthesis.

## Current SynthesisResult Schema
```python
class SynthesisResult(BaseModel):
    answer: str                                    # Main answer text ✅
    confidence: float                              # Score 0.0-1.0 ✅
    sources_used: List[str]                        # Citations ['[1]', '[2]'] ✅
    key_points: List[str]                          # Main points from docs ✅
    references_table: str                          # Markdown table with sources ✅
    page_images: Optional[List[PageImageInfo]]     # Page images (RECENTLY ADDED) ✅
```

## Prompt Instructions vs Schema Gaps

### 1. Human Feedback (HIGHEST PRIORITY - Line 59)
**Prompt Instructions:**
- "HIGHEST PRIORITY - Human Verified Content"
- "If a document has 'Human Verified' information, this is the ground truth"
- "When human feedback exists, prioritize it over other sources"
- "If there are conflicting information, human feedback takes precedence"

**Current Implementation:**
- Formatted as `"- Human Verified: {human_feedback}"` (line 338)
- Passed to LLM in prompt

**GAP:** ❌ No field to track which human feedback was used or if it influenced the answer

### 2. Entity Information (HIGH PRIORITY - Lines 60-64)
**Prompt Instructions:**
- "HIGH PRIORITY - Structured Entity Data"
- Special handling for 똑딱이 (PPT Embedded Documents)
- "ALWAYS mention it's a 'PPT 삽입 문서' or 'PPT Embedded Document'"
- Use structured data from tables/figures for precise details

**Current Implementation:**
- `_format_entity_info()` method formats entity data (lines 174-240):
  - 똑딱이: title, details, keywords, hypothetical_questions
  - table: title, details, keywords
  - figure: title, description

**GAP:** ❌ No field to capture which entities were referenced or their metadata

### 3. Warnings and Cautions (Line 109)
**Prompt Instructions:**
- "Include relevant warnings or cautions if mentioned"

**Current Implementation:**
- Expected to be included in answer text

**GAP:** ❌ No dedicated field to ensure warnings are captured and trackable

## Missing Content Analysis

### Content Being Formatted but Lost:
1. **Entity Metadata**
   - Type (똑딱이/table/figure)
   - Title
   - Details/Description
   - Keywords
   - Hypothetical questions (for 똑딱이)

2. **Human Feedback**
   - Which documents had human feedback
   - What corrections were applied
   - Whether feedback influenced the answer

3. **Captions**
   - Currently formatted as `"- Caption: {caption}"` (line 329)
   - Lost after synthesis

4. **Document Categories**
   - heading1, paragraph, table, figure, etc.
   - Important for understanding content structure

## Minimal Schema Enhancement Recommendations

Based on actual usage patterns and avoiding over-extension, add these fields to SynthesisResult:

```python
class EntityReference(BaseModel):
    """Entity information that was referenced in the answer"""
    entity_type: str = Field(description="Type: 똑딱이, table, or figure")
    title: Optional[str] = Field(description="Entity title if available")
    details: Optional[str] = Field(description="Entity details or description")
    source_doc: str = Field(description="Source document reference [1], [2], etc.")

class SynthesisResult(BaseModel):
    # ... existing fields ...
    
    # NEW FIELDS (Minimal additions based on actual usage):
    human_feedback_used: Optional[List[str]] = Field(
        default=None,
        description="List of human feedback that was incorporated into the answer"
    )
    
    entity_references: Optional[List[EntityReference]] = Field(
        default=None,
        description="Structured entity information (똑딱이/table/figure) referenced in answer"
    )
    
    warnings: Optional[List[str]] = Field(
        default=None,
        description="Any warnings or cautions extracted from documents"
    )
```

## Implementation Impact

### Benefits of These Additions:
1. **Human Feedback Tracking**: Can verify ground truth was used
2. **Entity Preservation**: Structured data remains accessible post-synthesis
3. **똑딱이 Detection**: Can confirm if PPT embedded documents were referenced
4. **Safety**: Warnings are explicitly captured
5. **Quality Verification**: Downstream nodes can validate answer completeness

### Minimal Disruption:
- All new fields are Optional (backward compatible)
- No changes to existing field behavior
- Simple data structures (Lists and basic types)
- Based on actual document metadata available

## Priority Order for Implementation

1. **human_feedback_used** - Critical for ground truth tracking
2. **entity_references** - Important for 똑딱이/table/figure tracking
3. **warnings** - Safety-critical information

## Files Requiring Updates

1. **workflow/nodes/synthesis.py**:
   - Add new Pydantic models (EntityReference)
   - Update SynthesisResult schema
   - Modify generation methods to populate new fields:
     - `_generate_answer_with_fallback()` (line 375)
     - `_generate_corrective_answer()` (line 711)
     - `_generate_improved_answer()` (line 866)

## Conclusion

The current SynthesisResult schema captures basic answer information but loses critical metadata about HOW the answer was generated. The recommended minimal additions (3 new fields) would preserve essential information without over-extending the schema, enabling better quality control and verification in downstream processing.