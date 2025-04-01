import os
import json
import time
import re
from typing import Dict, Any, Optional

class QueryCache:
    """Class to manage cached query results."""
    
    def __init__(self, cache_file: str = "query_cache.json", expiry_time: int = 86400):
        """
        Initialize the query cache.
        
        Args:
            cache_file: Path to the cache file
            expiry_time: Time in seconds before a cache entry expires (default: 24 hours)
        """
        self.cache_file = cache_file
        self.expiry_time = expiry_time
        self.cache = self.load_cache()
    
    def load_cache(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                # Remove expired entries
                current_time = time.time()
                cache = {
                    k: v for k, v in cache.items()
                    if 'timestamp' not in v or current_time - v['timestamp'] < self.expiry_time
                }
                return cache
            except Exception as e:
                print(f"Error loading cache: {str(e)}")
                return {}
        return {}
    
    def save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {str(e)}")
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize a query for consistent caching.
        
        Args:
            query: The query to normalize
            
        Returns:
            Normalized query string
        """
        # Convert to lowercase and remove extra whitespace
        query = query.lower().strip()
        query = re.sub(r'\s+', ' ', query)
        return query
    
    def get(self, query: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get cached result for a query.
        
        Args:
            query: The query to look up
            force_refresh: If True, ignores cache and returns None
            
        Returns:
            Cached result or None if not found or expired
        """
        if force_refresh:
            return None
            
        normalized_query = self._normalize_query(query)
        if normalized_query in self.cache:
            cache_entry = self.cache[normalized_query]
            # Check if entry has expired
            if 'timestamp' in cache_entry:
                current_time = time.time()
                if current_time - cache_entry['timestamp'] < self.expiry_time:
                    print(f"Query cache hit for: {query}")
                    return cache_entry['result']
                else:
                    # Remove expired entry
                    del self.cache[normalized_query]
                    self.save_cache()
        return None
    
    def set(self, query: str, result: Dict[str, Any]):
        """
        Store a query result in the cache.
        
        Args:
            query: The query to cache
            result: The result to cache
        """
        normalized_query = self._normalize_query(query)
        self.cache[normalized_query] = {
            'result': result,
            'timestamp': time.time()
        }
        self.save_cache()
        
    def clear(self, query: Optional[str] = None):
        """
        Clear specific query from cache or entire cache if query is None.
        
        Args:
            query: Specific query to clear, or None to clear all
        """
        if query is None:
            self.cache = {}
        else:
            normalized_query = self._normalize_query(query)
            if normalized_query in self.cache:
                del self.cache[normalized_query]
        self.save_cache() 