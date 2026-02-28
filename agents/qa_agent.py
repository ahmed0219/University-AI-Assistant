"""
Q&A Agent Module
Handles question-answering with RAG retrieval from university documents.
"""
from typing import Dict, Any, List, Optional
from core.llm import get_llm_client
from core.vector_store import get_vector_store
from config import TOP_K_RESULTS


class QAAgent:
    """
    Agent for answering questions about university policies and information.
    """
    
    def __init__(self, collection_name: str = "university"):
        """
        Initialize Q&A agent.
        
        Args:
            collection_name: Vector store collection to use
        """
        self.llm = get_llm_client()
        self.vector_store = get_vector_store(collection_name)
        self.system_prompt = self._build_system_prompt()
        
    def _build_system_prompt(self) -> str:
        """Build the system prompt for Q&A."""
        return """You are an expert university administrative assistant with deep knowledge of academic policies, procedures, and student services.

Your role is to:
1. Answer questions accurately based on the provided reference documents
2. Provide clear, step-by-step guidance for procedures
3. Include specific details like deadlines, requirements, and contact information when available
4. Be sympathetic to student concerns while maintaining professionalism
5. Redirect to appropriate offices when questions are beyond your knowledge

Guidelines:
- Base answers ONLY on the provided reference passages
- If information is incomplete, acknowledge what you know and what's unclear
- Never invent policies or procedures
- Use a friendly, helpful tone
- For complex procedures, use numbered steps
- Include relevant deadlines or timeframes when mentioned in references"""

    def answer(
        self,
        query: str,
        conversation_history: List[Dict] = None,
        document_filter: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG retrieval.
        
        Args:
            query: User's question
            conversation_history: Previous conversation turns
            document_filter: Metadata filters for retrieval
            
        Returns:
            Response with answer, sources, and context chunks
        """
        try:
            # Retrieve relevant passages (skip query rewrite to save API quota)
            if document_filter and isinstance(document_filter, dict):
                results = self.vector_store.query_with_filter(
                    query_text=query,
                    document_type=document_filter.get("document_type"),
                    source_file=document_filter.get("source_file"),
                    n_results=TOP_K_RESULTS
                )
            else:
                results = self.vector_store.query(
                    query_text=query,
                    n_results=TOP_K_RESULTS
                )
            
            if not results or not isinstance(results, dict):
                results = {}
            
            passages = results.get("documents") or []
            metadatas = results.get("metadatas") or []
            distances = results.get("distances") or []
            
            # Generate response with context
            if passages:
                answer = self.llm.generate_with_context(
                    query=query,
                    context_passages=passages,
                    conversation_history=conversation_history,
                    system_prompt=self.system_prompt
                )
                
                # Extract source information
                sources = self._extract_sources(metadatas)
            else:
                answer = self._no_context_response(query)
                sources = []
            
            return {
                "answer": answer,
                "sources": sources,
                "context_chunks": passages,
                "metadata": {
                    "num_passages": len(passages),
                    "distances": distances
                }
            }
        except Exception as e:
            print(f"[QA Agent Error] {e}")
            return {
                "answer": f"I encountered an error while searching: {str(e)}",
                "sources": [],
                "context_chunks": [],
                "metadata": {}
            }
    
    def _extract_sources(self, metadatas) -> List[Dict]:
        """Extract source information from metadata."""
        sources = []
        seen_sources = set()
        
        if not metadatas:
            return sources
        
        for meta in metadatas:
            if not meta or not isinstance(meta, dict):
                continue
            source = meta.get("source", "Unknown")
            if source not in seen_sources:
                seen_sources.add(source)
                sources.append({
                    "file": source,
                    "document_type": meta.get("document_type", "general"),
                    "page": meta.get("page")
                })
                
        return sources
    
    def _no_context_response(self, query: str) -> str:
        """Generate response when no relevant context is found."""
        return f"""I apologize, but I couldn't find specific information about "{query}" in our university documents.

Here are some suggestions:
1. Try rephrasing your question with different keywords
2. Contact the relevant administrative office directly
3. Check the university website for the most up-to-date information

Is there something else I can help you with?"""

    def answer_with_sources(
        self,
        query: str,
        show_sources: bool = True
    ) -> str:
        """
        Get a formatted answer with source citations.
        
        Args:
            query: User's question
            show_sources: Whether to include source references
            
        Returns:
            Formatted answer string
        """
        result = self.answer(query)
        answer = result["answer"]
        
        if show_sources and result["sources"]:
            sources_text = "\n\n**Sources:**\n"
            for i, source in enumerate(result["sources"], 1):
                sources_text += f"{i}. {source['file']}"
                if source.get("page"):
                    sources_text += f" (Page {source['page']})"
                sources_text += "\n"
            answer += sources_text
            
        return answer
    
    def quick_answer(self, query: str) -> str:
        """
        Get a quick, no-frills answer.
        
        Args:
            query: User's question
            
        Returns:
            Answer string
        """
        result = self.answer(query)
        return result["answer"]


# Convenience function
def ask_university(query: str) -> str:
    """
    Quick function to ask a university-related question.
    
    Args:
        query: Your question
        
    Returns:
        Answer string
    """
    agent = QAAgent()
    return agent.quick_answer(query)
