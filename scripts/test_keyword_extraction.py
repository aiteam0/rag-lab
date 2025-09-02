#!/usr/bin/env python3
"""
키워드 추출 검증 스크립트
meaningful_pos가 올바르게 설정되었는지 확인
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from kiwipiepy import Kiwi
from rich.console import Console
from rich.table import Table

sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()
console = Console()

def extract_keywords_current(kiwi, text):
    """현재 hybrid_search.py와 동일한 방식"""
    result = kiwi.tokenize(text)
    
    # 현재 설정된 meaningful_pos
    meaningful_pos = {'NNG', 'NNP', 'NNB', 'VV', 'VA', 'VX', 'MM', 'MAG', 'SL', 'SH', 'SN', 'XR'}
    keywords = []
    
    for token in result:
        if hasattr(token, 'tag') and hasattr(token, 'form'):
            if token.tag in meaningful_pos:
                if token.tag.startswith('NN') or token.tag in {'SL', 'SH', 'SN'}:
                    if len(token.form) > 1 or token.tag in {'SL', 'SH', 'SN', 'NNB'}:
                        keywords.append((token.form, token.tag, 1.0))
                elif token.tag.startswith(('VV', 'VA')):
                    if len(token.form) >= 2:
                        keywords.append((token.form, token.tag, 0.7))
                else:
                    # 다른 품사들 (VX, MM, MAG, XR)
                    keywords.append((token.form, token.tag, 0.5))
    
    return keywords

def extract_keywords_minimal(kiwi, text):
    """최소한의 품사만 사용 (명사 위주)"""
    result = kiwi.tokenize(text)
    
    # 최소한의 품사 세트 (명사, 중요 동사, 외래어)
    minimal_pos = {'NNG', 'NNP', 'NNB', 'SL', 'SN'}  # VV, VA 제외
    keywords = []
    
    for token in result:
        if hasattr(token, 'tag') and hasattr(token, 'form'):
            if token.tag in minimal_pos:
                if len(token.form) > 1 or token.tag in {'SL', 'SN', 'NNB'}:
                    keywords.append((token.form, token.tag, 1.0))
    
    return keywords

def extract_keywords_balanced(kiwi, text):
    """균형잡힌 품사 세트 (추천)"""
    result = kiwi.tokenize(text)
    
    # 균형잡힌 품사 세트 (명사, 중요 동사/형용사, 외래어)
    balanced_pos = {'NNG', 'NNP', 'NNB', 'VV', 'VA', 'SL', 'SH', 'SN'}  # VX, MM, MAG, XR 제외
    keywords = []
    
    for token in result:
        if hasattr(token, 'tag') and hasattr(token, 'form'):
            if token.tag in balanced_pos:
                if token.tag.startswith('NN') or token.tag in {'SL', 'SH', 'SN'}:
                    if len(token.form) > 1 or token.tag in {'SL', 'SH', 'SN', 'NNB'}:
                        keywords.append((token.form, token.tag, 1.0))
                elif token.tag.startswith(('VV', 'VA')):
                    if len(token.form) >= 2:
                        keywords.append((token.form, token.tag, 0.7))
    
    return keywords

async def test_keyword_extraction():
    """키워드 추출 테스트"""
    
    console.print("[bold blue]키워드 추출 검증 시작[/bold blue]\n")
    
    # Kiwi 초기화
    kiwi = Kiwi()
    
    # 테스트 쿼리들
    test_queries = [
        "엔진 오일 교체 방법",
        "브레이크 패드를 교환하는 절차",
        "타이어 공기압 확인 및 조정",
        "차량 배터리가 방전되었을 때 대처법",
        "와이퍼 블레이드 교체 주기",
        "에어컨 필터 청소하기",
        "이 차량의 연비는 어떻게 되나요?",
        "매우 중요한 안전 점검 사항들",
        "자동차를 깨끗하게 세차하는 방법"
    ]
    
    # 각 쿼리에 대해 테스트
    for query in test_queries:
        console.print(f"\n[yellow]쿼리: '{query}'[/yellow]")
        
        # 현재 방식
        current = extract_keywords_current(kiwi, query)
        console.print(f"\n[cyan]현재 방식 (모든 품사):[/cyan]")
        for word, tag, weight in current:
            console.print(f"  - '{word}' ({tag}) [weight: {weight}]")
        
        # 최소 방식
        minimal = extract_keywords_minimal(kiwi, query)
        console.print(f"\n[green]최소 방식 (명사만):[/green]")
        for word, tag, weight in minimal:
            console.print(f"  - '{word}' ({tag}) [weight: {weight}]")
        
        # 균형 방식
        balanced = extract_keywords_balanced(kiwi, query)
        console.print(f"\n[magenta]균형 방식 (추천):[/magenta]")
        for word, tag, weight in balanced:
            console.print(f"  - '{word}' ({tag}) [weight: {weight}]")
        
        # 차이점 분석
        current_words = set(w for w, _, _ in current)
        minimal_words = set(w for w, _, _ in minimal)
        balanced_words = set(w for w, _, _ in balanced)
        
        noise_words = current_words - balanced_words
        if noise_words:
            console.print(f"\n[red]노이즈 가능성 (현재-균형):[/red] {noise_words}")
        
        console.print("-" * 50)
    
    # DB 연결해서 실제 검색 테스트
    console.print("\n[bold yellow]실제 검색 테스트[/bold yellow]")
    
    connection_string = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    
    conn = await asyncpg.connect(connection_string)
    
    try:
        test_query = "엔진 오일 교체 방법"
        
        # 각 방식으로 검색
        for method_name, keywords in [
            ("현재", extract_keywords_current(kiwi, test_query)),
            ("최소", extract_keywords_minimal(kiwi, test_query)),
            ("균형", extract_keywords_balanced(kiwi, test_query))
        ]:
            words = [w for w, _, _ in keywords]
            
            # tsquery 생성 (처음 3개만 사용)
            if len(words) <= 2:
                search_query = ' & '.join(words[:3])
            else:
                # 첫 2개는 AND, 나머지는 OR
                primary = ' & '.join(words[:2])
                optional = ' | '.join(words[2:3]) if len(words) > 2 else ""
                search_query = f"({primary})" + (f" | {optional}" if optional else "")
            
            # 검색 실행
            count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM mvp_ddu_documents
                WHERE search_vector_korean @@ to_tsquery('simple', $1)
            """, search_query)
            
            console.print(f"\n[{method_name}] 키워드: {words[:3]}")
            console.print(f"  tsquery: '{search_query}'")
            console.print(f"  매칭 문서: {count}개")
    
    finally:
        await conn.close()
    
    console.print("\n[bold green]✅ 검증 완료[/bold green]")
    
    # 권장사항
    console.print("\n[bold yellow]💡 권장사항:[/bold yellow]")
    console.print("1. VX (보조용언), MM (관형사), MAG (부사), XR (어근)은 제외 추천")
    console.print("2. 명사(NN*) + 외래어(SL, SN) + 중요 동사/형용사(VV, VA)만 포함")
    console.print("3. 균형잡힌 품사 세트 사용 권장")

if __name__ == "__main__":
    asyncio.run(test_keyword_extraction())