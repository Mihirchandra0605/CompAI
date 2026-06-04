"""Script to ingest raw regulations (PDF, DOCX, TXT) into the ChromaDB vector store."""

import sys
import os
import concurrent.futures
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.vector_store import ChromaVectorStore
from infrastructure.document_parser import DocumentParser

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    RecursiveCharacterTextSplitter = None

# Maximum file size to attempt ingesting (in MB). Files larger than this are skipped.
MAX_FILE_SIZE_MB = 100
# Maximum seconds to spend on a single file before giving up.
FILE_TIMEOUT_SECONDS = 120
# Maximum number of vectors to send to Chroma in a single upsert call (must be < 5461).
MAX_BATCH_SIZE = 4000

def parse_file_with_timeout(parser, file_path, timeout=FILE_TIMEOUT_SECONDS):
    """Parse a file with a hard timeout to prevent getting stuck on large scanned PDFs."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(parser.parse_file, str(file_path))
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print(f"  [TIMEOUT] Skipping {file_path.name} — took longer than {timeout}s.")
            return []
        except Exception as e:
            print(f"  [ERROR] Failed to parse {file_path.name}: {e}")
            return []

def ingest_directory(directory_path: str):
    store = ChromaVectorStore()
    parser = DocumentParser(use_ocr=True)
    
    if RecursiveCharacterTextSplitter:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
    else:
        text_splitter = None
        
    dir_path = Path(directory_path)
    if not dir_path.exists():
        print(f"Directory {dir_path} does not exist.")
        return
        
    files = list(dir_path.glob("*.*"))
    if not files:
        print(f"No files found in {dir_path}")
        return
        
    tracker_file = dir_path / ".ingested_files.log"
    ingested = set()
    if tracker_file.exists():
        with open(tracker_file, "r") as f:
            ingested = set(line.strip() for line in f)

    for file_path in files:
        if file_path.suffix.lower() not in [".pdf", ".docx", ".doc", ".txt"]:
            continue
            
        if file_path.name in ingested:
            print(f"Skipping already ingested file: {file_path.name}")
            continue

        # Skip files that are too large (likely huge scanned documents)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            print(f"Skipping {file_path.name} ({file_size_mb:.1f} MB) — exceeds {MAX_FILE_SIZE_MB} MB limit.")
            with open(tracker_file, "a") as f:
                f.write(file_path.name + "\n")
            continue

        # Process this file
        _process_file(file_path, parser, store, text_splitter, tracker_file)


def _pdf_page_count(path: Path) -> int:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


# Process a single file (parsing, chunking, upserting, logging)
def _process_file(file_path: Path, parser: DocumentParser, store: ChromaVectorStore, text_splitter, tracker_file: Path):
    # Determine total pages for progress (only for PDFs)
    total_pages = _pdf_page_count(file_path) if file_path.suffix.lower() == ".pdf" else None
    processed_pages = 0
    
    print(f"Processing {file_path.name} ({file_path.stat().st_size / (1024 * 1024):.1f} MB)...")
    parsed_chunks = parser.parse_file(str(file_path))
    total_chunks = len(parsed_chunks)
    print(f"  → Total chunks to process: {total_chunks}")
    
    docs = []
    metas = []
    ids = []
    
    chunk_idx = 0
    for doc_chunk in parsed_chunks:
        if text_splitter:
            splits = text_splitter.split_text(doc_chunk.text)
            for split in splits:
                docs.append(split)
                metas.append(doc_chunk.metadata)
                ids.append(f"{file_path.name}_{chunk_idx}")
                chunk_idx += 1
        else:
            docs.append(doc_chunk.text)
            metas.append(doc_chunk.metadata)
            ids.append(f"{file_path.name}_{chunk_idx}")
            chunk_idx += 1
        
        # Update progress if we know total pages
        if total_pages:
            processed_pages += 1
            percent = (processed_pages / total_pages) * 100
            print(f"  → Page {processed_pages}/{total_pages} ({percent:.1f}%) processed")
    
    if docs:
        # ------------------------------------------------------------
        # Send the data to Chroma in chunks of MAX_BATCH_SIZE items
        # ------------------------------------------------------------
        for start in range(0, len(docs), MAX_BATCH_SIZE):
            end = start + MAX_BATCH_SIZE
            batch_docs = docs[start:end]
            batch_metas = metas[start:end]
            batch_ids = ids[start:end]
            store.add_documents(batch_docs, batch_metas, batch_ids)
        print(f"Ingested {len(docs)} chunks from {file_path.name}")
    else:
        print(f"No text extracted from {file_path.name}")
    
    # Log successful processing
    with open(tracker_file, "a") as f:
        f.write(file_path.name + "\n")
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If it's a file, ingest just the file. If directory, ingest directory.
        path = Path(sys.argv[1])
        if path.is_file():
            # Quick wrapper to reuse directory logic
            print(f"Processing single file: {path.name}")
            parser = DocumentParser(use_ocr=True)
            parsed_chunks = parser.parse_file(str(path))
            docs, metas, ids = [], [], []
            for i, chunk in enumerate(parsed_chunks):
                docs.append(chunk.text)
                metas.append(chunk.metadata)
                ids.append(f"{path.name}_{i}")
            store = ChromaVectorStore()
            store.add_documents(docs, metas, ids)
            print(f"Ingested {len(docs)} chunks from {path.name}")
        else:
            ingest_directory(sys.argv[1])
    else:
        # Default to raw_regulations folder
        default_dir = Path(__file__).parent.parent / "data" / "raw_regulations"
        default_dir.mkdir(parents=True, exist_ok=True)
        print(f"Please drop PDF/DOCX files into {default_dir} and run this script again, or provide a directory path.")
        
        # Try ingesting if there are files
        ingest_directory(str(default_dir))
