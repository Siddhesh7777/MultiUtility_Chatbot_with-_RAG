"""
PDF handling (RAG = Retrieval Augmented Generation).

Flow: PDF bytes -> pages -> small chunks -> embeddings -> FAISS index.
Each chat thread gets its own index, kept in memory
(it is lost when the app restarts).
"""
import os
import tempfile
from typing import Any, Dict, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import CHUNK_OVERLAP, CHUNK_SIZE, TOP_K, embeddings

# thread_id -> retriever / info about the uploaded PDF
_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}


def get_retriever(thread_id: Optional[str]):
    """Return the retriever for a thread, or None if no PDF was uploaded."""
    if thread_id:
        return _THREAD_RETRIEVERS.get(str(thread_id))
    return None


def get_document_metadata(thread_id: str) -> dict:
    """Return filename / pages / chunks for a thread's PDF (empty if none)."""
    return _THREAD_METADATA.get(str(thread_id), {})


def get_source_filename(thread_id: Optional[str]) -> Optional[str]:
    return get_document_metadata(str(thread_id)).get("filename")


def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """Index an uploaded PDF for one chat thread and return a summary dict."""
    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")

    # PyPDFLoader needs a file on disk, so write a temporary one
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        pages = PyPDFLoader(temp_path).load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        chunks = splitter.split_documents(pages)

        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": TOP_K}
        )

        summary = {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(pages),
            "chunks": len(chunks),
        }
        _THREAD_RETRIEVERS[str(thread_id)] = retriever
        _THREAD_METADATA[str(thread_id)] = summary
        return summary
    finally:
        # FAISS keeps its own copy of the text, so the temp file can go
        try:
            os.remove(temp_path)
        except OSError:
            pass
