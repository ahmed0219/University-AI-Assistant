"""
Agent Orchestrator Module
Routes queries to appropriate specialized agents based on intent classification.
"""
import re
from typing import Dict, Any, Optional, List
from core.llm import get_llm_client
from core.memory import get_session_memory, get_conversation_memory

# Common greetings / small talk patterns (case-insensitive)
_GREETING_PATTERNS = re.compile(
    r'^\s*(hi|hello|hey|bonjour|salut|salam|bonsoir|good\s*(morning|afternoon|evening)|'
    r'how\s*are\s*you|what\'?s?\s*up|yo|thanks|thank\s*you|merci|bye|goodbye|au\s*revoir|'
    r'help|aidez|comment\s*vas)\s*[!?.]*\s*$',
    re.IGNORECASE
)


class AgentOrchestrator:
    """
    Main orchestrator that routes queries to specialized agents.
    """
    
    def __init__(self, session_id: str, user_id: str = None):
        """
        Initialize the orchestrator.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier for personalization
        """
        self.session_id = session_id
        self.user_id = user_id
        self.llm = get_llm_client()
        self.session_memory = get_session_memory()
        self.conversation_memory = get_conversation_memory()
        
        # Lazy-loaded agents
        self._qa_agent = None
        self._admin_agent = None
        
    @property
    def qa_agent(self):
        """Lazy load Q&A agent."""
        if self._qa_agent is None:
            from .qa_agent import QAAgent
            self._qa_agent = QAAgent()
        return self._qa_agent
    
    @property
    def admin_agent(self):
        """Lazy load Admin agent."""
        if self._admin_agent is None:
            from .admin_agent import AdminAgent
            self._admin_agent = AdminAgent()
        return self._admin_agent
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a user query by routing to the appropriate agent.
        
        Args:
            query: User's query
            context: Optional additional context
            
        Returns:
            Response dict with answer, intent, and metadata
        """
        # Get conversation history
        history = self.session_memory.get_history(self.session_id)
        
        # Classify intent
        # Fast-path: detect obvious greetings without burning an LLM call
        if _GREETING_PATTERNS.match(query):
            intent = "general"
        else:
            intent = self.llm.classify_intent(query)
        
        # Route to appropriate agent
        response = self._route_to_agent(query, intent, history, context)
        if response is None:
            response = {}
        
        # Store in memory
        self.session_memory.add_turn(
            self.session_id,
            query,
            response.get("answer", "")
        )
        
        # Persist to database
        self.conversation_memory.add_turn(
            session_id=self.session_id,
            user_id=self.user_id,
            query=query,
            response=response.get("answer", ""),
            intent=intent,
            context_chunks=response.get("context_chunks", [])
        )
        
        return {
            "answer": response.get("answer", ""),
            "intent": intent,
            "sources": response.get("sources", []),
            "metadata": response.get("metadata", {})
        }
    
    def _route_to_agent(
        self,
        query: str,
        intent: str,
        history: List[Dict],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Route query to the appropriate agent based on intent.
        
        Args:
            query: User's query
            intent: Classified intent
            history: Conversation history
            context: Additional context
            
        Returns:
            Agent response
        """
        context = context or {}
        
        if intent == "qa":
            return self.qa_agent.answer(
                query=query,
                conversation_history=history,
                document_filter=context.get("document_filter")
            )
            
        elif intent == "admin":
            if not self._check_admin_permission():
                return {
                    "answer": "You don't have permission to access administrative features.",
                    "sources": []
                }
            return self.admin_agent.query(query)
            
        else:  # general or unknown
            return self._handle_general_query(query, history)
    
    def _handle_general_query(
        self,
        query: str,
        history: List[Dict]
    ) -> Dict[str, Any]:
        """Handle general queries with a friendly response."""
        # For greetings / small talk, respond directly without RAG
        prompt = f"""You are a friendly university AI assistant named "University Assistant".
The user said: "{query}"

If this is a greeting, respond warmly and offer to help with university-related questions.
You can also help with generating administrative emails.
If this is a thank you, respond politely.
If this is off-topic, politely redirect to university topics you can help with.

Keep your response brief, friendly and helpful. Respond in the same language the user used."""

        answer = self.llm.generate(prompt, temperature=0.7)
        return {
            "answer": answer,
            "sources": [],
            "metadata": {"type": "general"}
        }
    
    def _check_admin_permission(self) -> bool:
        """Check if user has admin permissions."""
        # This would integrate with your auth system
        # For now, return True for demo purposes
        return True
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        return self.conversation_memory.get_session_summary(self.session_id)
    
    def clear_session(self) -> None:
        """Clear current session from memory."""
        self.session_memory.clear_session(self.session_id)


def create_orchestrator(session_id: str, user_id: str = None) -> AgentOrchestrator:
    """
    Factory function to create an orchestrator.
    
    Args:
        session_id: Unique session identifier
        user_id: Optional user identifier
        
    Returns:
        Configured AgentOrchestrator instance
    """
    return AgentOrchestrator(session_id=session_id, user_id=user_id)
