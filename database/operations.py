"""
Database Operations Module
Common database operations for user management.
"""
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import SQLITE_DB_PATH


class DatabaseOperations:
    """
    Common database operations for the application.
    """
    
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        """
        Initialize database operations.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()
        
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self) -> None:
        """Initialize all required tables."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'student',
                email TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        """)
        
        # Create indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        
        conn.commit()
        conn.close()
    
    # User Operations
    
    def create_user(
        self,
        username: str,
        password: str,
        role: str = "student",
        email: str = None
    ) -> bool:
        """
        Create a new user.
        
        Args:
            username: Unique username
            password: User's password (should be hashed in production)
            role: User role (student, faculty, admin)
            email: Optional email address
            
        Returns:
            True if created, False if username exists
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT INTO users (username, password, role, email)
                VALUES (?, ?, ?, ?)
            """, (username, password, role, email))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate a user.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User dict if authenticated, None otherwise
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT id, username, role, email
            FROM users
            WHERE username = ? AND password = ?
        """, (username, password))
        
        row = c.fetchone()
        
        if row:
            # Update last login
            c.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE username = ?
            """, (username,))
            conn.commit()
            conn.close()
            
            return {
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "email": row[3]
            }
        
        conn.close()
        return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT id, username, role, email, created_at, last_login
            FROM users WHERE username = ?
        """, (username,))
        
        row = c.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "email": row[3],
                "created_at": row[4],
                "last_login": row[5]
            }
        return None
    
    def update_user_role(self, username: str, role: str) -> bool:
        """Update a user's role."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            UPDATE users SET role = ? WHERE username = ?
        """, (role, username))
        
        updated = c.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    def get_all_users(self, limit: int = 100) -> List[Dict]:
        """Get all users."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT id, username, role, email, created_at, last_login
            FROM users
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "email": row[3],
                "created_at": row[4],
                "last_login": row[5]
            }
            for row in rows
        ]
    
    # Analytics Operations
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # User stats
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        
        c.execute("""
            SELECT role, COUNT(*) FROM users GROUP BY role
        """)
        users_by_role = {row[0]: row[1] for row in c.fetchall()}
        
        # Conversation stats (from conversations table if exists)
        try:
            c.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = c.fetchone()[0]
        except:
            total_conversations = 0
        
        conn.close()
        
        return {
            "total_users": total_users,
            "users_by_role": users_by_role,
            "total_conversations": total_conversations
        }


# Singleton instance
_db_ops = None

def get_db_operations() -> DatabaseOperations:
    """Get database operations singleton."""
    global _db_ops
    if _db_ops is None:
        _db_ops = DatabaseOperations()
    return _db_ops
