import os
import sqlite3
from typing import List, Dict, Any, Optional
import json
from app.api.pptx_extractor import PPTXExtractor

class DatabaseManager:
    """Manages the storage and retrieval of MOAD content in a SQLite database."""
    
    def __init__(self, db_path: str = "moad_db.sqlite", pptx_path: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database
            pptx_path: Path to the MOAD PowerPoint file (optional)
        """
        self.db_path = db_path
        self.pptx_path = pptx_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create slides table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS slides (
            slide_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            content_preview TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create queries table for caching
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            query_text TEXT PRIMARY KEY,
            result TEXT NOT NULL,
            timestamp REAL NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def import_from_pptx(self, pptx_path: Optional[str] = None) -> int:
        """
        Import content from a PowerPoint file into the database.
        
        Args:
            pptx_path: Path to the PowerPoint file (optional)
            
        Returns:
            Number of slides imported
        """
        if pptx_path is None:
            pptx_path = self.pptx_path
        
        if not pptx_path or not os.path.exists(pptx_path):
            print(f"PPTX file not found: {pptx_path}")
            return 0
        
        try:
            print(f"Extracting content from {pptx_path}")
            extractor = PPTXExtractor(pptx_path)
            content = extractor.extract_content()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            count = 0
            for slide_id, slide_content in content.items():
                content_preview = slide_content[:200] + "..." if len(slide_content) > 200 else slide_content
                
                cursor.execute(
                    "INSERT OR REPLACE INTO slides (slide_id, content, content_preview) VALUES (?, ?, ?)",
                    (slide_id, slide_content, content_preview)
                )
                count += 1
            
            conn.commit()
            conn.close()
            
            print(f"Successfully imported {count} slides into the database")
            return count
            
        except Exception as e:
            print(f"Error importing from PPTX: {str(e)}")
            return 0
    
    def get_slides_count(self) -> int:
        """
        Get the number of slides in the database.
        
        Returns:
            Number of slides
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM slides")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def find_relevant_slides(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Find slides relevant to the query.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with slide information
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Split query into terms
        query_terms = query.lower().split()
        
        # Get all slides from the database
        cursor.execute("SELECT slide_id, content, content_preview FROM slides")
        all_slides = cursor.fetchall()
        conn.close()
        
        # Score slides based on query terms
        scored_slides = []
        for slide in all_slides:
            content = slide['content'].lower()
            score = sum(1 for term in query_terms if term in content)
            if score > 0:
                scored_slides.append({
                    'score': score,
                    'slide_id': slide['slide_id'],
                    'content': slide['content'],
                    'content_preview': slide['content_preview']
                })
        
        # Sort by score and limit results
        scored_slides.sort(key=lambda x: x['score'], reverse=True)
        return scored_slides[:max_results]
    
    def cache_query(self, query: str, result: Dict[str, Any], expiry_time: int = 86400) -> bool:
        """
        Cache a query result in the database.
        
        Args:
            query: The query string
            result: The result to cache
            expiry_time: Cache expiry time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Normalize query
            normalized_query = ' '.join(query.lower().split())
            
            # Convert result to JSON string
            result_json = json.dumps(result)
            
            # Current timestamp
            import time
            timestamp = time.time()
            
            cursor.execute(
                "INSERT OR REPLACE INTO queries (query_text, result, timestamp) VALUES (?, ?, ?)",
                (normalized_query, result_json, timestamp)
            )
            
            conn.commit()
            conn.close()
            
            print(f"Cached query result for: {normalized_query}")
            return True
            
        except Exception as e:
            print(f"Error caching query: {str(e)}")
            return False
    
    def get_cached_query(self, query: str, expiry_time: int = 86400) -> Optional[Dict[str, Any]]:
        """
        Get a cached query result.
        
        Args:
            query: The query string
            expiry_time: Cache expiry time in seconds
            
        Returns:
            Cached result or None if not found or expired
        """
        try:
            # Normalize query
            normalized_query = ' '.join(query.lower().split())
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT result, timestamp FROM queries WHERE query_text = ?",
                (normalized_query,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                print(f"Query cache miss for: {normalized_query}")
                return None
            
            # Check if cache is expired
            import time
            if time.time() - row['timestamp'] > expiry_time:
                print(f"Query cache expired for: {normalized_query}")
                return None
            
            # Parse JSON result
            result = json.loads(row['result'])
            print(f"Query cache hit for: {normalized_query}")
            
            return result
            
        except Exception as e:
            print(f"Error retrieving cached query: {str(e)}")
            return None 