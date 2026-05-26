"""Vector store abstraction — Qdrant-ready interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    """A document stored in the vector store."""

    doc_id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A search result from the vector store."""

    doc_id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class AbstractVectorStore(ABC):
    """Abstract vector store interface — Qdrant abstraction."""

    @abstractmethod
    async def upsert(self, documents: list[VectorDocument]) -> None:
        ...

    @abstractmethod
    async def search(
        self, query: str, top_k: int = 5, filter_metadata: dict | None = None
    ) -> list[SearchResult]:
        ...

    @abstractmethod
    async def delete(self, doc_ids: list[str]) -> None:
        ...


class InMemoryVectorStore(AbstractVectorStore):
    """In-memory vector store for V1 development."""

    def __init__(self) -> None:
        self._store: dict[str, VectorDocument] = {}

    async def upsert(self, documents: list[VectorDocument]) -> None:
        for doc in documents:
            self._store[doc.doc_id] = doc

    async def search(
        self, query: str, top_k: int = 5, filter_metadata: dict | None = None
    ) -> list[SearchResult]:
        # Simple keyword matching for V1
        results = []
        query_lower = query.lower()
        for doc in self._store.values():
            if query_lower in doc.content.lower():
                results.append(SearchResult(
                    doc_id=doc.doc_id,
                    content=doc.content,
                    score=1.0,
                    metadata=doc.metadata,
                ))
        return results[:top_k]

    async def delete(self, doc_ids: list[str]) -> None:
        for doc_id in doc_ids:
            self._store.pop(doc_id, None)
