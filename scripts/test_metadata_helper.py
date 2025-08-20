#!/usr/bin/env python3
"""
Test MetadataHelper to see what metadata is actually fetched
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from workflow.nodes.subtask_executor import MetadataHelper
from dotenv import load_dotenv
import json

load_dotenv()

async def test_metadata():
    """Test what metadata is actually fetched"""
    print("=" * 60)
    print("Testing MetadataHelper")
    print("=" * 60)
    
    try:
        # Initialize helper
        helper = MetadataHelper()
        print("\n✅ MetadataHelper initialized")
        
        # Get metadata
        metadata = await helper.get_metadata()
        
        print("\n📊 Metadata fetched from database:")
        print("-" * 40)
        
        # Categories
        if "categories" in metadata:
            categories = metadata["categories"]
            print(f"\n📁 Categories ({len(categories)} total):")
            for cat in categories[:10]:  # Show first 10
                print(f"  - {cat}")
            if len(categories) > 10:
                print(f"  ... and {len(categories) - 10} more")
        
        # Entity types
        if "entity_types" in metadata:
            entity_types = metadata["entity_types"]
            print(f"\n🏷️ Entity Types ({len(entity_types)} total):")
            for et in entity_types:
                print(f"  - {et}")
        
        # Available sources
        if "available_sources" in metadata:
            sources = metadata["available_sources"]
            print(f"\n📄 Available Sources ({len(sources)} total):")
            for source in sources:
                print(f"  - {source}")
        
        # Show full metadata structure
        print("\n📋 Full metadata structure:")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        
        # Key insight
        print("\n" + "=" * 60)
        print("🔍 KEY INSIGHT:")
        print("-" * 40)
        print("✅ Metadata contains 'available_sources' with actual DB sources")
        print("❌ But this is NOT passed to the LLM prompts!")
        print("❌ LLM is guessing 'gv80_manual.pdf' instead of using")
        print(f"   '{sources[0] if sources else 'N/A'}'")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_metadata())