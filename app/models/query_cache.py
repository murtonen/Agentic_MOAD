import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class QueryCache:
    """A simple cache for storing query results."""
    
    def __init__(self, cache_file: str = "query_cache.json", max_age_hours: float = 24):
        """
        Initialize the query cache.
        
        Args:
            cache_file: Path to the cache file
            max_age_hours: Maximum age of cache entries in hours
        """
        self.cache_file = cache_file
        self.max_age = timedelta(hours=max_age_hours)
        self.cache = self._load_cache()
        logger.info(f"Query cache initialized with max age of {max_age_hours} hours")
    
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached result for a query.
        
        Args:
            query: The query string
            
        Returns:
            Cached result or None if not found or expired
        """
        if query in self.cache:
            entry = self.cache[query]
            # Check if entry is expired
            timestamp = datetime.fromtimestamp(entry.get('timestamp', 0))
            if datetime.now() - timestamp < self.max_age:
                logger.debug(f"Cache hit for query: {query}")
                return entry.get('result')
            else:
                logger.debug(f"Cache entry expired for query: {query}")
        return None
    
    def set(self, query: str, result: Dict[str, Any]) -> None:
        """
        Store a result in the cache.
        
        Args:
            query: The query string
            result: The result to cache
        """
        self.cache[query] = {
            'result': result,
            'timestamp': datetime.now().timestamp()
        }
        self._save_cache()
        logger.debug(f"Cached result for query: {query}")
    
    def delete(self, query: str) -> bool:
        """
        Delete a specific query from the cache.
        
        Args:
            query: The query string to delete
            
        Returns:
            True if the query was deleted, False if it wasn't in the cache
        """
        if query in self.cache:
            del self.cache[query]
            self._save_cache()
            logger.debug(f"Deleted cache entry for query: {query}")
            return True
        return False
    
    def clear(self) -> None:
        """
        Clear the entire cache.
        """
        self.cache = {}
        self._save_cache()
        logger.info("Cleared entire query cache")
    
    def _load_cache(self) -> Dict[str, Any]:
        """
        Load the cache from disk.
        
        Returns:
            The loaded cache as a dictionary
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    logger.debug(f"Loaded {len(cache_data)} entries from cache file")
                    return cache_data
            except Exception as e:
                logger.error(f"Error loading cache: {str(e)}")
        return {}
    
    def _save_cache(self) -> None:
        """Save the cache to disk."""
        try:
            # Ensure the directory exists
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self.cache)} entries to cache file")
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")
    
    def cleanup(self) -> int:
        """
        Remove expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self.cache.items():
            timestamp = datetime.fromtimestamp(entry.get('timestamp', 0))
            if now - timestamp >= self.max_age:
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            self._save_cache()
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
        return len(expired_keys) 