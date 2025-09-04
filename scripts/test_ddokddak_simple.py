#!/usr/bin/env python3
"""
Simple direct test of DDUFilterGeneration with '똑딱이' entity type
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.subtask_executor import DDUFilterGeneration
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

def test_ddokddak_schema():
    """Test if DDUFilterGeneration schema allows '똑딱이' entity type"""
    print("\n" + "="*60)
    print("Testing DDUFilterGeneration Schema for '똑딱이' Support")
    print("="*60)
    
    # Check the field description
    entity_field = DDUFilterGeneration.model_fields['entity']
    description = entity_field.description
    
    print(f"\nEntity field description: {description}")
    
    if '똑딱이' in description:
        print("✅ SUCCESS: '똑딱이' is included in the entity field description!")
    else:
        print("❌ FAILURE: '똑딱이' is NOT in the entity field description!")
        print("   The description only allows:", description)
        return False
    
    # Test with LLM
    print("\n" + "-"*40)
    print("Testing LLM generation with '똑딱이' entity type...")
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        structured_llm = llm.with_structured_output(DDUFilterGeneration)
        
        prompt = """Generate a filter for PPT embedded documents (똑딱이 type).
The query is asking about '똑딱이 문서' which are embedded documents in PPT.

Create an entity filter with type='똑딱이'."""
        
        result = structured_llm.invoke(prompt)
        
        print(f"Generated result:")
        print(f"  Entity: {result.entity}")
        print(f"  Categories: {result.categories}")
        print(f"  Reasoning: {result.reasoning}")
        
        if result.entity and result.entity.get('type') == '똑딱이':
            print("\n✅ SUCCESS: LLM generated '똑딱이' entity filter correctly!")
            return True
        else:
            print(f"\n❌ FAILURE: LLM did not generate '똑딱이' entity filter!")
            print(f"   Generated entity: {result.entity}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during LLM test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ddokddak_schema()
    sys.exit(0 if success else 1)