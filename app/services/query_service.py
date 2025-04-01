import os
import logging
from flask import current_app
from app.models.query_cache import QueryCache
from app.services.openai_service import OpenAIService
from app.utils.moad_embeddings import MOADEmbeddings

logger = logging.getLogger(__name__)

class QueryService:
    """Service for handling ServiceNow MOAD queries"""
    
    def __init__(self):
        """Initialize the query service with embeddings, OpenAI service, and cache"""
        self.embeddings = MOADEmbeddings()
        self.openai_service = OpenAIService()
        
        # Initialize cache with configurable max age
        cache_max_age = current_app.config.get('CACHE_MAX_AGE', 24) if current_app else 24
        self.cache = QueryCache(max_age_hours=cache_max_age)
        
        logger.info(f"QueryService initialized with cache max age: {cache_max_age} hours")
    
    def process_query(self, query, bypass_cache=False):
        """
        Process a user query about ServiceNow MOAD
        
        Args:
            query (str): The user's question about ServiceNow
            bypass_cache (bool): If True, bypass cache and force a fresh response
            
        Returns:
            tuple: (result_dict, is_cached) - The query result and whether it was from cache
        """
        # Check if we can use a cached result
        if not bypass_cache:
            cached_result = self.cache.get(query)
            if cached_result:
                logger.info(f"Cache hit for query: {query}")
                return cached_result, True
        
        # No cached result, need to process the query
        logger.info(f"Processing fresh query: {query}")
        
        # Get relevant context from embeddings
        context = self.embeddings.get_relevant_context(query)
        
        if not context:
            logger.warning(f"No relevant context found for query: {query}")
            return {
                'summary': "I couldn't find any relevant information about ServiceNow to answer your query.",
                'sources': []
            }, False
        
        # Generate a response using OpenAI
        response = self.openai_service.generate_response(query, context)
        
        # Store the result in cache
        self.cache.set(query, response)
        
        return response, False
    
    def clear_cache(self, query=None):
        """
        Clear the query cache
        
        Args:
            query (str, optional): Specific query to clear from cache. If None, clears all cache.
        """
        if query:
            self.cache.delete(query)
            logger.info(f"Cleared cache for query: {query}")
        else:
            self.cache.clear()
            logger.info("Cleared entire query cache")
        
        return True 