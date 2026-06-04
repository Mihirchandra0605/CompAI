"""Centralized SLM Service — provides unified RAG capabilities for all agents."""

from __future__ import annotations

import json
import logging
from typing import Any

from infrastructure.llm_provider import AbstractLLMProvider
from infrastructure.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class SLMService:
    """Centralized SLM that wraps LLM Provider and ChromaDB for RAG."""

    def __init__(self, llm_provider: AbstractLLMProvider, vector_store: ChromaVectorStore | None = None):
        self.llm = llm_provider
        self.vector_store = vector_store

    async def query(
        self,
        prompt: str,
        system_prompt: str | None = None,
        use_rag: bool = False,
        rag_query: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """
        Query the SLM, optionally augmenting the prompt with context from the vector store.
        """
        augmented_prompt = prompt
        
        if use_rag and self.vector_store:
            # Determine what to search for
            search_term = rag_query if rag_query else prompt[:200]
            context = self._fetch_context(search_term)
            
            if context:
                augmented_prompt = f"--- RAG Context Provided ---\n{context}\n\n--- User Prompt ---\n{prompt}"

        response = await self.llm.generate(
            prompt=augmented_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content

    async def query_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        use_rag: bool = False,
        rag_query: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """
        Query the SLM for structured JSON output, optionally using RAG.
        """
        augmented_prompt = prompt
        
        if use_rag and self.vector_store:
            search_term = rag_query if rag_query else prompt[:200]
            context = self._fetch_context(search_term)
            
            if context:
                augmented_prompt = f"--- RAG Context Provided ---\n{context}\n\n--- User Prompt ---\n{prompt}"

        return await self.llm.generate_structured(
            prompt=augmented_prompt,
            output_schema=output_schema,
            system_prompt=system_prompt,
            temperature=temperature,
        )

    def _fetch_context(self, query: str, top_k: int = 3) -> str:
        """Helper to fetch formatted context from vector store."""
        if not self.vector_store:
            return ""
            
        try:
            results = self.vector_store.search(query=query, n_results=top_k)
            if not results:
                return ""
            
            formatted = []
            for res in results:
                source = res.get('metadata', {}).get('source', 'Unknown Document')
                formatted.append(f"[Source: {source}]\n{res['content']}")
                
            return "\n\n".join(formatted)
        except Exception as e:
            logger.warning(f"Failed to fetch context for RAG: {e}")
            return ""
