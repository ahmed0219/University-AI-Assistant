# 🎓 University AI Administrative Assistant

An intelligent, multi-agent AI assistant for university students and administrators. Built with **Streamlit**, powered by **Google Gemini**, and backed by a **ChromaDB** vector store for document-based question answering.

---

## Features

- **AI-Powered Q&A** — Ask questions about university policies, schedules, and documents using RAG (Retrieval-Augmented Generation).
- **Multi-Agent Architecture** — An orchestrator routes queries to specialized agents (Q&A, Admin, Email).
- **Administrative Email Generator** — Generate formal administrative emails (in French) for common university requests.
- **User Authentication** — Register and log in with role-based access (student / admin).
- **Document Ingestion** — Load and chunk PDF documents into a persistent ChromaDB vector store.
- **FAQ Cache** — Frequently asked questions are cached for faster responses.
- **Conversation Memory** — Session-based memory for contextual multi-turn conversations.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | [Streamlit](https://streamlit.io/) |
| LLM | Google Gemini (`gemini-2.5-flash`) |
| Embeddings | Google Gemini (`gemini-embedding-001`) |
| Vector Store | [ChromaDB](https://www.trychroma.com/) |
| Document Parsing | PyPDF2 + LangChain Text Splitters |
| Database | SQLite |
| Config | python-dotenv |

---

## Project Structure

```
twise/
├── app.py                        # Main Streamlit app (auth + chat)
├── config.py                     # Configuration & environment variables
├── gemini.py                     # Gemini LLM client setup
├── GeminiEmbeddingFunction.py    # Custom ChromaDB embedding function
├── load_document.py              # PDF ingestion pipeline
├── text_chunk.py                 # Text chunking utilities
├── requirements.txt
│
├── agents/
│   ├── orchestrator.py           # Routes queries to specialized agents
│   ├── qa_agent.py               # RAG-based Q&A agent
│   ├── admin_agent.py            # Admin database query agent
│   └── email_agent.py            # Administrative email generator
│
├── core/
│   ├── llm.py                    # LLM client factory
│   ├── embeddings.py             # Embedding utilities
│   ├── memory.py                 # Session & conversation memory
│   └── vector_store.py           # ChromaDB wrapper
│
├── database/
│   ├── operations.py             # SQLite user management
│   └── faq_cache.py              # FAQ caching layer
│
├── document_processing/
│   ├── chunker.py                # Document chunking logic
│   └── metadata_extractor.py     # PDF metadata extraction
│
├── pages/
│   └── 4_email_generator.py      # Email generator Streamlit page
│
├── pdf/                          # Place your university PDF documents here
└── chroma_db/                    # Persistent vector store (auto-generated)
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd twise
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here

# Optional overrides (defaults shown)
CHROMA_DB_PATH=./chroma_db
SQLITE_DB_PATH=./student_results.db
PDF_DIRECTORY=./pdf
LLM_MODEL=models/gemini-2.5-flash
EMBEDDING_MODEL=gemini-embedding-001
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
SIMILARITY_THRESHOLD=0.7
MAX_CONTEXT_LENGTH=8000
```

> Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/).

### 4. Add university documents

Place your PDF files inside the `pdf/` directory.

### 5. Ingest documents

```bash
python load_document.py
```

### 6. Run the application

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

---

## Usage

1. **Register** a new account or **log in** with existing credentials.
2. Use the **chat interface** to ask questions about university documents.
3. Navigate to the **Email Generator** page to create formal administrative emails.
4. Admin users have access to additional administrative query capabilities.

---

## Configuration Reference

All settings can be overridden via environment variables or the `.env` file:

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `LLM_MODEL` | `models/gemini-2.5-flash` | Gemini model for chat |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Gemini model for embeddings |
| `CHROMA_DB_PATH` | `./chroma_db` | ChromaDB persistence directory |
| `SQLITE_DB_PATH` | `./student_results.db` | SQLite database path |
| `PDF_DIRECTORY` | `./pdf` | Directory for source PDFs |
| `CHUNK_SIZE` | `500` | Document chunk size (tokens) |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K_RESULTS` | `5` | Number of retrieved chunks per query |
| `SIMILARITY_THRESHOLD` | `0.7` | Minimum similarity score for results |

---

## License

This project is for educational and administrative use within a university context.
