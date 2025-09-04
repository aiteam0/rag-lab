"""
Workflow Tools
Factory pattern for search tool selection
"""

import os
import logging
from typing import Optional, Union
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)


def create_search_tool(max_results: int = 5) -> Optional[Union[Tool, object]]:
    """
    Factory function to create appropriate search tool
    
    환경변수 USE_GOOGLE_SEARCH에 따라 Google 또는 Tavily 검색 도구 생성
    
    Args:
        max_results: 최대 검색 결과 수
        
    Returns:
        검색 도구 인스턴스 또는 None (모두 실패 시)
    """
    use_google = os.getenv("USE_GOOGLE_SEARCH", "false").lower() == "true"
    
    if use_google:
        # Google Search 시도
        try:
            from .google_search import GoogleSearchTool
            logger.info("[FACTORY] Attempting to use Google Search Tool")
            
            tool = GoogleSearchTool(max_results=max_results)
            if tool.check_availability():
                logger.info(f"[FACTORY] Google Search Tool initialized successfully (quota: {tool.quota_manager.remaining()}/{tool.quota_manager.daily_limit})")
                return tool  # Tool 객체가 아닌 GoogleSearchTool 인스턴스 반환
            else:
                logger.warning("[FACTORY] Google Search Tool not available (quota exhausted or API issue)")
        except ImportError as e:
            logger.warning(f"[FACTORY] Google Search Tool import failed: {e}")
        except Exception as e:
            logger.warning(f"[FACTORY] Google Search Tool initialization failed: {e}")
    
    # Tavily Search 폴백
    try:
        from .tavily_search import TavilySearchTool
        logger.info("[FACTORY] Using Tavily Search Tool")
        tool = TavilySearchTool(max_results=max_results)
        logger.info("[FACTORY] Tavily Search Tool initialized successfully")
        return tool  # TavilySearchTool 인스턴스 반환
    except Exception as e:
        logger.error(f"[FACTORY] Tavily Search Tool initialization failed: {e}")
    
    # 모두 실패하면 None 반환
    logger.error("[FACTORY] No search tool available")
    return None


# 기존 import 유지 (하위 호환성)
try:
    from .tavily_search import TavilySearchTool
except ImportError:
    TavilySearchTool = None
    
try:
    from .google_search import GoogleSearchTool
except ImportError:
    GoogleSearchTool = None


__all__ = ["TavilySearchTool", "GoogleSearchTool", "create_search_tool"]