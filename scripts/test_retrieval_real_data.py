"""
Retrieval System Test with Real Database Data
실제 DB에 저장된 문서를 대상으로 다양한 검색 기능을 테스트
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any
import numpy as np
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.panel import Panel

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from ingest.database import DatabaseManager
from ingest.embeddings import DualLanguageEmbeddings
from retrieval.search_filter import MVPSearchFilter
from retrieval.hybrid_search import HybridSearch

# .env 파일 로드
load_dotenv()

console = Console()


class RetrievalTester:
    """검색 시스템 테스터"""
    
    def __init__(self):
        self.db_manager = None
        self.hybrid_search = None
        self.embeddings = DualLanguageEmbeddings()
        self.test_results = []
    
    async def initialize(self):
        """초기화"""
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        self.hybrid_search = HybridSearch(self.db_manager.pool)
    
    async def cleanup(self):
        """정리"""
        if self.db_manager:
            await self.db_manager.close()
    
    def calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        if not vec1 or not vec2:
            return 0.0
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        return np.dot(vec1_np, vec2_np) / (np.linalg.norm(vec1_np) * np.linalg.norm(vec2_np))
    
    def print_detailed_results(self, results: List[Dict], max_display: int = 3, show_entity: bool = False):
        """검색 결과 상세 출력"""
        if not results:
            console.print("    [yellow]No results found[/yellow]")
            return
        
        console.print(f"\n  [green]Top {min(max_display, len(results))} Results:[/green]")
        
        for i, result in enumerate(results[:max_display], 1):
            console.print(f"\n  [bold]Result {i}:[/bold]")
            console.print(f"    📄 Source: {result.get('source', 'N/A')}")
            console.print(f"    📍 Page: {result.get('page', 'N/A')} | Category: {result.get('category', 'N/A')}")
            
            # 점수 정보 (있는 경우)
            if 'similarity' in result:
                console.print(f"    🎯 Similarity: {result['similarity']:.4f}")
            elif 'rank' in result:
                console.print(f"    🎯 Rank: {result['rank']:.4f}")
            elif 'rrf_score' in result:
                console.print(f"    🎯 RRF Score: {result['rrf_score']:.4f}")
            
            # 콘텐츠 표시
            content = result.get('page_content', '')
            if not content:
                content = result.get('translation_text', '')
            if not content:
                content = result.get('contextualize_text', '')
            
            if content:
                # 내용을 200자로 제한하여 표시
                display_content = content[:200] + "..." if len(content) > 200 else content
                # 줄바꿈 제거하여 깔끔하게 표시
                display_content = ' '.join(display_content.split())
                console.print(f"    📝 Content: [dim]{display_content}[/dim]")
            
            # 캡션 (있는 경우)
            if result.get('caption'):
                console.print(f"    💬 Caption: [cyan]{result['caption']}[/cyan]")
            
            # Entity 정보 (요청된 경우)
            if show_entity and result.get('entity'):
                try:
                    entity_data = json.loads(result['entity']) if isinstance(result['entity'], str) else result['entity']
                    if entity_data:
                        console.print(f"    🏷️  Entity Type: {entity_data.get('type', 'N/A')}")
                        if entity_data.get('title'):
                            console.print(f"    🏷️  Entity Title: {entity_data.get('title', '')[:100]}")
                except:
                    pass
    
    def evaluate_results(self, results: List[Dict], expected_keywords: List[str], test_name: str, language: str = "korean") -> Dict:
        """검색 결과 평가"""
        evaluation = {
            "test_name": test_name,
            "total_results": len(results),
            "keyword_matches": 0,
            "relevance_score": 0.0,
            "top_results": []
        }
        
        if not results:
            return evaluation
        
        # 키워드 매칭 확인
        for result in results[:5]:  # 상위 5개만 확인
            # 언어에 따라 적절한 필드 선택
            if language == "english":
                # 영어 검색은 translation_text 필드 확인
                content = result.get('translation_text', '') + ' ' + result.get('caption', '')
            else:
                # 한국어 검색은 page_content와 contextualize_text 확인
                content = result.get('page_content', '') + ' ' + result.get('contextualize_text', '')
            
            content_lower = content.lower()
            
            matches = sum(1 for keyword in expected_keywords if keyword.lower() in content_lower)
            evaluation["keyword_matches"] += matches
            
            # 상위 결과 저장
            evaluation["top_results"].append({
                "id": result.get('id'),
                "category": result.get('category'),
                "page": result.get('page'),
                "snippet": content[:100] + "..." if len(content) > 100 else content
            })
        
        # 관련성 점수 계산 (키워드 매칭 비율)
        if expected_keywords and results:
            max_possible_matches = len(expected_keywords) * min(5, len(results))
            evaluation["relevance_score"] = evaluation["keyword_matches"] / max_possible_matches if max_possible_matches > 0 else 0
        
        return evaluation
    
    async def test_korean_keyword_search(self):
        """한국어 키워드 검색 테스트"""
        console.print("\n[bold cyan]1. Korean Keyword Search Test[/bold cyan]")
        
        test_queries = [
            {
                "query": "안전벨트",
                "expected_keywords": ["안전벨트", "착용", "좌석"],
                "description": "Safety belt search"
            },
            {
                "query": "브레이크",
                "expected_keywords": ["브레이크", "페달", "주차"],
                "description": "Brake system search"
            },
            {
                "query": "운전 자세",
                "expected_keywords": ["운전", "자세", "좌석", "등받이"],
                "description": "Driving posture search"
            }
        ]
        
        results_summary = []
        
        for test in test_queries:
            start_time = time.time()
            
            # 키워드 검색 실행
            async with self.db_manager.pool.acquire() as conn:
                # Kiwi 토크나이저로 키워드 추출
                keywords = self.hybrid_search._extract_korean_keywords(test["query"])
                
                if keywords:
                    # 키워드 기반 검색
                    search_query = ' & '.join(keywords)
                    
                    results = await conn.fetch("""
                        SELECT id, source, page, category, page_content, 
                               contextualize_text, caption, entity
                        FROM mvp_ddu_documents
                        WHERE search_vector_korean @@ to_tsquery('simple', $1)
                        ORDER BY ts_rank(search_vector_korean, to_tsquery('simple', $1)) DESC
                        LIMIT 10
                    """, search_query)
                    
                    elapsed = time.time() - start_time
                    
                    # 결과 평가
                    results_list = [dict(r) for r in results]
                    evaluation = self.evaluate_results(results_list, test["expected_keywords"], test["description"], language="korean")
                    evaluation["query"] = test["query"]
                    evaluation["time"] = elapsed
                    evaluation["keywords_extracted"] = keywords
                    
                    results_summary.append(evaluation)
                    
                    # 결과 출력
                    console.print(f"\n  Query: '{test['query']}'")
                    console.print(f"  Keywords: {', '.join(keywords)}")
                    console.print(f"  Results: {len(results)} documents")
                    console.print(f"  Relevance: {evaluation['relevance_score']:.2%}")
                    console.print(f"  Time: {elapsed:.3f}s")
                    
                    if results:
                        console.print(f"  Top result: {results[0]['category']} (page {results[0]['page']})")
                    
                    # 상세 결과 출력
                    self.print_detailed_results(results_list)
        
        self.test_results.append(("Korean Keyword Search", results_summary))
        return results_summary
    
    async def test_english_keyword_search(self):
        """영어 키워드 검색 테스트"""
        console.print("\n[bold cyan]2. English Keyword Search Test[/bold cyan]")
        
        test_queries = [
            {
                "query": "seatbelt safety",
                "expected_keywords": ["seatbelt", "safety", "wear"],
                "description": "Seatbelt safety search"
            },
            {
                "query": "driving posture",
                "expected_keywords": ["driving", "posture", "seat"],
                "description": "Driving posture search"
            },
            {
                "query": "brake pedal",
                "expected_keywords": ["brake", "pedal", "parking"],
                "description": "Brake pedal search"
            }
        ]
        
        results_summary = []
        
        for test in test_queries:
            start_time = time.time()
            
            # 영어 키워드 검색
            async with self.db_manager.pool.acquire() as conn:
                keywords = test["query"].lower().split()
                search_query = ' & '.join(keywords)
                
                results = await conn.fetch("""
                    SELECT id, source, page, category, page_content,
                           translation_text, caption, entity
                    FROM mvp_ddu_documents
                    WHERE search_vector_english @@ to_tsquery('english', $1)
                    ORDER BY ts_rank(search_vector_english, to_tsquery('english', $1)) DESC
                    LIMIT 10
                """, search_query)
                
                elapsed = time.time() - start_time
                
                # 결과 평가
                results_list = [dict(r) for r in results]
                evaluation = self.evaluate_results(
                    results_list, 
                    test["expected_keywords"], 
                    test["description"],
                    language="english"
                )
                evaluation["query"] = test["query"]
                evaluation["time"] = elapsed
                
                results_summary.append(evaluation)
                
                # 결과 출력
                console.print(f"\n  Query: '{test['query']}'")
                console.print(f"  Results: {len(results)} documents")
                console.print(f"  Relevance: {evaluation['relevance_score']:.2%}")
                console.print(f"  Time: {elapsed:.3f}s")
                
                if results:
                    console.print(f"  Top result: {results[0]['category']} (page {results[0]['page']})")
                
                # 상세 결과 출력
                self.print_detailed_results(results_list)
        
        self.test_results.append(("English Keyword Search", results_summary))
        return results_summary
    
    async def test_semantic_search(self):
        """시맨틱 검색 테스트"""
        console.print("\n[bold cyan]3. Semantic Search Test[/bold cyan]")
        
        test_queries = [
            {
                "query": "차량 탑승 시 반드시 지켜야 할 안전 수칙",
                "language": "korean",
                "expected_keywords": ["안전벨트", "착용", "주행"],
                "description": "Safety rules semantic search"
            },
            {
                "query": "How to properly wear a seatbelt",
                "language": "english",
                "expected_keywords": ["seatbelt", "wear", "properly"],
                "description": "Seatbelt instruction semantic search"
            },
            {
                "query": "운전할 때 피해야 할 신발",
                "language": "korean",
                "expected_keywords": ["하이힐", "신발", "운전"],
                "description": "Driving shoes semantic search"
            }
        ]
        
        results_summary = []
        
        for test in test_queries:
            start_time = time.time()
            
            # 쿼리 임베딩 생성
            if test["language"] == "korean":
                query_embedding = await self.embeddings.embeddings.aembed_query(test["query"])
                embedding_column = "embedding_korean"
            else:
                query_embedding = await self.embeddings.embeddings.aembed_query(test["query"])
                embedding_column = "embedding_english"
            
            # 벡터 유사도 검색
            async with self.db_manager.pool.acquire() as conn:
                # 임베딩을 문자열로 변환
                embedding_str = f"[{','.join(map(str, query_embedding))}]"
                
                results = await conn.fetch(f"""
                    SELECT id, source, page, category, page_content,
                           contextualize_text, translation_text, caption, entity,
                           1 - ({embedding_column} <=> $1::vector) as similarity
                    FROM mvp_ddu_documents
                    WHERE {embedding_column} IS NOT NULL
                    ORDER BY {embedding_column} <=> $1::vector
                    LIMIT 10
                """, embedding_str)
                
                elapsed = time.time() - start_time
                
                # 결과 평가
                results_list = [dict(r) for r in results]
                evaluation = self.evaluate_results(
                    results_list,
                    test["expected_keywords"],
                    test["description"],
                    language=test["language"]
                )
                evaluation["query"] = test["query"]
                evaluation["language"] = test["language"]
                evaluation["time"] = elapsed
                
                if results:
                    evaluation["top_similarity"] = float(results[0]['similarity'])
                
                results_summary.append(evaluation)
                
                # 결과 출력
                console.print(f"\n  Query: '{test['query']}'")
                console.print(f"  Language: {test['language']}")
                console.print(f"  Results: {len(results)} documents")
                
                if results:
                    console.print(f"  Top similarity: {results[0]['similarity']:.4f}")
                    console.print(f"  Relevance: {evaluation['relevance_score']:.2%}")
                    console.print(f"  Time: {elapsed:.3f}s")
                    console.print(f"  Top result: {results[0]['category']} (page {results[0]['page']})")
                
                # 상세 결과 출력
                self.print_detailed_results(results_list)
        
        self.test_results.append(("Semantic Search", results_summary))
        return results_summary
    
    async def test_filter_search(self):
        """필터 기반 검색 테스트"""
        console.print("\n[bold cyan]4. Filter-based Search Test[/bold cyan]")
        
        test_filters = [
            {
                "filter": MVPSearchFilter(categories=["heading1"]),
                "description": "Heading1 category filter",
                "expected_count_min": 1
            },
            {
                "filter": MVPSearchFilter(categories=["figure", "table"]),
                "description": "Figure and Table filter",
                "expected_count_min": 1
            },
            {
                "filter": MVPSearchFilter(pages=[6]),
                "description": "Page 6 filter",
                "expected_count_min": 2
            },
            {
                "filter": MVPSearchFilter(
                    #categories=["figure"],
                    entity={"type": "image"}
                ),
                "description": "Figure with image entity filter",
                "expected_count_min": 1
            }
        ]
        
        results_summary = []
        
        for test in test_filters:
            start_time = time.time()
            
            # asyncpg용 SQL 생성
            where_clause, params = test["filter"].to_sql_where_asyncpg()
            
            async with self.db_manager.pool.acquire() as conn:
                # 필터링된 검색
                results = await conn.fetch(f"""
                    SELECT id, source, page, category, page_content,
                           contextualize_text, caption, entity
                    FROM mvp_ddu_documents
                    WHERE {where_clause}
                    ORDER BY id
                    LIMIT 20
                """, *params)
                
                elapsed = time.time() - start_time
                
                # 결과 평가
                evaluation = {
                    "description": test["description"],
                    "filter": test["filter"].to_dict(),
                    "total_results": len(results),
                    "expected_min": test["expected_count_min"],
                    "passed": len(results) >= test["expected_count_min"],
                    "time": elapsed
                }
                
                if results:
                    evaluation["sample_results"] = [
                        {
                            "id": r["id"],
                            "category": r["category"],
                            "page": r["page"]
                        } for r in results[:3]
                    ]
                
                results_summary.append(evaluation)
                
                # 결과 출력
                console.print(f"\n  Filter: {test['description']}")
                console.print(f"  Results: {len(results)} documents")
                console.print(f"  Expected min: {test['expected_count_min']}")
                console.print(f"  Status: {'✅ PASS' if evaluation['passed'] else '❌ FAIL'}")
                console.print(f"  Time: {elapsed:.3f}s")
                
                if results:
                    categories = set(r['category'] for r in results)
                    console.print(f"  Categories found: {', '.join(categories)}")
                    
                    # 상세 결과 출력 (필터 테스트는 간단히 2개만)
                    self.print_detailed_results([dict(r) for r in results], max_display=2)
        
        self.test_results.append(("Filter Search", results_summary))
        return results_summary
    
    async def test_hybrid_search(self):
        """하이브리드 검색 테스트"""
        console.print("\n[bold cyan]5. Hybrid Search Test (Semantic + Keyword)[/bold cyan]")
        
        test_cases = [
            {
                "query": "안전벨트 착용 방법",
                "filter": MVPSearchFilter(),
                "language": "korean",
                "description": "Seatbelt wearing method"
            },
            {
                "query": "vehicle safety instructions",
                "filter": MVPSearchFilter(categories=["heading1", "paragraph"]),
                "language": "english",
                "description": "Safety instructions with category filter"
            },
            {
                "query": "브레이크 페달",
                "filter": MVPSearchFilter(pages=[6]),
                "language": "korean",
                "description": "Brake pedal on specific page"
            }
        ]
        
        results_summary = []
        
        for test in test_cases:
            start_time = time.time()
            
            # 하이브리드 검색 실행
            results = await self.hybrid_search.search(
                query=test["query"],
                filter=test["filter"],
                language=test["language"],
                top_k=10,
                semantic_weight=0.5,
                keyword_weight=0.5
            )
            
            elapsed = time.time() - start_time
            
            # 결과 평가
            evaluation = {
                "description": test["description"],
                "query": test["query"],
                "language": test["language"],
                "filter": test["filter"].to_dict() if not test["filter"].is_empty() else "No filter",
                "total_results": len(results),
                "time": elapsed
            }
            
            if results:
                evaluation["top_results"] = []
                for r in results[:3]:
                    evaluation["top_results"].append({
                        "id": r.get("id"),
                        "category": r.get("category"),
                        "page": r.get("page"),
                        "rrf_score": r.get("rrf_score", 0),
                        "search_types": r.get("search_types", [])
                    })
            
            results_summary.append(evaluation)
            
            # 결과 출력
            console.print(f"\n  Query: '{test['query']}'")
            console.print(f"  Language: {test['language']}")
            console.print(f"  Filter: {test['description']}")
            console.print(f"  Results: {len(results)} documents")
            console.print(f"  Time: {elapsed:.3f}s")
            
            if results and "rrf_score" in results[0]:
                console.print(f"  Top RRF score: {results[0]['rrf_score']:.4f}")
                console.print(f"  Search types: {', '.join(results[0].get('search_types', []))}")
            
            # 상세 결과 출력
            self.print_detailed_results(results)
        
        self.test_results.append(("Hybrid Search", results_summary))
        return results_summary
    
    async def test_entity_search(self):
        """Entity 기반 검색 테스트"""
        console.print("\n[bold cyan]6. Entity-based Search Test[/bold cyan]")
        
        test_cases = [
            {
                "entity_filter": {"type": "image"},
                "description": "Search for image entities"
            },
            {
                "entity_filter": {"keywords": ["안전벨트"]},
                "description": "Search by entity keywords"
            },
            {
                "entity_filter": {"title": "안전"},
                "description": "Search by entity title"
            }
        ]
        
        results_summary = []
        
        for test in test_cases:
            start_time = time.time()
            
            # Entity 필터 생성
            filter = MVPSearchFilter(entity=test["entity_filter"])
            where_clause, params = filter.to_sql_where_asyncpg()
            
            async with self.db_manager.pool.acquire() as conn:
                results = await conn.fetch(f"""
                    SELECT id, source, page, category, entity,
                           page_content, contextualize_text
                    FROM mvp_ddu_documents
                    WHERE {where_clause}
                    LIMIT 10
                """, *params)
                
                elapsed = time.time() - start_time
                
                # 결과 평가
                evaluation = {
                    "description": test["description"],
                    "entity_filter": test["entity_filter"],
                    "total_results": len(results),
                    "time": elapsed
                }
                
                if results:
                    evaluation["entities_found"] = []
                    for r in results[:3]:
                        if r["entity"]:
                            entity_data = json.loads(r["entity"]) if isinstance(r["entity"], str) else r["entity"]
                            evaluation["entities_found"].append({
                                "id": r["id"],
                                "category": r["category"],
                                "entity_type": entity_data.get("type", "N/A"),
                                "entity_title": entity_data.get("title", "N/A")[:50]
                            })
                
                results_summary.append(evaluation)
                
                # 결과 출력
                console.print(f"\n  Filter: {test['description']}")
                console.print(f"  Entity filter: {test['entity_filter']}")
                console.print(f"  Results: {len(results)} documents")
                console.print(f"  Time: {elapsed:.3f}s")
                
                if evaluation.get("entities_found"):
                    console.print(f"  Sample entities:")
                    for entity in evaluation["entities_found"]:
                        console.print(f"    - {entity['entity_type']}: {entity['entity_title']}")
                
                # 상세 결과 출력 (Entity 정보 포함)
                if results:
                    self.print_detailed_results([dict(r) for r in results], max_display=2, show_entity=True)
        
        self.test_results.append(("Entity Search", results_summary))
        return results_summary
    
    async def test_performance(self):
        """성능 테스트"""
        console.print("\n[bold cyan]7. Performance Test[/bold cyan]")
        
        performance_results = []
        
        # 1. 단순 쿼리 성능
        console.print("\n  [yellow]Simple Query Performance[/yellow]")
        
        queries = ["안전벨트", "브레이크", "운전", "주차", "좌석"]
        times = []
        result_counts = []
        
        for query in queries:
            start = time.time()
            
            async with self.db_manager.pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT id, page, category, page_content FROM mvp_ddu_documents
                    WHERE page_content ILIKE $1
                    LIMIT 10
                """, f"%{query}%")
            
            elapsed = time.time() - start
            times.append(elapsed)
            result_counts.append(len(results))
            console.print(f"    '{query}': {len(results)} results in {elapsed:.4f}s")
        
        avg_time = np.mean(times)
        avg_results = np.mean(result_counts)
        console.print(f"    Average: {avg_results:.1f} results in {avg_time:.4f}s")
        performance_results.append(("Simple Query", avg_time))
        
        # 2. 벡터 검색 성능
        console.print("\n  [yellow]Vector Search Performance[/yellow]")
        
        test_embedding = [np.random.random() for _ in range(1536)]
        embedding_str = f"[{','.join(map(str, test_embedding))}]"
        
        start = time.time()
        async with self.db_manager.pool.acquire() as conn:
            await conn.fetch("""
                SELECT id FROM mvp_ddu_documents
                WHERE embedding_korean IS NOT NULL
                ORDER BY embedding_korean <=> $1::vector
                LIMIT 10
            """, embedding_str)
        
        vector_time = time.time() - start
        console.print(f"    Vector search time: {vector_time:.4f}s")
        performance_results.append(("Vector Search", vector_time))
        
        # 3. 복잡한 필터 성능
        console.print("\n  [yellow]Complex Filter Performance[/yellow]")
        
        complex_filter = MVPSearchFilter(
            categories=["paragraph", "heading1"],
            pages=[1, 2, 3, 4, 5, 6],
            entity={"type": "image"}
        )
        
        where_clause, params = complex_filter.to_sql_where_asyncpg()
        
        start = time.time()
        async with self.db_manager.pool.acquire() as conn:
            await conn.fetch(f"""
                SELECT id FROM mvp_ddu_documents
                WHERE {where_clause}
            """, *params)
        
        filter_time = time.time() - start
        console.print(f"    Complex filter time: {filter_time:.4f}s")
        performance_results.append(("Complex Filter", filter_time))
        
        self.test_results.append(("Performance", performance_results))
        return performance_results
    
    def generate_report(self):
        """테스트 결과 리포트 생성"""
        console.print("\n[bold magenta]═══ Test Results Summary ═══[/bold magenta]\n")
        
        # 전체 테스트 결과 테이블
        table = Table(title="Retrieval System Test Results")
        table.add_column("Test Category", style="cyan")
        table.add_column("Tests Run", justify="center")
        table.add_column("Avg Time", justify="center")
        table.add_column("Status", justify="center")
        
        for category, results in self.test_results:
            if category == "Performance":
                avg_time = np.mean([r[1] for r in results])
                status = "✅" if avg_time < 0.5 else "⚠️"
                table.add_row(
                    category,
                    str(len(results)),
                    f"{avg_time:.3f}s",
                    status
                )
            else:
                if results:
                    avg_time = np.mean([r.get("time", 0) for r in results])
                    # 성공 기준: 결과가 있고 시간이 적절함
                    all_pass = all(
                        r.get("total_results", 0) > 0 or r.get("passed", False)
                        for r in results
                    )
                    status = "✅" if all_pass else "⚠️"
                    
                    table.add_row(
                        category,
                        str(len(results)),
                        f"{avg_time:.3f}s",
                        status
                    )
        
        console.print(table)
        
        # 주요 발견사항
        console.print("\n[bold]Key Findings:[/bold]")
        
        findings = []
        
        # 각 테스트 카테고리별 분석
        for category, results in self.test_results:
            if category == "Korean Keyword Search" and results:
                avg_relevance = np.mean([r.get("relevance_score", 0) for r in results])
                findings.append(f"  • Korean search avg relevance: {avg_relevance:.1%}")
            
            elif category == "Semantic Search" and results:
                if any("top_similarity" in r for r in results):
                    avg_similarity = np.mean([r.get("top_similarity", 0) for r in results if "top_similarity" in r])
                    findings.append(f"  • Semantic search avg similarity: {avg_similarity:.3f}")
            
            elif category == "Filter Search" and results:
                passed = sum(1 for r in results if r.get("passed", False))
                findings.append(f"  • Filter tests passed: {passed}/{len(results)}")
        
        for finding in findings:
            console.print(finding)
        
        # 권장사항
        console.print("\n[bold]Recommendations:[/bold]")
        
        # 성능 분석
        perf_results = dict(self.test_results).get("Performance", [])
        if perf_results:
            for test_name, test_time in perf_results:
                if test_time > 0.5:
                    console.print(f"  ⚠️  {test_name} is slow ({test_time:.3f}s) - consider optimization")
                else:
                    console.print(f"  ✅ {test_name} performance is good ({test_time:.3f}s)")
        
        return self.test_results


async def main():
    """메인 실행 함수"""
    console.print(Panel.fit(
        "[bold cyan]Retrieval System Test with Real Data[/bold cyan]\n"
        "Testing search functionality with actual database content",
        title="🔍 Retrieval Test Suite"
    ))
    
    tester = RetrievalTester()
    
    try:
        await tester.initialize()
        
        # 데이터베이스 상태 확인
        stats = await tester.db_manager.get_table_stats()
        console.print(f"\n[bold]Database Status:[/bold]")
        console.print(f"  Total documents: {stats['total_documents']}")
        console.print(f"  Categories: {', '.join(f'{k}({v})' for k, v in list(stats['categories'].items())[:5])}")
        
        if stats['total_documents'] == 0:
            console.print("\n[red]❌ No documents in database. Please run ingestion first.[/red]")
            return
        
        # 각 테스트 실행
        await tester.test_korean_keyword_search()
        await tester.test_english_keyword_search()
        await tester.test_semantic_search()
        await tester.test_filter_search()
        await tester.test_hybrid_search()
        await tester.test_entity_search()
        await tester.test_performance()
        
        # 결과 리포트 생성
        tester.generate_report()
        
    except Exception as e:
        console.print(f"\n[red]❌ Test error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
    
    finally:
        await tester.cleanup()
        console.print("\n[green]✅ Test completed[/green]")


if __name__ == "__main__":
    # 환경 변수 체크
    required_env = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "OPENAI_API_KEY"]
    missing = [var for var in required_env if not os.getenv(var)]
    
    if missing:
        console.print(f"[red]❌ Missing environment variables: {', '.join(missing)}[/red]")
        sys.exit(1)
    
    asyncio.run(main())