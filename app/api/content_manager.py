import os
import json
import re
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from app.api.pptx_extractor import PPTXExtractor

class ContentManager:
    """Manages the extraction, storage, and retrieval of MOAD content."""
    
    def __init__(self, pptx_path: str, cache_path: str = "moad_content.json", 
                 embeddings_path: str = "moad_embeddings.json"):
        """
        Initialize the content manager.
        
        Args:
            pptx_path: Path to the MOAD PowerPoint file
            cache_path: Path to cache the extracted content
            embeddings_path: Path to cache the content embeddings
        """
        self.pptx_path = pptx_path
        self.cache_path = cache_path
        self.embeddings_path = embeddings_path
        self.content = {}
        self.embeddings = {}
        self.enable_semantic_search = True  # Can be toggled if embeddings unavailable
        
    def load_content(self) -> Dict[str, str]:
        """
        Load content either from cache or by extracting from PPTX.
        
        Returns:
            Dictionary mapping slide IDs to slide content
        """
        # Check if cached content exists
        if os.path.exists(self.cache_path):
            print(f"Loading cached content from {self.cache_path}")
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.content = json.load(f)
                print(f"Successfully loaded {len(self.content)} slides from cache")
                
                # Try to load embeddings if available
                if os.path.exists(self.embeddings_path):
                    try:
                        with open(self.embeddings_path, 'r', encoding='utf-8') as f:
                            self.embeddings = json.load(f)
                        print(f"Successfully loaded embeddings for {len(self.embeddings)} slides")
                    except Exception as e:
                        print(f"Warning: Could not load embeddings, semantic search disabled: {str(e)}")
                        self.enable_semantic_search = False
                else:
                    print("No embeddings file found, semantic search disabled")
                    self.enable_semantic_search = False
                
                return self.content
            except Exception as e:
                print(f"Error loading cached content: {str(e)}")
                # Fall back to extraction if cache loading fails
        
        # Extract content from PPTX
        if os.path.exists(self.pptx_path):
            print(f"Extracting content from {self.pptx_path}")
            try:
                extractor = PPTXExtractor(self.pptx_path)
                self.content = extractor.extract_content()
                print(f"Successfully extracted {len(self.content)} slides")
                
                # Save to cache
                self.save_to_cache()
                
                # Generate embeddings if possible
                try:
                    self._generate_embeddings()
                except Exception as e:
                    print(f"Warning: Could not generate embeddings, semantic search disabled: {str(e)}")
                    self.enable_semantic_search = False
                
                return self.content
            except Exception as e:
                print(f"Error extracting content: {str(e)}")
                return {}
        else:
            print(f"PPTX file not found: {self.pptx_path}")
            return {}
    
    def save_to_cache(self) -> bool:
        """
        Save the extracted content to a cache file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.content, f, ensure_ascii=False, indent=2)
            print(f"Content saved to cache: {self.cache_path}")
            return True
        except Exception as e:
            print(f"Error saving to cache: {str(e)}")
            return False
    
    def _generate_embeddings(self) -> bool:
        """
        Generate embeddings for all slides using OpenAI API.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import openai
            import os
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("Warning: OpenAI API key not found, semantic search disabled")
                self.enable_semantic_search = False
                return False
            
            client = openai.OpenAI(api_key=api_key)
            embeddings_dict = {}
            
            print("Generating embeddings for all slides...")
            for slide_id, content in self.content.items():
                # Use only the first 8000 chars to stay within token limits
                truncated_content = content[:8000]
                
                response = client.embeddings.create(
                    input=truncated_content,
                    model="text-embedding-3-small"
                )
                
                embeddings_dict[slide_id] = response.data[0].embedding
                
            # Save embeddings to file
            with open(self.embeddings_path, 'w', encoding='utf-8') as f:
                json.dump(embeddings_dict, f)
                
            self.embeddings = embeddings_dict
            print(f"Successfully generated and saved embeddings for {len(embeddings_dict)} slides")
            self.enable_semantic_search = True
            return True
            
        except Exception as e:
            print(f"Error generating embeddings: {str(e)}")
            self.enable_semantic_search = False
            return False
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for a text string using OpenAI API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            import openai
            import os
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            
            client = openai.OpenAI(api_key=api_key)
            
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            print(f"Error getting embedding: {str(e)}")
            return None
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            a: First vector
            b: Second vector
            
        Returns:
            Cosine similarity score
        """
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def get_relevant_slides(self, query: str, max_results: int = 10, 
                           use_semantic: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Retrieve slides relevant to the query using hybrid search.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            use_semantic: Whether to use semantic search (if available)
            
        Returns:
            List of dictionaries with slide ID and content
        """
        # Determine whether to use semantic search
        should_use_semantic = self.enable_semantic_search
        if use_semantic is not None:
            should_use_semantic = use_semantic and self.enable_semantic_search
            
        # Check for license comparison queries
        is_license_query = self._is_license_comparison_query(query)
            
        if should_use_semantic:
            # Try semantic search
            try:
                semantic_results = self._semantic_search(query, max_results)
                
                # If this is a license comparison query and we didn't get good results,
                # fall back to specialized license search
                if is_license_query:
                    license_results = self._search_license_comparison(query, max_results)
                    # Merge results, prioritizing license-specific ones
                    combined_results = license_results + [r for r in semantic_results if r["slide_id"] not in [lr["slide_id"] for lr in license_results]]
                    return combined_results[:max_results]
                    
                return semantic_results
            except Exception as e:
                print(f"Semantic search failed: {str(e)}. Falling back to keyword search.")
                # Fall back to keyword search
        
        # Use keyword matching if semantic search is disabled or failed
        return self._keyword_search(query, max_results)
    
    def _semantic_search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search for relevant slides.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with slide ID and content
        """
        # Get embedding for query
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            raise ValueError("Failed to get embedding for query")
            
        # Calculate similarity scores
        scores = {}
        for slide_id, slide_embedding in self.embeddings.items():
            similarity = self.cosine_similarity(query_embedding, slide_embedding)
            scores[slide_id] = similarity
            
        # Sort by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Take top results
        results = []
        for slide_id, score in sorted_scores[:max_results]:
            content = self.content[slide_id]
            results.append({
                "slide_id": slide_id,
                "content": content,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "relevance_score": score
            })
            
        return results
    
    def _keyword_search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search for relevant slides.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with slide ID and content
        """
        # Enhanced keyword matching with weights for important terms
        relevant_slides = {}
        
        # Extract important terms
        important_terms = self._extract_important_terms(query)
        query_terms = query.lower().split()
        
        for slide_id, content in self.content.items():
            content_lower = content.lower()
            
            # Calculate base score from all query terms
            base_score = sum(1 for term in query_terms if term in content_lower)
            
            # Add extra weight for important terms
            important_score = sum(3 for term in important_terms if term in content_lower)
            
            # Add extra weight for exact phrases
            phrase_score = 2 if query.lower() in content_lower else 0
            
            total_score = base_score + important_score + phrase_score
            if total_score > 0:
                relevant_slides[slide_id] = total_score
        
        # Sort by relevance score
        sorted_slides = sorted(relevant_slides.items(), key=lambda x: x[1], reverse=True)
        
        # Take top results
        results = []
        for slide_id, score in sorted_slides[:max_results]:
            content = self.content[slide_id]
            results.append({
                "slide_id": slide_id,
                "content": content,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "relevance_score": score / (len(query_terms) + len(important_terms) + 2)  # Normalize score
            })
        
        # Check if the query is about license comparisons and add specialized search
        if self._is_license_comparison_query(query) and len(results) < max_results:
            license_results = self._search_license_comparison(query, max_results - len(results))
            # Merge results, avoiding duplicates
            results.extend([r for r in license_results if r["slide_id"] not in [res["slide_id"] for res in results]])
            results = results[:max_results]
        
        return results
    
    def _extract_important_terms(self, query: str) -> List[str]:
        """
        Extract important terms from the query.
        
        Args:
            query: The search query
            
        Returns:
            List of important terms
        """
        # Product names, features, and license types are important
        important_patterns = [
            r'\b(itsm|itom|csx|hrsd|csm|itbm)\b',  # Product names
            r'\b(virtual agent|workflow|now assist|ai|chatbot)\b',  # Features
            r'\b(standard|pro|enterprise|pro\+)\b',  # License types
        ]
        
        important_terms = []
        query_lower = query.lower()
        
        for pattern in important_patterns:
            matches = re.findall(pattern, query_lower)
            important_terms.extend(matches)
            
        return important_terms
    
    def _is_license_comparison_query(self, query: str) -> bool:
        """
        Check if query is about license comparisons.
        
        Args:
            query: The search query
            
        Returns:
            True if query is about license comparisons
        """
        query_lower = query.lower()
        
        # Check for license comparison indicators
        license_terms = ['license', 'edition', 'tier', 'standard', 'pro', 'enterprise', 'pro+']
        comparison_terms = ['compare', 'comparison', 'difference', 'vs', 'versus', 'between']
        
        has_license = any(term in query_lower for term in license_terms)
        has_comparison = any(term in query_lower for term in comparison_terms)
        
        return has_license and has_comparison
    
    def _search_license_comparison(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Specialized search for license comparison information.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with slide ID and content
        """
        feature_match = re.search(r'\b(virtual agent|workflow|now assist|ai|chatbot|search)\b', query.lower())
        feature = feature_match.group(1) if feature_match else None
        
        # Look for capability matrices and comparison charts
        capability_matrices = []
        for slide_id, content in self.content.items():
            content_lower = content.lower()
            
            # Check for indicators of capability matrices
            is_capability_matrix = ('capability' in content_lower and 'matrix' in content_lower) or 'feature matrix' in content_lower
            
            # Check for license comparison indicators
            has_license_comparison = any(term in content_lower for term in ['standard', 'pro', 'enterprise', 'pro+']) and any(term in content_lower for term in ['license', 'edition', 'tier'])
            
            # Check for feature reference if specified
            has_feature = not feature or feature in content_lower
            
            if (is_capability_matrix or has_license_comparison) and has_feature:
                # Calculate a relevance score
                relevance = 0
                if is_capability_matrix:
                    relevance += 2
                if has_license_comparison:
                    relevance += 2
                if feature and feature in content_lower:
                    relevance += 3
                if 'table' in content_lower:
                    relevance += 1
                    
                capability_matrices.append((slide_id, relevance))
        
        # Sort by relevance
        sorted_matrices = sorted(capability_matrices, key=lambda x: x[1], reverse=True)
        
        # Take top results
        results = []
        for slide_id, relevance in sorted_matrices[:max_results]:
            content = self.content[slide_id]
            results.append({
                "slide_id": slide_id,
                "content": content,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "relevance_score": relevance / 8.0  # Normalize score (max possible is 8)
            })
            
        return results 