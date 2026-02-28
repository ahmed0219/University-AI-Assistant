"""
Vector Store Module
Multi-collection ChromaDB wrapper with metadata filtering support.
"""
import chromadb
from typing import List, Dict, Any, Optional
from config import CHROMA_DB_PATH, DEFAULT_COLLECTION, TOP_K_RESULTS
from .embeddings import get_embedding_function


class VectorStore:
    """
    ChromaDB vector store with multi-collection support and metadata filtering.
    """
    
    def __init__(self, collection_name: str = DEFAULT_COLLECTION):
        """
        Initialize the vector store.
        
        Args:
            collection_name: Name of the collection to use
        """
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection_name = collection_name
        self._collection = None
        
    @property
    def collection(self):
        """Lazy load collection with embedding function."""
        if self._collection is None:
            embed_fn = get_embedding_function(document_mode=True)
            try:
                self._collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=embed_fn
                )
            except Exception:
                self._collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=embed_fn
                )
        return self._collection
    
    def add_documents(
        self,
        documents: List[str],
        ids: List[str] = None,
        metadatas: List[Dict[str, Any]] = None
    ) -> None:
        """
        Add documents to the collection.
        
        Args:
            documents: List of document texts
            ids: Optional list of document IDs
            metadatas: Optional list of metadata dicts
        """
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
            
        if metadatas is None:
            metadatas = [{"source": "unknown"} for _ in documents]
            
        # Add in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            
            self.collection.add(
                documents=batch_docs,
                ids=batch_ids,
                metadatas=batch_meta
            )
            
    def query(
        self,
        query_text: str,
        n_results: int = TOP_K_RESULTS,
        where: Dict[str, Any] = None,
        include: List[str] = None
    ) -> Dict[str, Any]:
        """
        Query the collection for similar documents.
        
        Args:
            query_text: The query string
            n_results: Number of results to return
            where: Optional metadata filter
            include: What to include in results (documents, metadatas, distances)
            
        Returns:
            Query results with documents, metadatas, and distances
        """
        if include is None:
            include = ["documents", "metadatas", "distances"]
            
        # Switch to query mode for retrieval
        embed_fn = get_embedding_function(document_mode=False)
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=include
            )
        except Exception as e:
            print(f"[VectorStore Query Error] {e}")
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}
        
        if not results:
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}
        
        return {
            "documents": results.get("documents", [[]])[0] if results.get("documents") else [],
            "metadatas": results.get("metadatas", [[]])[0] if results.get("metadatas") else [],
            "distances": results.get("distances", [[]])[0] if results.get("distances") else [],
            "ids": results.get("ids", [[]])[0] if results.get("ids") else []
        }
    
    def query_with_filter(
        self,
        query_text: str,
        document_type: str = None,
        source_file: str = None,
        n_results: int = TOP_K_RESULTS
    ) -> Dict[str, Any]:
        """
        Query with common metadata filters.
        
        Args:
            query_text: The query string
            document_type: Filter by document type (regulations, academic, etc.)
            source_file: Filter by source file name
            n_results: Number of results to return
            
        Returns:
            Filtered query results
        """
        where = {}
        if document_type:
            where["document_type"] = document_type
        if source_file:
            where["source"] = source_file
            
        return self.query(
            query_text=query_text,
            n_results=n_results,
            where=where if where else None
        )
    
    def get_all_documents(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get sample of all documents in collection.
        
        Args:
            limit: Maximum number of documents to return
            
        Returns:
            Sample of documents from collection
        """
        return self.collection.peek(limit=limit)
    
    def count(self) -> int:
        """Get total document count in collection."""
        return self.collection.count()
    
    def delete_collection(self) -> None:
        """Delete the entire collection."""
        self.client.delete_collection(name=self.collection_name)
        self._collection = None
        
    def list_collections(self) -> List[str]:
        """List all available collections."""
        return [col.name for col in self.client.list_collections()]


# Convenience function for getting default store
def get_vector_store(collection_name: str = DEFAULT_COLLECTION) -> VectorStore:
    """
    Get a vector store instance.
    
    Args:
        collection_name: Name of collection to use
        
    Returns:
        VectorStore instance
    """
    return VectorStore(collection_name)
