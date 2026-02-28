"""
Document Loader
Extracts, chunks and indexes PDF documents into ChromaDB.
"""
import time
import chromadb
from text_chunk import extract_and_chunk_pdfs_from_dir
from GeminiEmbeddingFunction import GeminiEmbeddingFunction
from config import CHROMA_DB_PATH, PDF_DIRECTORY, DEFAULT_COLLECTION

DB_NAME = DEFAULT_COLLECTION
PDF_DIR = PDF_DIRECTORY
BATCH_SIZE = 50
BATCH_DELAY = 60  # seconds between batches


def load_documents():
    """Delete old collections and re-index all PDFs."""
    embed_fn = GeminiEmbeddingFunction()
    embed_fn.document_mode = True

    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    # Delete existing collections
    for col in chroma_client.list_collections():
        col_name = col if isinstance(col, str) else col.name
        print(f"🗑️  Deleting old collection: {col_name}")
        chroma_client.delete_collection(name=col_name)

    # Create fresh collection
    db = chroma_client.create_collection(name=DB_NAME, embedding_function=embed_fn)
    print(f"✅ Collection '{DB_NAME}' initialized.")

    # Extract and chunk PDFs
    print("⏳ Extracting and chunking PDFs...")
    documents = extract_and_chunk_pdfs_from_dir(PDF_DIR)
    ids = [f"doc_{i}" for i in range(len(documents))]

    # Add in batches with rate-limit delays
    for i in range(0, len(documents), BATCH_SIZE):
        batch_docs = documents[i:i + BATCH_SIZE]
        batch_ids = ids[i:i + BATCH_SIZE]
        print(f"  📦 Adding batch {i // BATCH_SIZE + 1} ({len(batch_docs)} chunks)...")
        db.add(documents=batch_docs, ids=batch_ids)
        if i + BATCH_SIZE < len(documents):
            print(f"  ⏳ Waiting {BATCH_DELAY}s for rate limit...")
            time.sleep(BATCH_DELAY)

    print(f"✅ {len(documents)} chunks added to the DB.")


if __name__ == "__main__":
    load_documents()
