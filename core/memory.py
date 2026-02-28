"""
Conversation Memory Module
Manages chat history and user context across sessions.
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import SQLITE_DB_PATH, MAX_CONVERSATION_HISTORY


class ConversationMemory:
    """
    Manages conversation history with persistence.
    """
    
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        """
        Initialize conversation memory.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()
        
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self) -> None:
        """Initialize conversation tables."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                intent TEXT,
                context_chunks TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_session 
            ON conversations(session_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
        
    def add_turn(
        self,
        session_id: str,
        query: str,
        response: str,
        user_id: str = None,
        intent: str = None,
        context_chunks: List[str] = None
    ) -> int:
        """
        Add a conversation turn.
        
        Args:
            session_id: Unique session identifier
            query: User's query
            response: Assistant's response
            user_id: Optional user identifier
            intent: Classified intent
            context_chunks: Retrieved context passages
            
        Returns:
            ID of the inserted record
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        chunks_str = "|".join(context_chunks) if context_chunks else ""
        
        c.execute("""
            INSERT INTO conversations 
            (session_id, user_id, query, response, intent, context_chunks)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, query, response, intent, chunks_str))
        
        record_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def get_history(
        self,
        session_id: str,
        limit: int = MAX_CONVERSATION_HISTORY
    ) -> List[Dict[str, str]]:
        """
        Get recent conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum turns to return
            
        Returns:
            List of conversation turns as dicts
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT query, response, intent, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))
        
        rows = c.fetchall()
        conn.close()
        
        # Return in chronological order
        history = []
        for row in reversed(rows):
            history.append({
                "user": row[0],
                "assistant": row[1],
                "intent": row[2],
                "timestamp": row[3]
            })
            
        return history
    
    def get_user_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all conversation history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum turns to return
            
        Returns:
            List of conversation turns
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT session_id, query, response, intent, timestamp
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "session_id": row[0],
                "user": row[1],
                "assistant": row[2],
                "intent": row[3],
                "timestamp": row[4]
            }
            for row in rows
        ]
    
    def clear_session(self, session_id: str) -> int:
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Session to clear
            
        Returns:
            Number of records deleted
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            DELETE FROM conversations WHERE session_id = ?
        """, (session_id,))
        
        deleted = c.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Summary with turn count, intents, duration
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT 
                COUNT(*) as turns,
                MIN(timestamp) as start_time,
                MAX(timestamp) as end_time
            FROM conversations
            WHERE session_id = ?
        """, (session_id,))
        
        row = c.fetchone()
        
        # Get intent distribution
        c.execute("""
            SELECT intent, COUNT(*) as count
            FROM conversations
            WHERE session_id = ?
            GROUP BY intent
        """, (session_id,))
        
        intents = {r[0]: r[1] for r in c.fetchall() if r[0]}
        conn.close()
        
        return {
            "session_id": session_id,
            "total_turns": row[0],
            "start_time": row[1],
            "end_time": row[2],
            "intents": intents
        }


class SessionMemory:
    """
    In-memory session storage for active conversations.
    Use for fast access during active sessions.
    """
    
    def __init__(self, max_turns: int = MAX_CONVERSATION_HISTORY):
        """
        Initialize session memory.
        
        Args:
            max_turns: Maximum turns to keep in memory
        """
        self.max_turns = max_turns
        self._sessions: Dict[str, List[Dict]] = {}
        
    def add_turn(self, session_id: str, query: str, response: str) -> None:
        """Add a turn to session memory."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            
        self._sessions[session_id].append({
            "user": query,
            "assistant": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim to max turns
        if len(self._sessions[session_id]) > self.max_turns:
            self._sessions[session_id] = self._sessions[session_id][-self.max_turns:]
            
    def get_history(self, session_id: str) -> List[Dict]:
        """Get history for a session."""
        return self._sessions.get(session_id, [])
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session from memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            
    def get_context_string(self, session_id: str, last_n: int = 3) -> str:
        """Get recent history as a formatted string."""
        history = self.get_history(session_id)[-last_n:]
        
        if not history:
            return ""
            
        lines = []
        for turn in history:
            lines.append(f"User: {turn['user']}")
            lines.append(f"Assistant: {turn['assistant']}")
            
        return "\n".join(lines)


# Singleton instances
_conversation_memory = None
_session_memory = None

def get_conversation_memory() -> ConversationMemory:
    """Get conversation memory instance."""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory

def get_session_memory() -> SessionMemory:
    """Get session memory instance."""
    global _session_memory
    if _session_memory is None:
        _session_memory = SessionMemory()
    return _session_memory
