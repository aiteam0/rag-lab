"""
MVP RAG System - Ingest Module
Phase 1: Data ingestion and processing
"""

from .database import DatabaseManager
from .models import DDUDocument
from .embeddings import DualLanguageEmbeddings

__all__ = [
    "DatabaseManager",
    "DDUDocument", 
    "DualLanguageEmbeddings"
]