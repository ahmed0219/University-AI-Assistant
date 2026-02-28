"""
Document Chunker Module
Enhanced text chunking with metadata preservation.
"""
import os
from typing import List, Dict, Any, Tuple
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP, PDF_DIRECTORY


class DocumentChunker:
    """
    Chunks documents with metadata for better retrieval.
    """
    
    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks
        """
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
    def chunk_pdf(
        self,
        file_path: str,
        document_type: str = "general"
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Extract and chunk a PDF file with metadata.
        
        Args:
            file_path: Path to PDF file
            document_type: Type of document (regulations, academic, etc.)
            
        Returns:
            Tuple of (chunks list, metadata list)
        """
        reader = PdfReader(file_path)
        filename = os.path.basename(file_path)
        
        all_chunks = []
        all_metadata = []
        
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if not text:
                continue
                
            # Chunk this page
            page_chunks = self.splitter.split_text(text)
            
            # Create metadata for each chunk
            for i, chunk in enumerate(page_chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    "source": filename,
                    "page": page_num,
                    "chunk_index": i,
                    "document_type": document_type,
                    "total_pages": len(reader.pages)
                })
        
        return all_chunks, all_metadata
    
    def chunk_text(
        self,
        text: str,
        source: str = "unknown",
        document_type: str = "general"
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Chunk plain text with metadata.
        
        Args:
            text: Text to chunk
            source: Source identifier
            document_type: Type of document
            
        Returns:
            Tuple of (chunks list, metadata list)
        """
        chunks = self.splitter.split_text(text)
        
        metadata = [
            {
                "source": source,
                "chunk_index": i,
                "document_type": document_type
            }
            for i in range(len(chunks))
        ]
        
        return chunks, metadata
    
    def process_pdf_directory(
        self,
        directory_path: str = PDF_DIRECTORY,
        document_type_mapping: Dict[str, str] = None
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Process all PDFs in a directory.
        
        Args:
            directory_path: Path to directory containing PDFs
            document_type_mapping: Optional dict mapping filenames to document types
            
        Returns:
            Tuple of (all chunks, all metadata)
        """
        all_chunks = []
        all_metadata = []
        
        document_type_mapping = document_type_mapping or {}
        
        for filename in os.listdir(directory_path):
            if not filename.endswith(".pdf"):
                continue
                
            file_path = os.path.join(directory_path, filename)
            doc_type = document_type_mapping.get(filename, "general")
            
            print(f"Processing: {filename}")
            
            try:
                chunks, metadata = self.chunk_pdf(file_path, doc_type)
                all_chunks.extend(chunks)
                all_metadata.extend(metadata)
                print(f"  ✓ {len(chunks)} chunks extracted")
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        return all_chunks, all_metadata
    
    def chunk_with_context(
        self,
        file_path: str,
        context_window: int = 1
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Chunk with surrounding context for better retrieval.
        
        Args:
            file_path: Path to PDF file
            context_window: Number of surrounding chunks to include
            
        Returns:
            Chunks with context and metadata
        """
        # First get regular chunks
        base_chunks, base_metadata = self.chunk_pdf(file_path)
        
        enhanced_chunks = []
        enhanced_metadata = []
        
        for i, chunk in enumerate(base_chunks):
            # Build context from surrounding chunks
            start = max(0, i - context_window)
            end = min(len(base_chunks), i + context_window + 1)
            
            context_chunks = base_chunks[start:end]
            enhanced_text = "\n\n".join(context_chunks)
            
            enhanced_chunks.append(enhanced_text)
            enhanced_metadata.append({
                **base_metadata[i],
                "context_range": f"{start}-{end}",
                "primary_chunk_index": i
            })
        
        return enhanced_chunks, enhanced_metadata


def ingest_documents(
    pdf_directory: str = PDF_DIRECTORY,
    collection_name: str = "university"
) -> int:
    """
    Convenience function to ingest all PDFs into vector store.
    
    Args:
        pdf_directory: Directory containing PDFs
        collection_name: Target collection name
        
    Returns:
        Number of chunks ingested
    """
    from core.vector_store import get_vector_store
    
    chunker = DocumentChunker()
    chunks, metadata = chunker.process_pdf_directory(pdf_directory)
    
    if not chunks:
        print("No documents to ingest")
        return 0
    
    # Generate IDs
    ids = [f"doc_{i}" for i in range(len(chunks))]
    
    # Add to vector store
    vector_store = get_vector_store(collection_name)
    vector_store.add_documents(chunks, ids, metadata)
    
    print(f"✓ Ingested {len(chunks)} chunks into '{collection_name}'")
    return len(chunks)
