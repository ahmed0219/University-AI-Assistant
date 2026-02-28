"""
Enhanced Gemini Embeddings Module
Provides embedding generation for document and query modes with batch processing.
"""
try:
    from chromadb import EmbeddingFunction
except ImportError:
    from chromadb.api.types import EmbeddingFunction
from google import genai
import os
from typing import List
from config import GEMINI_API_KEY, EMBEDDING_MODEL


class GeminiEmbeddings(EmbeddingFunction):
    """
    Wrapper for Gemini embedding model with support for document and query modes.
    """
    
    def __init__(self, api_key: str = None, document_mode: bool = True):
        """
        Initialize the embedding function.
        
        Args:
            api_key: Gemini API key (uses env var if not provided)
            document_mode: True for indexing documents, False for queries
        """
        self.api_key = api_key or GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.document_mode = document_mode
        self.model = EMBEDDING_MODEL        # must be set before any print that uses it
        self.embedding_dim = 768
        try:
            masked = (self.api_key[:6] + "..." + self.api_key[-4:]) if self.api_key else "(none)"
        except Exception:
            masked = "(masked)"
        print(f"[Embeddings] Initialized model={self.model}, api_key={masked}")
        
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            input: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        task = "retrieval_document" if self.document_mode else "retrieval_query"
        embeddings = []
        
        for text in input:
            try:
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=text,
                )
                embeddings.append(response.embeddings[0].values)
            except Exception as e:
                print(f"[Embedding Error] {e}")
                # Fallback to zero vector on error
                embeddings.append([0.0] * self.embedding_dim)
                
        return embeddings
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed documents for indexing.
        
        Args:
            texts: List of document texts
            
        Returns:
            List of embedding vectors
        """
        original_mode = self.document_mode
        self.document_mode = True
        embeddings = self(texts)
        self.document_mode = original_mode
        return embeddings
    
    def embed_query(self, text: str = None, input = None) -> List[List[float]]:
        """
        Embed a single query for retrieval.
        
        Args:
            text: Query text
            input: Alternative parameter name (used by newer ChromaDB).
                   Can be a string or a list of strings.
            
        Returns:
            List of embedding vectors (one per input text)
        """
        query_input = input if input is not None else text
        # ChromaDB may pass a list of strings
        if isinstance(query_input, str):
            query_input = [query_input]
        original_mode = self.document_mode
        self.document_mode = False
        embeddings = self(query_input)
        self.document_mode = original_mode
        return embeddings
    
    def batch_embed(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        Embed texts in batches for efficiency.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch
            
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self(batch)
            all_embeddings.extend(batch_embeddings)
        return all_embeddings


# Singleton instance for reuse
_embedding_instance = None

def get_embedding_function(document_mode: bool = True) -> GeminiEmbeddings:
    """
    Get or create embedding function singleton.
    
    Args:
        document_mode: Whether to use document mode
        
    Returns:
        GeminiEmbeddings instance
    """
    global _embedding_instance
    if _embedding_instance is None:
        _embedding_instance = GeminiEmbeddings()
    _embedding_instance.document_mode = document_mode
    return _embedding_instance
