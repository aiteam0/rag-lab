#!/usr/bin/env python3
"""
한국어 FTS 문제 수정 스크립트
기존 search_vector를 Kiwi로 토크나이징한 결과로 업데이트
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from kiwipiepy import Kiwi
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()
console = Console()

def tokenize_korean_text(kiwi, text):
    """Kiwi를 사용해 한국어 텍스트를 토크나이징"""
    if not text:
        return ""
    
    # Kiwi로 형태소 분석
    result = kiwi.tokenize(text)
    
    # 균형잡힌 품사 세트 (명사, 중요 동사/형용사, 외래어)
    # 제외: VX(보조용언), MM(관형사), MAG(부사), XR(어근) - 노이즈 방지
    meaningful_pos = {'NNG', 'NNP', 'NNB', 'VV', 'VA', 'SL', 'SH', 'SN'}
    tokens = []
    
    # 특별 처리가 필요한 단어들 (Kiwi가 인식 못하는 경우)
    special_words = ['오일', '엔진오일', '브레이크', '와이퍼', '타이어']
    
    # 특별 단어 먼저 추출
    text_lower = text.lower()
    for word in special_words:
        if word in text or word in text_lower:
            tokens.append(word)
    
    for token in result:
        if hasattr(token, 'form') and hasattr(token, 'tag'):
            if token.tag in meaningful_pos:
                # 단어가 1글자 이상인 경우만 포함 (단, 특정 품사는 1글자도 허용)
                if len(token.form) > 1 or token.tag in {'SL', 'SH', 'SN', 'NNB'}:
                    tokens.append(token.form)
    
    # 중복 제거하고 공백으로 연결
    unique_tokens = list(dict.fromkeys(tokens))  # 순서 유지하며 중복 제거
    return ' '.join(unique_tokens)

def format_tsquery(text):
    """여러 단어를 tsquery 형식으로 변환"""
    if not text:
        return ""
    
    words = text.split()
    if len(words) == 1:
        return words[0]
    else:
        # 여러 단어는 & 연산자로 연결
        return ' & '.join(words)

async def fix_korean_fts():
    """모든 문서의 search_vector_korean을 Kiwi 토크나이징 결과로 업데이트"""
    
    # Kiwi 초기화
    console.print("[yellow]Kiwi 토크나이저 초기화 중...[/yellow]")
    kiwi = Kiwi()
    
    # DB 연결
    connection_string = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    
    conn = await asyncpg.connect(connection_string)
    
    try:
        console.print("[bold blue]한국어 FTS 수정 시작[/bold blue]\n")
        
        # 모든 문서 가져오기
        docs = await conn.fetch("""
            SELECT 
                id,
                page_content,
                contextualize_text,
                caption,
                entity::text as entity_json,
                human_feedback
            FROM mvp_ddu_documents
            ORDER BY id
        """)
        
        total_docs = len(docs)
        console.print(f"총 {total_docs}개 문서를 처리합니다.\n")
        
        # Progress bar 설정
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("문서 처리 중...", total=total_docs)
            
            updated_count = 0
            sample_outputs = []
            
            for doc in docs:
                # 한국어 텍스트 조합
                korean_text_parts = []
                
                if doc['contextualize_text']:
                    korean_text_parts.append(doc['contextualize_text'])
                if doc['page_content']:
                    korean_text_parts.append(doc['page_content'])
                if doc['caption']:
                    korean_text_parts.append(doc['caption'])
                if doc['human_feedback']:
                    korean_text_parts.append(doc['human_feedback'])
                
                # entity에서 텍스트 추출 (간단한 방식)
                if doc['entity_json']:
                    try:
                        import json
                        entity = json.loads(doc['entity_json'])
                        if entity and isinstance(entity, dict):
                            # title, keywords 등 추출
                            if 'title' in entity:
                                korean_text_parts.append(str(entity['title']))
                            if 'keywords' in entity and isinstance(entity['keywords'], list):
                                korean_text_parts.extend(entity['keywords'])
                    except:
                        pass
                
                # 전체 텍스트 결합
                full_korean_text = ' '.join(korean_text_parts)
                
                # Kiwi로 토크나이징
                tokenized_text = tokenize_korean_text(kiwi, full_korean_text)
                
                # 처음 5개 샘플 저장
                if len(sample_outputs) < 5:
                    sample_outputs.append({
                        'id': doc['id'],
                        'original': full_korean_text[:100],
                        'tokenized': tokenized_text[:200]
                    })
                
                # DB 업데이트 - to_tsvector에 토크나이징된 텍스트 전달
                await conn.execute("""
                    UPDATE mvp_ddu_documents
                    SET search_vector_korean = to_tsvector('simple', $1)
                    WHERE id = $2
                """, tokenized_text, doc['id'])
                
                updated_count += 1
                progress.update(task, advance=1)
        
        console.print(f"\n[green]✅ {updated_count}개 문서 업데이트 완료![/green]\n")
        
        # 샘플 출력
        console.print("[bold yellow]토크나이징 샘플 (처음 5개):[/bold yellow]")
        for sample in sample_outputs:
            console.print(f"\n[cyan]문서 ID {sample['id']}:[/cyan]")
            console.print(f"  원본: {sample['original']}...")
            console.print(f"  토큰: {sample['tokenized']}...")
        
        # 검증 테스트
        console.print("\n[bold yellow]검증 테스트:[/bold yellow]")
        
        test_queries = ["엔진", "오일", "엔진 오일", "교체", "엔진오일"]
        
        for original in test_queries:
            # 토크나이징
            tokenized = tokenize_korean_text(kiwi, original)
            
            # tsquery 형식으로 변환
            tsquery = format_tsquery(tokenized)
            
            if tsquery:  # 빈 문자열이 아닌 경우만 검색
                try:
                    # 검색 테스트
                    count = await conn.fetchval("""
                        SELECT COUNT(*)
                        FROM mvp_ddu_documents
                        WHERE search_vector_korean @@ to_tsquery('simple', $1)
                    """, tsquery)
                    
                    console.print(f"\n'{original}' → 토큰: '{tokenized}' → tsquery: '{tsquery}' → 매칭: {count}개")
                except Exception as e:
                    console.print(f"\n'{original}' → 토큰: '{tokenized}' → [red]에러: {e}[/red]")
            else:
                console.print(f"\n'{original}' → [yellow]토큰 없음[/yellow]")
            
            console.print(f"\n'{original}' → 토큰: '{tokenized}' → 매칭: {count}개")
        
        console.print("\n[bold green]✅ 한국어 FTS 수정 완료![/bold green]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ 에러 발생: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
    
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_korean_fts())