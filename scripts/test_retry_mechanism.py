#!/usr/bin/env python3
"""
Retry 메커니즘 테스트 스크립트
피드백 기반 재시도가 제대로 작동하는지 검증
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from typing import Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from workflow.nodes.synthesis import SynthesisNode
from workflow.state import MVPWorkflowState
from langchain_core.documents import Document

console = Console()

class RetryMechanismTester:
    """Retry 메커니즘 테스터"""
    
    def __init__(self):
        self.synthesis_node = SynthesisNode()
        
    async def test_hallucination_retry(self):
        """환각 체크 실패 재시도 테스트"""
        console.print("\n[bold cyan]🔄 Testing Hallucination Retry Mechanism[/bold cyan]")
        
        # 테스트 문서
        documents = [
            Document(
                page_content="엔진 오일은 정기적으로 교체해야 합니다. 엔진룸을 열고 오일 레벨을 확인하세요.",
                metadata={"source": "manual.pdf", "page": 45, "category": "maintenance"}
            ),
            Document(
                page_content="냉각수 레벨을 확인하려면 엔진이 식은 후에 확인해야 합니다.",
                metadata={"source": "manual.pdf", "page": 50, "category": "safety"}
            )
        ]
        
        # State 준비 - 첫 번째 시도
        state_first = {
            "query": "엔진 오일 교체 방법을 알려주세요",
            "documents": documents,
            "retry_count": 0,
            "metadata": {}
        }
        
        console.print("\n[yellow]1️⃣ First attempt (no retry):[/yellow]")
        result1 = await self.synthesis_node(state_first)
        
        # 첫 번째 답변 출력
        if "intermediate_answer" in result1:
            console.print(Panel(
                result1["intermediate_answer"][:300] + "...",
                title="First Answer (truncated)",
                border_style="yellow"
            ))
        
        # State 준비 - 재시도 (환각 피드백 포함)
        state_retry = {
            "query": "엔진 오일 교체 방법을 알려주세요",
            "documents": documents,
            "retry_count": 1,
            "hallucination_check": {
                "is_valid": False,
                "score": 0.3,
                "reason": "Answer contains unsupported claims",
                "suggestions": [
                    "Only include information explicitly stated in documents",
                    "Add page citations for all claims",
                    "Avoid mentioning specific oil capacity or intervals not in documents"
                ],
                "needs_retry": True
            },
            "metadata": {
                "hallucination_check": {
                    "hallucination_score": 0.7,
                    "problematic_claims": [
                        "오일 용량이 4.5L입니다",
                        "10,000km마다 교체하세요"
                    ],
                    "supported_claims": [
                        "엔진 오일은 정기적으로 교체해야 합니다"
                    ]
                }
            }
        }
        
        console.print("\n[green]2️⃣ Retry with hallucination feedback:[/green]")
        result2 = await self.synthesis_node(state_retry)
        
        # 재시도 답변 출력
        if "intermediate_answer" in result2:
            console.print(Panel(
                result2["intermediate_answer"][:300] + "...",
                title="Corrected Answer (truncated)",
                border_style="green"
            ))
        
        # 결과 비교
        self._compare_results(result1, result2, "Hallucination")
        
    async def test_quality_retry(self):
        """품질 체크 실패 재시도 테스트"""
        console.print("\n[bold cyan]🔄 Testing Quality Improvement Retry Mechanism[/bold cyan]")
        
        # 테스트 문서
        documents = [
            Document(
                page_content="타이어 공기압 점검: 1. 타이어가 차가운 상태에서 점검 2. 권장 공기압은 운전석 도어 스티커 확인 3. 압력계로 측정 4. 부족시 보충",
                metadata={"source": "manual.pdf", "page": 120, "category": "maintenance"}
            ),
            Document(
                page_content="타이어 공기압 점검 주기: 매월 1회 권장. 장거리 운행 전 필수 점검.",
                metadata={"source": "manual.pdf", "page": 121, "category": "maintenance"}
            )
        ]
        
        # State 준비 - 재시도 (품질 피드백 포함)
        state_retry = {
            "query": "타이어 공기압 점검 방법",
            "documents": documents,
            "retry_count": 1,
            "answer_grade": {
                "is_valid": False,
                "score": 0.45,
                "reason": "Answer lacks completeness and specific details",
                "suggestions": [
                    "Add step-by-step procedure",
                    "Include safety warnings",
                    "Specify required tools",
                    "Add time estimates"
                ],
                "needs_retry": True
            },
            "metadata": {
                "answer_grade": {
                    "overall_score": 0.45,
                    "completeness": 0.3,
                    "relevance": 0.7,
                    "clarity": 0.6,
                    "usefulness": 0.2,
                    "missing_aspects": [
                        "Required tools (압력계)",
                        "Safety precautions",
                        "Time required for the task"
                    ],
                    "strengths": [
                        "Clear language",
                        "Mentions basic steps"
                    ]
                }
            }
        }
        
        console.print("\n[green]📈 Generating improved answer with quality feedback:[/green]")
        result = await self.synthesis_node(state_retry)
        
        # 개선된 답변 출력
        if "intermediate_answer" in result:
            console.print(Panel(
                result["intermediate_answer"],
                title="Quality-Improved Answer",
                border_style="green"
            ))
            
        # 메타데이터 출력
        if "metadata" in result and "synthesis" in result["metadata"]:
            meta = result["metadata"]["synthesis"]
            console.print(f"\n[dim]Confidence: {meta.get('confidence', 0):.2f}[/dim]")
            console.print(f"[dim]Sources used: {meta.get('sources', [])}[/dim]")
    
    def _compare_results(self, result1: Dict, result2: Dict, test_type: str):
        """결과 비교 테이블 생성"""
        table = Table(title=f"{test_type} Retry Comparison")
        table.add_column("Metric", style="cyan")
        table.add_column("First Attempt", style="yellow")
        table.add_column("After Retry", style="green")
        
        # 답변 길이 비교
        len1 = len(result1.get("intermediate_answer", ""))
        len2 = len(result2.get("intermediate_answer", ""))
        table.add_row("Answer Length", str(len1), str(len2))
        
        # 신뢰도 비교
        conf1 = result1.get("confidence_score", 0)
        conf2 = result2.get("confidence_score", 0)
        table.add_row("Confidence", f"{conf1:.2f}", f"{conf2:.2f}")
        
        # 소스 수 비교
        sources1 = len(result1.get("metadata", {}).get("synthesis", {}).get("sources", []))
        sources2 = len(result2.get("metadata", {}).get("synthesis", {}).get("sources", []))
        table.add_row("Sources Used", str(sources1), str(sources2))
        
        console.print(table)
        
    async def run_all_tests(self):
        """모든 테스트 실행"""
        console.print(Panel(
            "[bold]🧪 Retry Mechanism Test Suite[/bold]\n"
            "Testing feedback-based retry generation",
            border_style="cyan"
        ))
        
        try:
            # 환각 재시도 테스트
            await self.test_hallucination_retry()
            
            # 품질 재시도 테스트
            await self.test_quality_retry()
            
            console.print("\n[bold green]✅ All retry mechanism tests completed![/bold green]")
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Test failed: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())

async def main():
    """메인 함수"""
    tester = RetryMechanismTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())