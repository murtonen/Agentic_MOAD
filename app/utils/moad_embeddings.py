import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MOADEmbeddings:
    """Handles embeddings-based search for MOAD content"""
    
    def __init__(self, embeddings_path: str = None):
        """
        Initialize MOAD embeddings utility
        
        Args:
            embeddings_path: Path to the embeddings data file
        """
        if embeddings_path is None:
            # Default to the data directory in the project
            embeddings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                          'data', 'moad_embeddings.json')
        
        self.embeddings_path = embeddings_path
        self.embeddings_data = self._load_embeddings()
        
        if self.embeddings_data:
            logger.info(f"Loaded {len(self.embeddings_data.get('chunks', []))} MOAD content chunks")
        else:
            logger.warning("Failed to load MOAD embeddings data")
    
    def _load_embeddings(self) -> Optional[Dict[str, Any]]:
        """
        Load embeddings data from file
        
        Returns:
            Dictionary containing embeddings data or None if loading fails
        """
        try:
            if not os.path.exists(self.embeddings_path):
                logger.error(f"Embeddings file not found: {self.embeddings_path}")
                return None
                
            with open(self.embeddings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading embeddings: {str(e)}")
            return None
    
    def get_relevant_context(self, query: str, max_chunks: int = 5) -> List[Dict[str, Any]]:
        """
        Get relevant content chunks for a query
        
        Args:
            query: The user query
            max_chunks: Maximum number of chunks to return
            
        Returns:
            List of relevant content dictionaries with content and metadata
        """
        if not self.embeddings_data or 'chunks' not in self.embeddings_data:
            logger.error("No embeddings data available")
            return []
            
        # This is a simplified version. In a real implementation, you would:
        # 1. Generate embedding for the query using OpenAI or other embedding model
        # 2. Calculate similarity scores with all chunks
        # 3. Return the most similar chunks
        
        # For now, we'll return the first few chunks (placeholder implementation)
        relevant_chunks = []
        chunks = self.embeddings_data.get('chunks', [])
        
        # Simple keyword matching as placeholder
        matched_chunks = []
        query_terms = set(query.lower().split())
        
        for chunk in chunks:
            content = chunk.get('content', '').lower()
            match_score = sum(1 for term in query_terms if term in content)
            if match_score > 0:
                matched_chunks.append((chunk, match_score))
        
        # Sort by match score and take top results
        matched_chunks.sort(key=lambda x: x[1], reverse=True)
        relevant_chunks = [chunk for chunk, _ in matched_chunks[:max_chunks]]
        
        if not relevant_chunks and chunks:
            # Fallback to first few chunks if no matches
            relevant_chunks = chunks[:max_chunks]
            
        logger.info(f"Found {len(relevant_chunks)} relevant chunks for query: {query}")
        return relevant_chunks 