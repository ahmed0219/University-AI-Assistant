"""
Admin Agent Module
Handles administrative queries and database operations with function calling.
"""
import sqlite3
from typing import Dict, Any, List, Optional
from core.llm import get_llm_client
from config import SQLITE_DB_PATH


class AdminAgent:
    """
    Agent for administrative queries about system data and users.
    """
    
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        """
        Initialize Admin agent.
        
        Args:
            db_path: Path to SQLite database
        """
        self.llm = get_llm_client()
        self.db_path = db_path
        
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Process an administrative query.
        
        Args:
            user_query: Natural language query
            
        Returns:
            Response with answer and data
        """
        # Get database schema
        schema = self._get_schema()
        
        # Generate SQL query
        sql = self._generate_sql(user_query, schema)
        
        if not sql:
            return {
                "answer": "I couldn't understand that query. Could you rephrase it?",
                "data": None
            }
        
        # Execute query safely
        try:
            results = self._execute_query(sql)
            
            # Generate natural language response
            answer = self._format_response(user_query, sql, results)
            
            return {
                "answer": answer,
                "data": results,
                "sql": sql
            }
        except Exception as e:
            return {
                "answer": f"I encountered an error executing that query: {str(e)}",
                "data": None,
                "error": str(e)
            }
    
    def _get_schema(self) -> str:
        """Get database schema as string."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Get all tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        
        schema_parts = []
        for (table_name,) in tables:
            c.execute(f"PRAGMA table_info({table_name});")
            columns = c.fetchall()
            cols = [f"{col[1]} ({col[2]})" for col in columns]
            schema_parts.append(f"Table: {table_name}\nColumns: {', '.join(cols)}")
        
        conn.close()
        return "\n\n".join(schema_parts)
    
    def _generate_sql(self, user_query: str, schema: str) -> Optional[str]:
        """Generate SQL from natural language query."""
        prompt = f"""You are a SQL expert. Convert the following natural language query to SQL.

Database Schema:
{schema}

User Query: "{user_query}"

Rules:
- Only generate SELECT queries (no INSERT, UPDATE, DELETE)
- Use proper SQL syntax for SQLite
- Return ONLY the SQL query, nothing else
- If the query cannot be answered with the schema, return "INVALID"

SQL Query:"""

        response = self.llm.generate(prompt, temperature=0.1)
        sql = response.strip()
        
        # Clean up response
        sql = sql.replace("```sql", "").replace("```", "").strip()
        
        if "INVALID" in sql.upper() or not sql.upper().startswith("SELECT"):
            return None
            
        return sql
    
    def _execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results."""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute(sql)
        rows = c.fetchall()
        
        results = [dict(row) for row in rows]
        conn.close()
        
        return results
    
    def _format_response(
        self,
        user_query: str,
        sql: str,
        results: List[Dict]
    ) -> str:
        """Format query results into natural language."""
        if not results:
            return "No results found matching your query."
        
        # Summarize results for the LLM
        results_preview = str(results[:10])  # Limit for prompt size
        
        prompt = f"""Convert these database results into a natural, helpful response.

User asked: "{user_query}"

Results (showing up to 10 of {len(results)} total):
{results_preview}

Provide a clear, natural language summary of the data. Include specific numbers and names where relevant.
Keep the response concise but informative."""

        return self.llm.generate(prompt, temperature=0.3)
    
    # Convenience methods for common queries
    
    def get_user_count(self) -> int:
        """Get total number of registered users."""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        count = c.fetchone()[0]
        conn.close()
        return count
    
    def get_users_by_role(self) -> Dict[str, int]:
        """Get user count by role."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT role, COUNT(*) as count
            FROM users
            GROUP BY role
        """)
        
        rows = c.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in rows}
    
    def get_recent_users(self, limit: int = 10) -> List[Dict]:
        """Get recently registered users."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT username, role, created_at, last_login
            FROM users
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "username": row[0],
                "role": row[1],
                "created_at": row[2],
                "last_login": row[3]
            }
            for row in rows
        ]
