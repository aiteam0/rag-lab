administrator@DESKTOP-VTUOR4O:/mnt/e/MyProject2/multimodal-rag-wsl-v2/scripts$ uv run python 1_setup_database.py

MVP RAG System - Database Setup Utility
============================================================

Options:
1. Setup database (create tables and indexes)
2. Test connection only
3. Exit

Select option (1-3): 1
============================================================
MVP RAG System - Database Setup
============================================================

📌 Initializing database connection...
✅ Connection pool created

📌 Setting up database schema...
✅ 데이터베이스 스키마 설정 완료

📊 Database Statistics:
  - Total Documents: 0
  - Categories: 0 types
  - Sources: 0 files

✅ Database setup completed successfully!

📌 Database connection closed

administrator@DESKTOP-VTUOR4O:/mnt/e/MyProject2/multimodal-rag-wsl-v2/scripts$ uv run python 2_ingest_documents.py

MVP RAG System - Document Ingestion Utility
============================================================

Default pickle file found: /mnt/e/MyProject2/multimodal-rag-wsl-v2/data/gv80_owners_manual_TEST6P_documents.pkl
Use default file? (Y/n): y

Options:
1. Full ingestion
2. Test ingestion (first 5 documents)
3. Exit

Select option (1-3): 1
Batch size (default 10): 10
============================================================
MVP RAG System - Document Ingestion
============================================================

📁 Loading pickle file: /mnt/e/MyProject2/multimodal-rag-wsl-v2/data/gv80_owners_manual_TEST6P_documents.pkl

📊 Document Statistics:
  - Total Documents: 122
  - Categories: {'heading1': 23, 'figure': 10, 'table': 3, 'caption': 4, 'paragraph': 78, 'header': 3, 'list': 1}
  - Sources: ['data/gv80_owners_manual_TEST6P.pdf']...
  - Page Range: 1 - 6
  - Has Translation: 102 docs
  - Has Contextualize: 122 docs

Proceed with ingestion of 122 documents? (y/N): y

📌 Loading documents...
✅ Loaded 122 documents

📌 Starting ingestion (batch size: 10)...
Ingesting: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 13/13 [01:07<00:00,  5.17s/it]

============================================================
Ingestion Summary
============================================================
✅ Successfully ingested: 122 documents
⏱️  Total time: 67.16 seconds
📈 Average: 0.550 seconds per document

📊 Final Database Statistics:
  - Total Documents: 122
  - paragraph: 78 docs
  - heading1: 23 docs
  - figure: 10 docs
  - caption: 4 docs
  - table: 3 docs

✅ Ingestion completed successfully!

administrator@DESKTOP-VTUOR4O:/mnt/e/MyProject2/multimodal-rag-wsl-v2/scripts$ uv run test_phase1.py

MVP RAG System - Phase 1 Test Suite
============================================================

Options:
1. Test all Phase 1 components
2. Test database connection (detailed)
3. Exit

Select option (1-3): 2

============================================================
Database Connection Detailed Test
============================================================

PostgreSQL Version:
PostgreSQL 16.9 (Debian 16.9-1.pgdg120+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14) 12.2.0, 64-bit

pgvector Extension:
  - vector v0.8.0

✅ MVP table exists

Indexes (8):
  - mvp_ddu_documents_pkey
  - idx_korean_embedding
  - idx_english_embedding
  - idx_korean_fts
  - idx_english_fts
  - idx_source
  - idx_category
  - idx_page

  administrator@DESKTOP-VTUOR4O:/mnt/e/MyProject2/multimodal-rag-wsl-v2/scripts$ uv run test_phase1.py

MVP RAG System - Phase 1 Test Suite
============================================================

Options:
1. Test all Phase 1 components
2. Test database connection (detailed)
3. Exit

Select option (1-3): 1
============================================================
MVP RAG System - Phase 1 Components Test
============================================================

📌 Testing Database Module...
  ✅ PostgreSQL connected: PostgreSQL 16.9 (Debian 16.9-1...

📌 Testing Models Module...
  ✅ DDU Categories: 14 types
  ✅ Document conversion successful

📌 Testing Embeddings Module...
  ✅ Korean embedding: 1536 dims
  ✅ English embedding: 1536 dims

📌 Testing Loader Module...
  ✅ Pickle validation: True
  ✅ Loaded 122 documents

📌 Testing SearchFilter Module...
  ✅ Filter created with 3 parameters
  ✅ SQL WHERE clause generated

📌 Testing HybridSearch Module...
  ✅ Kiwi tokenizer initialized
  ✅ Korean text tokenized: 2 tokens

============================================================
Test Summary
============================================================
Database        ✅ PASS
Models          ✅ PASS
Embeddings      ✅ PASS
Loader          ✅ PASS
SearchFilter    ✅ PASS
HybridSearch    ✅ PASS

📈 Results: 6 passed, 0 failed, 0 skipped

✅ Phase 1 components are ready!

administrator@DESKTOP-VTUOR4O:/mnt/e/MyProject2/multimodal-rag-wsl-v2/scripts$ uv run python test_phase1_detailed.py

MVP RAG System - Detailed Phase 1 Test Suite
============================================================

╔═══════════════════════════════════════════╗
║   Phase 1 Detailed Component Testing      ║
╚═══════════════════════════════════════════╝

═══ Database Module Detailed Test ═══

1. Connection Pool Test
  ✅ Concurrent connections: 10 successful

2. Schema Validation Test
  ✅ All 15 columns present

3. CRUD Operations Test
  ✅ INSERT successful (ID: 124)
  ✅ SELECT successful
  ✅ UPDATE successful
  ✅ DELETE successful

4. Index Performance Test
  ℹ️  Found 8 indexes
  ⚠️  Sequential scan detected

═══ Models Module Detailed Test ═══

1. Category Classification Test
  ✅ paragraph  → text   (correct)
  ✅ figure     → image  (correct)
  ✅ table      → table  (correct)
  ✅ heading1   → text   (correct)
  ✅ chart      → image  (correct)

2. Data Conversion Test
  ✅ page_content exists
  ✅ metadata exists
  ✅ category preserved
  ✅ entity preserved
  ✅ image_path preserved
  ✅ All 10 DB fields present

3. Edge Cases Test
  ✅ None values handled correctly

═══ Embeddings Module Detailed Test ═══

1. Various Text Embedding Test
  ✅ Korean only          - Correct
  ✅ English only         - Correct
  ✅ Both languages       - Correct
  ✅ Empty document       - Correct

2. Embedding Dimension & Quality Test
  ✅ Korean embedding dimension: 1536
  ✅ English embedding dimension: 1536
  ℹ️  Korean L2 norm: 1.0000
  ℹ️  English L2 norm: 1.0000
  ℹ️  Korean - Mean: -0.0004, Std: 0.0255
  ℹ️  English - Mean: -0.0005, Std: 0.0255

3. Semantic Similarity Test
  ℹ️  Korean similarity (car-car): 0.7206
  ℹ️  Korean similarity (car-weather): 0.1165
  ✅ Semantic similarity working correctly

4. Performance Test
  ⏱️  Average embedding time: 0.069s per document
  ⏱️  Total time for 10 documents: 0.687s

═══ SearchFilter Module Detailed Test ═══

1. Basic Filter Creation Test
  ✅ Category filter      - Generated SQL with 1 params
     WHERE: category = ANY(%(categories)s)...
  ✅ Page filter          - Generated SQL with 1 params
     WHERE: page = ANY(%(pages)s)...
  ✅ Combined filter      - Generated SQL with 3 params
     WHERE: category = ANY(%(categories)s) AND page = ANY(%(pa...
  ✅ Entity filter        - Generated SQL with 2 params
     WHERE: (entity->>'type' = %(entity_type)s AND entity->'ke...

2. SQL Injection Prevention Test
  ✅ Malicious input 1 safely handled
  ✅ Malicious input 2 safely handled
  ✅ Malicious input 3 safely handled

3. Complex Entity Filter Test
  ✅ All entity fields processed: entity_type, entity_title, entity_keywords, entity_details

4. Query Parameter Parsing Test
  ✅ Categories parsed
  ✅ Pages parsed
  ✅ Sources parsed
  ✅ Caption parsed
  ✅ Entity parsed

5. Empty Filter Test
  ✅ Empty filter correctly identified
  ✅ Empty filter generates valid SQL

═══ HybridSearch Module Detailed Test ═══

1. Korean Keyword Extraction Test
  Query: GV80의 엔진 성능은 어떻게 되나요?
  Keywords: GV, SL
  ✅ Extracted 2 keywords
  Query: 안전 장치와 브레이크 시스템
  Keywords: 안전, NNG
  ✅ Extracted 2 keywords
  Query: 연비와 주행 거리
  Keywords: 연비, NNG
  ✅ Extracted 2 keywords

2. RRF Merge Algorithm Test
  Semantic results: [1, 2, 3, 5]
  Keyword results: [2, 4, 1, 6]
  Merged (top 3): [2, 1, 4]
  ✅ RRF merge working correctly

3. Search with Filter Test
  ℹ️  Found 122 documents in database
  ℹ️  Filter matches 78 documents
  ✅ Filter working correctly

4. Language-specific Search Test
  ✅ Korean search configuration ready
  ✅ English search configuration ready

═══ Loader Module Detailed Test ═══

1. File Validation Test
  ✅ Pickle file validation passed

2. Statistics Test
  Total Documents: 122
  Categories: 7 types
  Sources: 1 files
  Page Range: 1 - 6
  With Translation: 102
  With Context: 122
  With Caption: 13

3. Document Loading Test
  ✅ All 122 documents loaded
  ✅ Document structure valid

4. Category Distribution Analysis
  paragraph         78 docs ( 63.9%)
  heading1          23 docs ( 18.9%)
  figure            10 docs (  8.2%)
  caption            4 docs (  3.3%)
  table              3 docs (  2.5%)

5. Entity Type Analysis
  Found 2 entity types:
    - table: 2 occurrences
    - image: 2 occurrences

6. Loading Performance Test
  ⏱️  Loading time: 0.006s
  ⏱️  Speed: 20418 docs/second

═══ Test Results Summary ═══

                           Detailed Test Results                           
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component                 ┃   Status   ┃ Details                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Connection Pool           │  ✅ PASS   │ 0.108s                         │
│ Schema Validation         │  ✅ PASS   │ 17 columns                     │
│ CRUD Operations           │  ✅ PASS   │ All operations                 │
│ Index Performance         │  ⚠️  WARN   │ Seq scan                       │
│ Category Classification   │  ✅ PASS   │ 5 cases                        │
│ LangChain Conversion      │  ✅ PASS   │ 5 checks                       │
│ DB Dict Conversion        │  ✅ PASS   │ 10 fields                      │
│ Edge Cases                │  ✅ PASS   │ None handling                  │
│ Text Embedding Varieties  │  ✅ PASS   │ 4 cases                        │
│ Embedding Quality         │  ✅ PASS   │ Dimensions OK                  │
│ Semantic Similarity       │  ✅ PASS   │ Similarity ordering correct    │
│ Performance               │  ✅ PASS   │ 0.069s/doc                     │
│ Filter Creation           │  ✅ PASS   │ 4 filters                      │
│ SQL Injection Prevention  │  ✅ PASS   │ 3 tests                        │
│ Complex Entity Filter     │  ✅ PASS   │ 4 fields                       │
│ Query Param Parsing       │  ✅ PASS   │ 5 checks                       │
│ Empty Filter              │  ✅ PASS   │ Correct behavior               │
│ Korean Keyword Extraction │  ✅ PASS   │ Kiwi tokenizer working         │
│ RRF Merge                 │  ✅ PASS   │ Correct ordering               │
│ Filter Integration        │  ✅ PASS   │ 78/122 docs                    │
│ Language Configuration    │  ✅ PASS   │ Both languages                 │
│ File Validation           │  ✅ PASS   │ Valid format                   │
│ Statistics                │  ✅ PASS   │ 122 docs                       │
│ Document Loading          │  ✅ PASS   │ 122 docs                       │
│ Category Analysis         │  ✅ PASS   │ 7 categories                   │
│ Entity Analysis           │  ✅ PASS   │ 2 types                        │
│ Performance               │  ✅ PASS   │ 20418 docs/s                   │
└───────────────────────────┴────────────┴────────────────────────────────┘

Final Statistics:
  ✅ Passed: 26
  ❌ Failed: 0
  ⚠️  Warnings: 1
  ⏭️  Skipped: 0
  ⏱️  Total Time: 17.45s

🎉 All detailed tests passed successfully!

administrator@DESKTOP-VTUOR4O:/mnt/e/MyProject2/multimodal-rag-wsl-v2/scripts$ uv run python test_retrieval_real_data.py
╭───────────────── 🔍 Retrieval Test Suite ─────────────────╮
│ Retrieval System Test with Real Data                      │
│ Testing search functionality with actual database content │
╰───────────────────────────────────────────────────────────╯

Database Status:
  Total documents: 122
  Categories: paragraph(78), heading1(23), figure(10), caption(4), table(3)

1. Korean Keyword Search Test

  Query: '안전벨트'
  Keywords: 안전벨트
  Results: 10 documents
  Relevance: 86.67%
  Time: 1.340s
  Top result: figure (page 6)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 안전과 관련된 정보를 제공하기 위해 설계되었습니다. 특히, 안전벨트 착용 방법과 차량 내 안전한 자세를 강조하고 있습니다. 주변 
텍스트와 함께, 이 이미지는 운전 중 안전을 확보하기 위한 필수 지침을 전달하는 역할을 합니다. 문서 전체에서 이 이미지는 안전벨트 착용의 중요성을 강조하며, 독자가 안전하...
    💬 Caption: Summary:

- **주요 내용**: 경고 아이콘이 포함된 이미지로, 주의 또는 위험을 나타냄.
- **키워드**: 경고, 주의, 위험, 아이콘.
- **특징**: 삼각형 형태의 아이콘 안에 느낌표가 있어 시각적으로 주의를 끌도록 설계됨.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량의 안전벨트를 착용하는 방법을 시각적으로 설명하는 역할을 합니다. 주변 텍스트와 함께, 안전한 운전을 위한 필수적인 절차를 강조하고
있습니다. 이 이미지는 문서의 안전 및 주의 사항 섹션에 위치하여, 운전자가 차량에 탑승하기 전에 반드시 숙지해야 할 내용을 전달합니다. ### 2. 시각적 구조 상세 ...
    💬 Caption: Summary:

- **주요 내용**: 이미지에는 안전벨트를 착용하는 방법이 설명되어 있습니다. 
- **주요 키워드**: 안전벨트, 착용 방법, 안전, 차량.
- **특징**: 
  - 번호가 매겨진 각 부분(1-5)은 안전벨트의 구성 요소를 나타냅니다.
  - 안전벨트의 올바른 착용을 강조하여 안전한 운전을 촉구합니다.

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 - **목적**: 이 이미지는 안전벨트를 착용하는 방법을 시각적으로 설명하기 위해 필요합니다. 안전벨트는 차량 탑승 시 필수적인 안전 장치로, 사고 발생 
시 탑승자의 생명을 보호하는 역할을 합니다. - **문서 내 역할**: 이 이미지는 안전 및 주의 사항을 설명하는 페이지의 일부로, 안전벨트 착용 방법을 명확히 전달...
    💬 Caption: Summary:

- **주요 내용**: 이미지에는 안전벨트를 착용하는 방법이 설명되어 있습니다. 
- **주요 키워드**: 안전벨트, 착용 방법, 안전, 차량.
- **특징**: 
  - 번호가 매겨진 단계별 지침이 포함되어 있어 안전벨트를 올바르게 착용하는 방법을 시각적으로 안내합니다. 
  - 각 번호는 특정 부위를 나타내며, 사용자가 쉽게 이해할 수 있도록 도와줍니다.

  Query: '브레이크'
  Keywords: 브레이크
  Results: 10 documents
  Relevance: 60.00%
  Time: 0.003s
  Top result: paragraph (page 6)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    📝 Content: 운전할 때 하이힐 등 운전하기 불편한 신발을 신지 마십시오. 가속 페달, 브레이크 페달 등의 조작능력이 저하되어 사고의 원인이 됩니다. 전자식 파킹 브레이크를 해제할 때에는 차량이 
움직일 수 있으므로 반드시 브레이크 페달을 확실히 밟으십시오.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 3 | Category: paragraph
    📝 Content: (1) 도어 열림 레버(실내) 000 .... 5-26 (2) 승차 자세 메모리 시 스 템.................. 5-33 (3) 실외 미러 조절 스위치 .......................... .............. 5-42 (4) 실외 
미러 접이 버튼 .............................. . 5-42 ...

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 3 | Category: table
    📝 Content: ### 1. 테이블의 목적과 의미 분석 이 테이블은 차량 내부의 다양한 버튼과 스위치의 위치 및 기능을 설명하는 데 필요한 정보를 제공합니다. 각 항목은 차량의 특정 기능을 조작하는 데 
사용되는 버튼을 나타내며, 사용자가 차량을 보다 쉽게 이해하고 조작할 수 있도록 돕습니다. 이 테이블은 차량 매뉴얼의 일부분으로, 차량의 내부 구조와 기능을 설명하는 데 중...
    💬 Caption: Summary:

- **주요 내용**: 이미지에는 다양한 버튼 및 스위치의 기능과 위치에 대한 설명이 포함되어 있습니다.
- **키워드**: 도어 열림 레버, 승차 자세 메모리 시스템, 전동식 리어 커튼 버튼, 전자식 파킹 브레이크 스위치.
- **테이블 구조**: 각 항목은 번호, 기능 설명, 페이지 번호로 구성되어 있으며, 총 12개의 항목이 나열되어 있습니다.

  Query: '운전 자세'
  Keywords: 운전, 자세
  Results: 10 documents
  Relevance: 95.00%
  Time: 0.003s
  Top result: heading1 (page 6)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: heading1
    📝 Content: # 올바른 운전 자세

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: list
    📝 Content: 1. 엉덩이를 좌석 가장 안쪽으로 넣고 등을등받이에 기대어 앉으십시오. 등을 구부리거나 좌석 끝에 걸터앉지 마십시오. 2. 안전벨트의 어깨띠가 어깨와 가슴을 지나도록 하십시오. 3. 
안전벨트가 꼬이거나 짓눌리지 않게 하십시오. 4. 안전벨트의 골반띠가 골반을 부드럽게 지나도록 하십시오. 5. "찰칵" 소리가 날 때까지 버클에 밀어 넣으십시오.

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: header
    📝 Content: 안전 및 주의 사항

2. English Keyword Search Test

  Query: 'seatbelt safety'
  Results: 4 documents
  Relevance: 100.00%
  Time: 0.005s
  Top result: figure (page 6)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 - **목적**: 이 이미지는 안전벨트를 착용하는 방법을 시각적으로 설명하기 위해 필요합니다. 안전벨트는 차량 탑승 시 필수적인 안전 장치로, 사고 발생 
시 탑승자의 생명을 보호하는 역할을 합니다. - **문서 내 역할**: 이 이미지는 안전 및 주의 사항을 설명하는 페이지의 일부로, 안전벨트 착용 방법을 명확히 전달...
    💬 Caption: Summary:

- **주요 내용**: 이미지에는 안전벨트를 착용하는 방법이 설명되어 있습니다. 
- **주요 키워드**: 안전벨트, 착용 방법, 안전, 차량.
- **특징**: 
  - 번호가 매겨진 단계별 지침이 포함되어 있어 안전벨트를 올바르게 착용하는 방법을 시각적으로 안내합니다. 
  - 각 번호는 특정 부위를 나타내며, 사용자가 쉽게 이해할 수 있도록 도와줍니다.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량의 안전벨트를 착용하는 방법을 시각적으로 설명하는 역할을 합니다. 주변 텍스트와 함께, 안전한 운전을 위한 필수적인 절차를 강조하고
있습니다. 이 이미지는 문서의 안전 및 주의 사항 섹션에 위치하여, 운전자가 차량에 탑승하기 전에 반드시 숙지해야 할 내용을 전달합니다. ### 2. 시각적 구조 상세 ...
    💬 Caption: Summary:

- **주요 내용**: 이미지에는 안전벨트를 착용하는 방법이 설명되어 있습니다. 
- **주요 키워드**: 안전벨트, 착용 방법, 안전, 차량.
- **특징**: 
  - 번호가 매겨진 각 부분(1-5)은 안전벨트의 구성 요소를 나타냅니다.
  - 안전벨트의 올바른 착용을 강조하여 안전한 운전을 촉구합니다.

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 안전과 관련된 정보를 제공하기 위해 설계되었습니다. 특히, 안전벨트 착용 방법과 차량 내 안전한 자세를 강조하고 있습니다. 주변 
텍스트와 함께, 이 이미지는 운전 중 안전을 확보하기 위한 필수 지침을 전달하는 역할을 합니다. 문서 전체에서 이 이미지는 안전벨트 착용의 중요성을 강조하며, 독자가 안전하...
    💬 Caption: Summary:

- **주요 내용**: 경고 아이콘이 포함된 이미지로, 주의 또는 위험을 나타냄.
- **키워드**: 경고, 주의, 위험, 아이콘.
- **특징**: 삼각형 형태의 아이콘 안에 느낌표가 있어 시각적으로 주의를 끌도록 설계됨.

  Query: 'driving posture'
  Results: 7 documents
  Relevance: 93.33%
  Time: 0.003s
  Top result: figure (page 6)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 안전과 관련된 정보를 제공하기 위해 설계되었습니다. 특히, 안전벨트 착용 방법과 차량 내 안전한 자세를 강조하고 있습니다. 주변 
텍스트와 함께, 이 이미지는 운전 중 안전을 확보하기 위한 필수 지침을 전달하는 역할을 합니다. 문서 전체에서 이 이미지는 안전벨트 착용의 중요성을 강조하며, 독자가 안전하...
    💬 Caption: Summary:

- **주요 내용**: 경고 아이콘이 포함된 이미지로, 주의 또는 위험을 나타냄.
- **키워드**: 경고, 주의, 위험, 아이콘.
- **특징**: 삼각형 형태의 아이콘 안에 느낌표가 있어 시각적으로 주의를 끌도록 설계됨.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    📝 Content: 올바른 운전 자세가 되도록 운전석과 스티어링 휠을 조절하십시오. 바람직한 운전 자세는 좌석에 깊숙이 앉아 브레이크 페달을 끝까지 밟았을 때 무릎이 약간 굽혀지고, 손목이 스티어링 
휠의 가장 먼 곳에 닿아야 합니다. 또한, 헤드레스트의 높이가 조절되는 차량인 경우는 운전자의 귀 상단이 헤드레스트 중심에 올 수 있도록 헤드레스트를 조절하십시오.

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 4 | Category: paragraph
    📝 Content: 1일 1회 일상 점검 · .... 2-3 엔진룸 점검 2-3 규격 타이어 장착 및 타이어 공기압 수시 점검. . 2-3 클러스터 및 페달류 점검 m.... 2-3 올바른 운전 자세 . . ... 2-4 좌석, 스티어링 휠,
미러 조정. ...... 2-4 운전석 주변 점검 . ... .… . 中 2-4 안전벨트 착용 ...........

  Query: 'brake pedal'
  Results: 5 documents
  Relevance: 80.00%
  Time: 0.002s
  Top result: paragraph (page 6)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    📝 Content: 운전할 때 하이힐 등 운전하기 불편한 신발을 신지 마십시오. 가속 페달, 브레이크 페달 등의 조작능력이 저하되어 사고의 원인이 됩니다. 전자식 파킹 브레이크를 해제할 때에는 차량이 
움직일 수 있으므로 반드시 브레이크 페달을 확실히 밟으십시오.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 2 | Category: paragraph
    📝 Content: 사고기록장치는 자동차의 충돌 등 사고 전후 일정 시간 동안 자동차의 운행 정보(주행속도, 제동페달, 가속페 달 등의 작동 여부)를 저장하고, 저장된 정보를 확인할 수 있는 기능을 하는 
장치를 말합니다.

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    📝 Content: - · 전자식 파킹 브레이크를 해제할 때에는 차 량이 움직일 수 있으므로 반드시 브레이크 페달을 확실히 밟으십시오.

3. Semantic Search Test

  Query: '차량 탑승 시 반드시 지켜야 할 안전 수칙'
  Language: korean
  Results: 10 documents
  Top similarity: 0.6373
  Relevance: 53.33%
  Time: 0.613s
  Top result: paragraph (page 4)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 4 | Category: paragraph
    🎯 Similarity: 0.6373
    📝 Content: 2

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 4 | Category: heading1
    🎯 Similarity: 0.6163
    📝 Content: # 2. 안전 및 주의 사항

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    🎯 Similarity: 0.5860
    📝 Content: - · 차 주위에 사람이나 물체 등이 없는지 확 인하십시오.

  Query: 'How to properly wear a seatbelt'
  Language: english
  Results: 10 documents
  Top similarity: 0.7435
  Relevance: 40.00%
  Time: 0.443s
  Top result: heading1 (page 6)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: heading1
    🎯 Similarity: 0.7435
    📝 Content: # 안전벨트 착용

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: list
    🎯 Similarity: 0.6968
    📝 Content: 1. 엉덩이를 좌석 가장 안쪽으로 넣고 등을등받이에 기대어 앉으십시오. 등을 구부리거나 좌석 끝에 걸터앉지 마십시오. 2. 안전벨트의 어깨띠가 어깨와 가슴을 지나도록 하십시오. 3. 
안전벨트가 꼬이거나 짓눌리지 않게 하십시오. 4. 안전벨트의 골반띠가 골반을 부드럽게 지나도록 하십시오. 5. "찰칵" 소리가 날 때까지 버클에 밀어 넣으십시오.

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    🎯 Similarity: 0.6115
    📝 Content: - 2. 안전벨트의 어깨띠가 어깨와 가슴을 지나 도록 하십시오.

  Query: '운전할 때 피해야 할 신발'
  Language: korean
  Results: 10 documents
  Top similarity: 0.4829
  Relevance: 46.67%
  Time: 0.325s
  Top result: paragraph (page 6)

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    🎯 Similarity: 0.4829
    📝 Content: 운전할 때 하이힐 등 운전하기 불편한 신발을 신지 마십시오. 가속 페달, 브레이크 페달 등의 조작능력이 저하되어 사고의 원인이 됩니다. 전자식 파킹 브레이크를 해제할 때에는 차량이 
움직일 수 있으므로 반드시 브레이크 페달을 확실히 밟으십시오.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: heading1
    🎯 Similarity: 0.4156
    📝 Content: # 운전석 주변 점검

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: heading1
    🎯 Similarity: 0.4154
    📝 Content: # 안전벨트 착용

4. Filter-based Search Test

  Filter: Heading1 category filter
  Results: 20 documents
  Expected min: 1
  Status: ✅ PASS
  Time: 0.004s
  Categories found: heading1

  Top 2 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 1 | Category: heading1
    📝 Content: # 내 용 찾 기 방 법 설 명

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 1 | Category: heading1
    📝 Content: # 내용으로 찾을 때

  Filter: Figure and Table filter
  Results: 13 documents
  Expected min: 1
  Status: ✅ PASS
  Time: 0.004s
  Categories found: figure, table

  Top 2 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 1 | Category: figure
    📝 Content: 
    💬 Caption: Summary:

# 이미지 요약

- **목차**: 차량 관련 안내 및 안전 정보
- **주요 항목**:
  - 안내 및 차량 정보
  - 안전 및 주의 사항
  - 시트 및 안전 장치
  - 계기판 사용 방법
  - 편의 장치
  - 시동 및 주행
  - 비상 시 응급 조치

이 내용은 차량 사용 설명서의 목차로, 안전과 편의성을 강조하고 있습니다.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 1 | Category: table
    📝 Content: 목차를 활용하세요.
    💬 Caption: Summary:

## 이미지 요약

- **주제**: 차량 안내 및 안전 정보
- **목차 항목**:
  - 차량의 외관, 내부, 모터, 차량 정보
  - 안전 운전 및 주의 사항
  - 안전 장치 사용 방법
  - 계기판 사용 방법
  - 편의 장치 사용 방법
  - 시동 및 주행 관련 정보
  - 운전 보조 시스템 사용 방법

이 내용은 차량의 안전 및 기능에 대한 정보를 제공하는 매뉴얼의 목차로 보입니다.

  Filter: Page 6 filter
  Results: 20 documents
  Expected min: 2
  Status: ✅ PASS
  Time: 0.010s
  Categories found: figure, header, paragraph, heading1, list

  Top 2 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    📝 Content: 좌석, 스티어링 휠, 미러는 출발 전에 조절하시고 주행 중에 절대로 조작하지 마십시오. 내외측의 미러를 조정하여, 충분한 시야를 확보하십시오. 모든 게이지 및 경고등을 
확인하십시오.전자식 파킹 브레이크를 해제하고 브레이크 경고등이 꺼지는지 확인하십시오. 차 주위에 사람이나 물체 등이 없는지 확인하십시오.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    📝 Content: 운전석 주변은 항상 깨끗하게 유지하십시오. 빈 깡통 등이 페 달 밑으로 굴러 들어갈경우 페달 조작이 불가능하게 되어 매우위험합니다. 바닥 매트는 페달의 움직임을 방해하지 않는 것으로 
너무 두껍지 않으면서 바닥에고정되는 제품이어야 합니다. 차 안에는 화물을 좌석 높이 이상으로 적재하지 마십시오.

  Filter: Figure with image entity filter
  Results: 2 documents
  Expected min: 1
  Status: ✅ PASS
  Time: 0.003s
  Categories found: figure

  Top 2 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 5 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 점검 매뉴얼의 일부분으로, 차량의 엔진 및 관련 부품의 점검 절차를 안내하고 있습니다. 주변 텍스트와 함께 차량의 안전성을 확보하기
위한 점검 항목들을 제시하고 있으며, 사용자가 차량의 상태를 점검하고 이상 유무를 확인할 수 있도록 돕는 역할을 합니다. 이 이미지의 위치는 매뉴얼의 중간 부분으로, 차...
    💬 Caption: Summary:

죄송하지만 이미지를 분석할 수 없습니다. 다른 질문이나 요청이 있으시면 도와드리겠습니다.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 안전과 관련된 정보를 제공하기 위해 설계되었습니다. 특히, 안전벨트 착용 방법과 차량 내 안전한 자세를 강조하고 있습니다. 주변 
텍스트와 함께, 이 이미지는 운전 중 안전을 확보하기 위한 필수 지침을 전달하는 역할을 합니다. 문서 전체에서 이 이미지는 안전벨트 착용의 중요성을 강조하며, 독자가 안전하...
    💬 Caption: Summary:

- **주요 내용**: 경고 아이콘이 포함된 이미지로, 주의 또는 위험을 나타냄.
- **키워드**: 경고, 주의, 위험, 아이콘.
- **특징**: 삼각형 형태의 아이콘 안에 느낌표가 있어 시각적으로 주의를 끌도록 설계됨.

5. Hybrid Search Test (Semantic + Keyword)

  Query: '안전벨트 착용 방법'
  Language: korean
  Filter: Seatbelt wearing method
  Results: 10 documents
  Time: 0.493s
  Top RRF score: 0.0153
  Search types: semantic, keyword

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    🎯 Similarity: 0.5084
    📝 Content: ### 1. 이미지의 목적과 의미 분석 - **목적**: 이 이미지는 안전벨트를 착용하는 방법을 시각적으로 설명하기 위해 필요합니다. 안전벨트는 차량 탑승 시 필수적인 안전 장치로, 사고 발생 
시 탑승자의 생명을 보호하는 역할을 합니다. - **문서 내 역할**: 이 이미지는 안전 및 주의 사항을 설명하는 페이지의 일부로, 안전벨트 착용 방법을 명확히 전달...
    💬 Caption: Summary:

- **주요 내용**: 이미지에는 안전벨트를 착용하는 방법이 설명되어 있습니다. 
- **주요 키워드**: 안전벨트, 착용 방법, 안전, 차량.
- **특징**: 
  - 번호가 매겨진 단계별 지침이 포함되어 있어 안전벨트를 올바르게 착용하는 방법을 시각적으로 안내합니다. 
  - 각 번호는 특정 부위를 나타내며, 사용자가 쉽게 이해할 수 있도록 도와줍니다.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    🎯 Similarity: 0.5016
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량의 안전벨트를 착용하는 방법을 시각적으로 설명하는 역할을 합니다. 주변 텍스트와 함께, 안전한 운전을 위한 필수적인 절차를 강조하고
있습니다. 이 이미지는 문서의 안전 및 주의 사항 섹션에 위치하여, 운전자가 차량에 탑승하기 전에 반드시 숙지해야 할 내용을 전달합니다. ### 2. 시각적 구조 상세 ...
    💬 Caption: Summary:

- **주요 내용**: 이미지에는 안전벨트를 착용하는 방법이 설명되어 있습니다. 
- **주요 키워드**: 안전벨트, 착용 방법, 안전, 차량.
- **특징**: 
  - 번호가 매겨진 각 부분(1-5)은 안전벨트의 구성 요소를 나타냅니다.
  - 안전벨트의 올바른 착용을 강조하여 안전한 운전을 촉구합니다.

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: header
    🎯 Similarity: 0.5118
    📝 Content: 안전 및 주의 사항

  Query: 'vehicle safety instructions'
  Language: english
  Filter: Safety instructions with category filter
  Results: 10 documents
  Time: 0.357s
  Top RRF score: 0.0082
  Search types: semantic

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 4 | Category: paragraph
    🎯 Similarity: 0.5729
    📝 Content: 1일 1회 일상 점검 · .... 2-3 엔진룸 점검 2-3 규격 타이어 장착 및 타이어 공기압 수시 점검. . 2-3 클러스터 및 페달류 점검 m.... 2-3 올바른 운전 자세 . . ... 2-4 좌석, 스티어링 휠,
미러 조정. ...... 2-4 운전석 주변 점검 . ... .… . 中 2-4 안전벨트 착용 ...........

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 2 | Category: paragraph
    🎯 Similarity: 0.5283
    📝 Content: - ㆍ 한 국 교통 안전 공 단 자 동 차안 전연 구 원

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 1 | Category: paragraph
    🎯 Similarity: 0.5183
    📝 Content: ABS 경고5

  Query: '브레이크 페달'
  Language: korean
  Filter: Brake pedal on specific page
  Results: 10 documents
  Time: 0.284s
  Top RRF score: 0.0163
  Search types: semantic, keyword

  Top 3 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: paragraph
    🎯 Similarity: 0.3572
    📝 Content: 운전할 때 하이힐 등 운전하기 불편한 신발을 신지 마십시오. 가속 페달, 브레이크 페달 등의 조작능력이 저하되어 사고의 원인이 됩니다. 전자식 파킹 브레이크를 해제할 때에는 차량이 
움직일 수 있으므로 반드시 브레이크 페달을 확실히 밟으십시오.

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: heading1
    🎯 Similarity: 0.2240
    📝 Content: # 모든 좌석의 탑승자들은 가까운 거리라도 주행 전에 반드시 안전벨트를 착용하십시오.

  Result 3:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: heading1
    🎯 Similarity: 0.2342
    📝 Content: # 좌석, 스티어링 휠, 미러 조정

6. Entity-based Search Test

  Filter: Search for image entities
  Entity filter: {'type': 'image'}
  Results: 2 documents
  Time: 0.003s
  Sample entities:
    - image: 냉각수 점검의 중요성
    - image: 안전한 운전을 위한 기본 수칙

  Top 2 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 5 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 점검 매뉴얼의 일부분으로, 차량의 엔진 및 관련 부품의 점검 절차를 안내하고 있습니다. 주변 텍스트와 함께 차량의 안전성을 확보하기
위한 점검 항목들을 제시하고 있으며, 사용자가 차량의 상태를 점검하고 이상 유무를 확인할 수 있도록 돕는 역할을 합니다. 이 이미지의 위치는 매뉴얼의 중간 부분으로, 차...
    🏷️  Entity Type: image
    🏷️  Entity Title: 냉각수 점검의 중요성

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 안전과 관련된 정보를 제공하기 위해 설계되었습니다. 특히, 안전벨트 착용 방법과 차량 내 안전한 자세를 강조하고 있습니다. 주변 
텍스트와 함께, 이 이미지는 운전 중 안전을 확보하기 위한 필수 지침을 전달하는 역할을 합니다. 문서 전체에서 이 이미지는 안전벨트 착용의 중요성을 강조하며, 독자가 안전하...
    🏷️  Entity Type: image
    🏷️  Entity Title: 안전한 운전을 위한 기본 수칙

  Filter: Search by entity keywords
  Entity filter: {'keywords': ['안전벨트']}
  Results: 1 documents
  Time: 0.003s
  Sample entities:
    - image: 안전한 운전을 위한 기본 수칙

  Top 1 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 안전과 관련된 정보를 제공하기 위해 설계되었습니다. 특히, 안전벨트 착용 방법과 차량 내 안전한 자세를 강조하고 있습니다. 주변 
텍스트와 함께, 이 이미지는 운전 중 안전을 확보하기 위한 필수 지침을 전달하는 역할을 합니다. 문서 전체에서 이 이미지는 안전벨트 착용의 중요성을 강조하며, 독자가 안전하...
    🏷️  Entity Type: image
    🏷️  Entity Title: 안전한 운전을 위한 기본 수칙

  Filter: Search by entity title
  Entity filter: {'title': '안전'}
  Results: 2 documents
  Time: 0.003s
  Sample entities:
    - table: 차량 안전 및 사용 안내
    - image: 안전한 운전을 위한 기본 수칙

  Top 2 Results:

  Result 1:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 1 | Category: table
    📝 Content: Table (from tables_json, image: gv80_owners_manual_TEST6P_0000_0001-page-1-table-2.png)
    🏷️  Entity Type: table
    🏷️  Entity Title: 차량 안전 및 사용 안내

  Result 2:
    📄 Source: data/gv80_owners_manual_TEST6P.pdf
    📍 Page: 6 | Category: figure
    📝 Content: ### 1. 이미지의 목적과 의미 분석 이 이미지는 차량 안전과 관련된 정보를 제공하기 위해 설계되었습니다. 특히, 안전벨트 착용 방법과 차량 내 안전한 자세를 강조하고 있습니다. 주변 
텍스트와 함께, 이 이미지는 운전 중 안전을 확보하기 위한 필수 지침을 전달하는 역할을 합니다. 문서 전체에서 이 이미지는 안전벨트 착용의 중요성을 강조하며, 독자가 안전하...
    🏷️  Entity Type: image
    🏷️  Entity Title: 안전한 운전을 위한 기본 수칙

7. Performance Test

  Simple Query Performance
    '안전벨트': 10 results in 0.0053s
    '브레이크': 10 results in 0.0036s
    '운전': 10 results in 0.0041s
    '주차': 2 results in 0.0035s
    '좌석': 10 results in 0.0033s
    Average: 8.4 results in 0.0040s

  Vector Search Performance
    Vector search time: 0.0039s

  Complex Filter Performance
    Complex filter time: 0.0025s

═══ Test Results Summary ═══

              Retrieval System Test Results               
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Test Category          ┃ Tests Run ┃ Avg Time ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ Korean Keyword Search  │     3     │  0.448s  │   ✅   │
│ English Keyword Search │     3     │  0.003s  │   ✅   │
│ Semantic Search        │     3     │  0.461s  │   ✅   │
│ Filter Search          │     4     │  0.005s  │   ✅   │
│ Hybrid Search          │     3     │  0.378s  │   ✅   │
│ Entity Search          │     3     │  0.003s  │   ✅   │
│ Performance            │     3     │  0.003s  │   ✅   │
└────────────────────────┴───────────┴──────────┴────────┘

Key Findings:
  • Korean search avg relevance: 80.6%
  • Semantic search avg similarity: 0.621
  • Filter tests passed: 4/4

Recommendations:
  ✅ Simple Query performance is good (0.004s)
  ✅ Vector Search performance is good (0.004s)
  ✅ Complex Filter performance is good (0.003s)

✅ Test completed

administrator@DESKTOP-VTUOR4O:/mnt/e/MyProject2/multimodal-rag-wsl-v2/scripts$ uv run python test_entity_filter_only.py

Entity Filter Only Test
============================================================

Test: Only entity type=image filter (no category filter)
  SQL WHERE: (entity->>'type' = $1)
  Parameters: ['image']
  Results: 2 documents found
  Categories: {'figure': 2}
  Entity types: {'image': 2}

  Sample Results:

  Result 1:
    ID: 89
    Category: figure
    Page: 5
    Entity Type: image
    Entity Title: 냉각수 점검의 중요성...
    Entity Keywords: ['냉각수', '엔진', '보조 탱크']

  Result 2:
    ID: 114
    Category: figure
    Page: 6
    Entity Type: image
    Entity Title: 안전한 운전을 위한 기본 수칙...
    Entity Keywords: ['운전', '안전벨트', '전자식 파킹 브레이크']
------------------------------------------------------------

Test: Only entity type=table filter
  SQL WHERE: (entity->>'type' = $1)
  Parameters: ['table']
  Results: 2 documents found
  Categories: {'table': 2}
  Entity types: {'table': 2}

  Sample Results:

  Result 1:
    ID: 30
    Category: table
    Page: 1
    Entity Type: table
    Entity Title: 차량 안전 및 사용 안내...
    Entity Keywords: ['안내 및 차량 정보', '안전 및 주의 사항', '안전 장치']

  Result 2:
    ID: 52
    Category: table
    Page: 3
    Entity Type: table
    Entity Title: 전기 시스템 버튼 설명...
    Entity Keywords: ['도어 열림 레버', '승차 자세 메모리 시스템', '실외 미러 조절 스위치']
------------------------------------------------------------

Test: Only entity keywords filter
  SQL WHERE: (entity->'keywords' ?| $1)
  Parameters: [['안전벨트']]
  Results: 1 documents found
  Categories: {'figure': 1}
  Entity types: {'image': 1}

  Sample Results:

  Result 1:
    ID: 114
    Category: figure
    Page: 6
    Entity Type: image
    Entity Title: 안전한 운전을 위한 기본 수칙...
    Entity Keywords: ['운전', '안전벨트', '전자식 파킹 브레이크']
------------------------------------------------------------

Test: Only entity title filter
  SQL WHERE: (entity->>'title' ILIKE $1)
  Parameters: ['%안전%']
  Results: 2 documents found
  Categories: {'table': 1, 'figure': 1}
  Entity types: {'table': 1, 'image': 1}

  Sample Results:

  Result 1:
    ID: 30
    Category: table
    Page: 1
    Entity Type: table
    Entity Title: 차량 안전 및 사용 안내...
    Entity Keywords: ['안내 및 차량 정보', '안전 및 주의 사항', '안전 장치']

  Result 2:
    ID: 114
    Category: figure
    Page: 6
    Entity Type: image
    Entity Title: 안전한 운전을 위한 기본 수칙...
    Entity Keywords: ['운전', '안전벨트', '전자식 파킹 브레이크']
------------------------------------------------------------

Test: Combined: figure category + image entity
  SQL WHERE: category = ANY($1) AND (entity->>'type' = $2)
  Parameters: [['figure'], 'image']
  Results: 2 documents found
  Categories: {'figure': 2}
  Entity types: {'image': 2}

  Sample Results:

  Result 1:
    ID: 89
    Category: figure
    Page: 5
    Entity Type: image
    Entity Title: 냉각수 점검의 중요성...
    Entity Keywords: ['냉각수', '엔진', '보조 탱크']

  Result 2:
    ID: 114
    Category: figure
    Page: 6
    Entity Type: image
    Entity Title: 안전한 운전을 위한 기본 수칙...
    Entity Keywords: ['운전', '안전벨트', '전자식 파킹 브레이크']
------------------------------------------------------------

Test: Empty entity filter (should return all with entity)
  SQL WHERE: 1=1
  Parameters: []
  Results: 20 documents found
  Categories: {'heading1': 2, 'figure': 2, 'table': 1, 'caption': 2, 'paragraph': 13}
  Entity types: {}

  Sample Results:

  Result 1:
    ID: 1
    Category: heading1
    Page: 1
    Entity Type: N/A

  Result 2:
    ID: 2
    Category: heading1
    Page: 1
    Entity Type: N/A

  Result 3:
    ID: 3
    Category: figure
    Page: 1
    Entity Type: N/A
------------------------------------------------------------

Overall Entity Statistics:
  Total documents with entity: 122

  Entity type distribution:
    NULL: 118 documents
    table: 2 documents
    image: 2 documents

✅ Test completed