"""Quick sanity‑check: fetch the top‑k most similar chunks from ChromaDB."""
import sys
from pathlib import Path

# Add project root to path so sibling package imports work when running this script directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.vector_store import ChromaVectorStore

def main():
    store = ChromaVectorStore()
    results = store.search(
        query="What are the penalties for non‑compliance with TRAI regulations?",
        n_results=5,
    )
    if not results:
        print("No results found. Is the vector store populated?")
        return

    for r in results:
        print("-" * 80)
        print(f"Source: {r['metadata'].get('source', 'unknown')}")
        print(f"Document ID: {r.get('id', 'unknown')}")
        print(r["content"][:300] + "…")

if __name__ == "__main__":
    main()