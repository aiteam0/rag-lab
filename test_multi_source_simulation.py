"""
Multi-source 필터링 시뮬레이션 테스트
여러 source에 대한 필터 생성과 검색이 정상 동작하는지 확인
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from retrieval.search_filter import MVPSearchFilter

def test_multi_source_filter():
    """여러 source에 대한 필터 테스트"""
    
    print("="*60)
    print("🧪 Multi-Source Filter Simulation")
    print("="*60)
    
    # 시나리오 1: 단일 source 필터
    print("\n1️⃣ Single Source Filter")
    filter1 = MVPSearchFilter(
        sources=["gv80_manual.pdf"],
        pages=[10, 11, 12],
        categories=["paragraph", "table"]
    )
    where1, params1 = filter1.to_sql_where_asyncpg()
    print(f"WHERE: {where1}")
    print(f"Params: {params1}")
    
    # 시나리오 2: 여러 source 필터
    print("\n2️⃣ Multiple Sources Filter")
    filter2 = MVPSearchFilter(
        sources=["gv80_manual.pdf", "gv70_manual.pdf", "genesis_guide.pdf"],
        pages=[1, 2, 3, 100, 200],  # 각 source마다 다른 페이지 범위
        categories=["table", "figure"]
    )
    where2, params2 = filter2.to_sql_where_asyncpg()
    print(f"WHERE: {where2}")
    print(f"Params: {params2}")
    
    # 시나리오 3: Entity 필터 포함
    print("\n3️⃣ Filter with Entity")
    filter3 = MVPSearchFilter(
        sources=["manual1.pdf", "manual2.pdf"],
        entity={
            "type": "table",  # 'image' 또는 'table'만 가능
            "keywords": ["엔진", "연비"]
        }
    )
    where3, params3 = filter3.to_sql_where_asyncpg()
    print(f"WHERE: {where3}")
    print(f"Params: {params3}")
    
    # 문제점 분석
    print("\n📊 Analysis:")
    print("✅ SQL ANY operator handles multiple sources correctly")
    print("⚠️  Issue: Pages [1,2,3,100,200] apply to ALL sources")
    print("   - manual1.pdf may have pages 1-50")
    print("   - manual2.pdf may have pages 1-300")
    print("   - Filter doesn't know which pages belong to which source")
    
    print("\n🔍 Entity Type Validation:")
    print("Current: entity type can be any string")
    print("Should be: entity type restricted to 'image' or 'table'")
    
    # 시나리오 4: 실제 쿼리 시뮬레이션
    print("\n4️⃣ Real Query Simulation")
    print("Query: 'Show me the engine specifications table from page 50'")
    
    # 추출된 정보
    extracted = {
        "pages": [50],
        "entity_type": "table",
        "keywords": ["engine", "specifications"]
    }
    
    # 생성될 필터
    real_filter = MVPSearchFilter(
        pages=[50],
        categories=["table"],  # entity_type이 table이므로
        entity={
            "type": "table",
            "keywords": ["engine", "specifications"]
        }
    )
    where_real, params_real = real_filter.to_sql_where_asyncpg()
    print(f"Generated WHERE: {where_real}")
    print(f"Params: {params_real}")
    
    return True

def analyze_problems():
    """문제점 분석 및 해결방안"""
    
    print("\n" + "="*60)
    print("🚨 Identified Problems & Solutions")
    print("="*60)
    
    print("\n1. DB Connection Required")
    print("   Problem: Falls back to defaults if DB unavailable")
    print("   Solution: Raise exception if DB connection fails")
    print("   ```python")
    print("   if not self.db_connection_string:")
    print("       raise ValueError('Database connection required')")
    print("   ```")
    
    print("\n2. Entity Type Validation")
    print("   Problem: Any string accepted for entity type")
    print("   Solution: Hardcode valid types")
    print("   ```python")
    print("   VALID_ENTITY_TYPES = ['image', 'table']")
    print("   if entity_type and entity_type not in VALID_ENTITY_TYPES:")
    print("       entity_type = None  # Or raise error")
    print("   ```")
    
    print("\n3. Multi-Source Metadata Issue")
    print("   Problem: Single filter applies to all sources equally")
    print("   Issues:")
    print("   - Page ranges differ per source")
    print("   - Categories might differ per source")
    print("   - Entity distribution varies")
    print("   ")
    print("   Current Behavior:")
    print("   - WHERE source = ANY(['doc1', 'doc2']) AND page = ANY([1,2,100])")
    print("   - This returns pages 1,2,100 from BOTH documents")
    print("   ")
    print("   Potential Solutions:")
    print("   a) Don't use source filter - let vector search handle relevance")
    print("   b) Use source filter only when explicitly mentioned")
    print("   c) Create separate queries per source (complex)")
    print("   ")
    print("   Recommended: Option (a) - Rely on semantic search")
    print("   - Remove automatic source filtering")
    print("   - Only filter by source if user explicitly mentions it")
    print("   - Let embeddings find relevant content across all sources")

if __name__ == "__main__":
    test_multi_source_filter()
    analyze_problems()
    
    print("\n" + "="*60)
    print("✅ Simulation Complete")
    print("="*60)