"""
LLM Client Module
Wrapper for Gemini LLM with conversation support and prompt templates.
"""
import time
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
from config import GEMINI_API_KEY, LLM_MODEL, MAX_CONTEXT_LENGTH


class LLMClient:
    """
    Wrapper for Gemini LLM with conversation and context management.
    """
    
    def __init__(self, model_name: str = LLM_MODEL, api_key: str = None):
        """
        Initialize the LLM client.
        
        Args:
            model_name: Gemini model to use
            api_key: API key (uses env var if not provided)
        """
        api_key = api_key or GEMINI_API_KEY
        self.client = genai.Client(api_key=api_key)
        # Mask API key for safe logging (show prefix+suffix only)
        try:
            masked_key = (api_key[:6] + "..." + api_key[-4:]) if api_key else "(none)"
        except Exception:
            masked_key = "(masked)"
        print(f"[LLM] Initialized client model={model_name}, api_key={masked_key}")
        self.model_name = model_name
        self.max_context = MAX_CONTEXT_LENGTH
        
    def generate(
        self,
        prompt: str,
        system_instruction: str = None,
        temperature: float = 0.7
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The user prompt
            system_instruction: Optional system instruction
            temperature: Sampling temperature
            
        Returns:
            Generated text response
        """
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
            )
            if system_instruction:
                config.system_instruction = system_instruction
            response = self._call_with_retry(prompt, config)
            return response.text
        except Exception as e:
            print(f"[LLM Error] {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def _call_with_retry(self, prompt: str, config, max_retries: int = 3):
        """Call Gemini API with exponential backoff on rate limits."""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"[LLM] Retry {attempt+1}/{max_retries} model={self.model_name}")
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
            except Exception as e:
                err = str(e)
                if ("429" in err or "RESOURCE_EXHAUSTED" in err) and attempt < max_retries - 1:
                    wait = 15 * (attempt + 1)
                    print(f"[LLM] Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise
    
    def generate_with_context(
        self,
        query: str,
        context_passages: List[str],
        conversation_history: List[Dict[str, str]] = None,
        system_prompt: str = None
    ) -> str:
        """
        Generate response with RAG context and conversation history.
        
        Args:
            query: User's question
            context_passages: Retrieved passages from vector store
            conversation_history: Previous conversation turns
            system_prompt: System instruction for the assistant
            
        Returns:
            Generated response
        """
        if system_prompt is None:
            system_prompt = self._default_university_prompt()
            
        # Build context from passages
        context = "\n\n".join([
            f"[Reference {i+1}]: {passage}"
            for i, passage in enumerate(context_passages)
        ])
        
        # Build conversation history
        history_text = ""
        if conversation_history:
            for turn in conversation_history[-5:]:  # Last 5 turns
                history_text += f"User: {turn.get('user', '')}\n"
                history_text += f"Assistant: {turn.get('assistant', '')}\n\n"
        
        # Construct final prompt
        prompt = f"""
{system_prompt}

REFERENCE INFORMATION:
{context}

{"PREVIOUS CONVERSATION:" if history_text else ""}
{history_text}

USER QUESTION: {query}

Provide a helpful, accurate response based on the reference information above.
"""
        
        # Truncate if too long
        if len(prompt) > self.max_context:
            prompt = prompt[:self.max_context] + "\n[Context truncated due to length]"
            
        return self.generate(prompt)
    
    def _default_university_prompt(self) -> str:
        """Default system prompt for university assistant."""
        return """You are a helpful AI assistant for university students and staff.
Your role is to answer questions about university policies, procedures, academic programs, 
and administrative matters using the provided reference information.

Guidelines:
- Be accurate and base your answers on the provided references
- Be friendly and professional in your tone
- If information is not in the references, say so clearly
- Provide specific details like dates, requirements, and procedures when available
- For complex procedures, break down steps clearly
- Do not invent or assume information not present in the references"""

    def classify_intent(self, query: str) -> str:
        """
        Classify the intent of a user query.
        Uses keyword fast-paths to avoid an LLM call when intent is obvious.
        
        Args:
            query: User's question
            
        Returns:
            Intent category: 'qa', 'admin', 'general'
        """
        import re
        q = query.strip()

        # Fast-path: short greetings / small-talk → no LLM call
        _greeting_re = re.compile(
            r'^(hi|hello|hey|bonjour|salut|salam|bonsoir|'
            r'good\s*(morning|afternoon|evening)|how\s*are\s*you|'
            r'what\'?s?\s*up|yo|thanks|thank\s*you|merci|'
            r'bye|goodbye|au\s*revoir|aidez|comment\s*vas)\s*[!?.]*$',
            re.IGNORECASE,
        )
        if _greeting_re.match(q):
            return 'general'

        # Fast-path: admin keywords → no LLM call
        _admin_kw = ['student data', 'system metric', 'all users', 'manage document']
        if any(kw in q.lower() for kw in _admin_kw):
            return 'admin'

        # Fallback: ask the LLM only for ambiguous cases
        prompt = f"""Classify the following user query into one of these categories:
- qa: Questions about university policies, procedures, academics, administration
- admin: Administrative queries about student data, system metrics (staff only)
- general: General greetings, off-topic, or unclear queries

Query: "{q}"

Respond with ONLY the category name (qa, admin, or general):"""

        response = self.generate(prompt, temperature=0.1)
        intent = response.strip().lower()
        valid_intents = ['qa', 'admin', 'general']
        return intent if intent in valid_intents else 'qa'
    
    def rewrite_query(self, query: str, conversation_history: List[Dict] = None) -> str:
        """
        Rewrite a query for better retrieval.
        
        Args:
            query: Original user query
            conversation_history: Previous conversation for context
            
        Returns:
            Rewritten query optimized for retrieval
        """
        context = ""
        if conversation_history:
            recent = conversation_history[-3:]
            context = "\n".join([
                f"User: {t.get('user', '')}" for t in recent
            ])
            
        prompt = f"""Rewrite the following query to be more specific and better suited for searching a university document database.
If the query references previous conversation, make it self-contained.

{"Recent conversation:" if context else ""}
{context}

Original query: "{query}"

Rewritten query (output ONLY the rewritten query, nothing else):"""

        rewritten = self.generate(prompt, temperature=0.2)
        return rewritten.strip().strip('"')


# Singleton instance
_llm_instance = None

def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    return _llm_instance
