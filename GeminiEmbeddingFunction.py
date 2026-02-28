"""
Standalone Gemini Embedding Function for ChromaDB.
Used by load_document.py for document ingestion.
"""
import time

try:
    from chromadb import EmbeddingFunction
except ImportError:
    from chromadb.api.types import EmbeddingFunction
from google import genai
from config import GEMINI_API_KEY, EMBEDDING_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)
try:
    _masked = (GEMINI_API_KEY[:6] + "..." + GEMINI_API_KEY[-4:]) if GEMINI_API_KEY else "(none)"
except Exception:
    _masked = "(masked)"
print(f"[GeminiEmbeddingFunction] Initialized model={EMBEDDING_MODEL}, api_key={_masked}")


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Embedding function with retry logic for rate limits."""
    document_mode = True

    def __init__(self):
        pass

    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = []
        for text in input:
            embedding = self._embed_with_retry(text)
            embeddings.append(embedding)

        if any(e is None for e in embeddings):
            raise RuntimeError("Some embeddings failed. Please retry.")
        return embeddings

    def _embed_with_retry(self, text: str, max_retries: int = 5):
        """Embed a single text with exponential backoff on rate limits."""
        for attempt in range(max_retries):
            try:
                response = _client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=text,
                )
                return response.embeddings[0].values
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    wait = 30 * (attempt + 1)
                    print(f"Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    print(f"Embedding error: {e}")
                    return None
        print(f"Failed after {max_retries} retries.")
        return None
