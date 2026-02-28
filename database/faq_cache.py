"""
FAQ Cache Module
Caches frequently asked questions for faster response times.
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from config import SQLITE_DB_PATH, FAQ_CACHE_TTL_HOURS, MAX_CACHE_SIZE


class FAQCache:
    """
    Cache for frequently asked questions to reduce redundant LLM calls.
    """
    
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        """
        Initialize FAQ cache.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.ttl_hours = FAQ_CACHE_TTL_HOURS
        self.max_size = MAX_CACHE_SIZE
        self._init_db()
        
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self) -> None:
        """Initialize cache table."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS faq_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT UNIQUE NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                hit_count INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_hash 
            ON faq_cache(query_hash)
        """)
        
        conn.commit()
        conn.close()
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query normalization."""
        # Normalize: lowercase, strip whitespace, remove extra spaces
        normalized = " ".join(query.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]
    
    def get(self, query: str) -> Optional[str]:
        """
        Get cached response for a query.
        
        Args:
            query: User's query
            
        Returns:
            Cached response or None
        """
        query_hash = self._hash_query(query)
        conn = self._get_conn()
        c = conn.cursor()
        
        # Check cache with TTL
        ttl_cutoff = datetime.now() - timedelta(hours=self.ttl_hours)
        
        c.execute("""
            SELECT response FROM faq_cache
            WHERE query_hash = ? AND created_at > ?
        """, (query_hash, ttl_cutoff))
        
        row = c.fetchone()
        
        if row:
            # Update hit count and last accessed
            c.execute("""
                UPDATE faq_cache
                SET hit_count = hit_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE query_hash = ?
            """, (query_hash,))
            conn.commit()
            conn.close()
            return row[0]
        
        conn.close()
        return None
    
    def set(self, query: str, response: str) -> None:
        """
        Cache a query-response pair.
        
        Args:
            query: User's query
            response: Generated response
        """
        query_hash = self._hash_query(query)
        conn = self._get_conn()
        c = conn.cursor()
        
        # Upsert
        c.execute("""
            INSERT INTO faq_cache (query_hash, query, response)
            VALUES (?, ?, ?)
            ON CONFLICT(query_hash) DO UPDATE SET
                response = excluded.response,
                hit_count = hit_count + 1,
                last_accessed = CURRENT_TIMESTAMP
        """, (query_hash, query, response))
        
        conn.commit()
        
        # Cleanup if over max size
        self._cleanup_if_needed(conn)
        
        conn.close()
    
    def _cleanup_if_needed(self, conn: sqlite3.Connection) -> None:
        """Remove old entries if cache exceeds max size."""
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM faq_cache")
        count = c.fetchone()[0]
        
        if count > self.max_size:
            # Remove least recently accessed entries
            excess = count - self.max_size
            c.execute("""
                DELETE FROM faq_cache
                WHERE id IN (
                    SELECT id FROM faq_cache
                    ORDER BY last_accessed ASC
                    LIMIT ?
                )
            """, (excess,))
            conn.commit()
    
    def get_popular_queries(self, limit: int = 10) -> List[Dict]:
        """
        Get most frequently asked questions.
        
        Args:
            limit: Number of queries to return
            
        Returns:
            List of popular queries with hit counts
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT query, response, hit_count, last_accessed
            FROM faq_cache
            ORDER BY hit_count DESC
            LIMIT ?
        """, (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "query": row[0],
                "response": row[1][:200] + "..." if len(row[1]) > 200 else row[1],
                "hit_count": row[2],
                "last_accessed": row[3]
            }
            for row in rows
        ]
    
    def invalidate(self, query: str = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            query: Specific query to invalidate (all if None)
            
        Returns:
            Number of entries invalidated
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        if query:
            query_hash = self._hash_query(query)
            c.execute("DELETE FROM faq_cache WHERE query_hash = ?", (query_hash,))
        else:
            c.execute("DELETE FROM faq_cache")
        
        deleted = c.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT 
                COUNT(*) as total_entries,
                SUM(hit_count) as total_hits,
                AVG(hit_count) as avg_hits
            FROM faq_cache
        """)
        
        row = c.fetchone()
        
        # Entries by age
        c.execute("""
            SELECT 
                COUNT(CASE WHEN created_at > datetime('now', '-1 day') THEN 1 END) as day_old,
                COUNT(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 END) as week_old,
                COUNT(*) as total
            FROM faq_cache
        """)
        
        age_row = c.fetchone()
        conn.close()
        
        return {
            "total_entries": row[0] or 0,
            "total_hits": row[1] or 0,
            "average_hits": round(row[2] or 0, 1),
            "entries_last_24h": age_row[0] or 0,
            "entries_last_week": age_row[1] or 0,
            "cache_utilization": round((row[0] or 0) / self.max_size * 100, 1)
        }


# Decorator for caching function results
def cached_response(cache: FAQCache = None):
    """
    Decorator to cache function responses.
    
    Args:
        cache: FAQCache instance (creates new if None)
    """
    _cache = cache or FAQCache()
    
    def decorator(func):
        def wrapper(query: str, *args, **kwargs):
            # Try cache first
            cached = _cache.get(query)
            if cached:
                return cached
            
            # Generate and cache response
            response = func(query, *args, **kwargs)
            _cache.set(query, response)
            return response
        
        return wrapper
    return decorator


# Singleton instance
_faq_cache = None

def get_faq_cache() -> FAQCache:
    """Get FAQ cache singleton."""
    global _faq_cache
    if _faq_cache is None:
        _faq_cache = FAQCache()
    return _faq_cache
