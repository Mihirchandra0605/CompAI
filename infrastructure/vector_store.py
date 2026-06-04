"""Vector store abstraction using ChromaDB for RAG."""

import os
from pathlib import Path
from typing import List, Dict, Any

try:
    import chromadb
except ImportError:
    chromadb = None

class ChromaVectorStore:
    """A local vector store powered by ChromaDB."""
    
    def __init__(self, persist_dir: str = "./.chroma_db", collection_name: str = "regulations"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        
        # Ensure directory exists
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        if chromadb is None:
            raise ImportError("chromadb is required for ChromaVectorStore. Install chromadb first.")
        
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """Add documents to the vector store."""
        if not documents:
            return
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search the vector store for relevant documents."""
        # if collection is empty, return empty
        if self.collection.count() == 0:
            return []
            
        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count())
        )
        
        formatted_results = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results['metadatas'] else {}
                formatted_results.append({
                    "content": doc,
                    "metadata": meta,
                    "id": results['ids'][0][i]
                })
        return formatted_results
