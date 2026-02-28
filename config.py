# Configuration for the University AI Assistant
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Database Paths
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./student_results.db")

# Document 
PDF_DIRECTORY = os.getenv("PDF_DIRECTORY", "./pdf")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# RAG Settings
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

# LLM Settings
LLM_MODEL = os.getenv("LLM_MODEL", "models/gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "8000"))

# Collections for different document types
COLLECTIONS = {
    "university": "General university documents",
    "regulations": "Rules, policies, and procedures",
    "academic": "Course information, syllabi, requirements",
    "administrative": "Forms, deadlines, contacts"
}

# Default collection
DEFAULT_COLLECTION = "university"

# Cache Settings
FAQ_CACHE_TTL_HOURS = int(os.getenv("FAQ_CACHE_TTL_HOURS", "24"))
MAX_CACHE_SIZE = int(os.getenv("MAX_CACHE_SIZE", "1000"))

# Conversation Settings
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))

# User Roles
ROLES = {
    "student": ["chat"],
    "faculty": ["chat", "view_analytics"],
    "admin": ["chat", "manage_documents", "view_all_data", "configure_system"]
}
