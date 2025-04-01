import os
import json
import time
from typing import List, Dict, Any

class ContentService:
    """Service for managing content extracted from the MOAD PowerPoint."""
    
    def __init__(self, pptx_path: str = "moad.pptx", json_path: str = "moad_content.json"):
        """
        Initialize the content service.
        
        Args:
            pptx_path: Path to the MOAD PowerPoint file
            json_path: Path to the cached JSON content file
        """
        self.pptx_path = pptx_path
        self.json_path = json_path
        self.moad_content = {}
        
    def load_content(self) -> Dict[str, Any]:
        """
        Load content from cache or extract from PowerPoint.
        
        Returns:
            Dictionary mapping slide IDs to slide content
        """
        start_time = time.time()
        print("Loading MOAD content...")
        
        # Check if the JSON cache exists
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.moad_content = json.load(f)
                print(f"Loaded content from cache: {len(self.moad_content)} slides")
            except Exception as e:
                print(f"Error loading from cache: {str(e)}")
                self._extract_content_from_pptx()
        else:
            # Extract from PowerPoint if cache doesn't exist
            self._extract_content_from_pptx()
        
        print(f"Content loading completed in {time.time() - start_time:.2f} seconds")
        return self.moad_content
    
    def _extract_content_from_pptx(self):
        """Extract content directly from the PowerPoint file."""
        try:
            # Import here to avoid dependency issues if not needed
            from app.utils.extractors.pptx_extractor import PPTXExtractor
            
            print(f"Extracting content from PowerPoint: {self.pptx_path}")
            extractor = PPTXExtractor(self.pptx_path)
            self.moad_content = extractor.extract_all_slides()
            
            # Save to cache for future use
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.moad_content, f, ensure_ascii=False, indent=2)
            
            print(f"Extracted and cached {len(self.moad_content)} slides")
        except Exception as e:
            print(f"Error extracting content: {str(e)}")
            # Initialize with empty content if extraction fails
            self.moad_content = {}
    
    def get_relevant_slides(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get slides relevant to the given query.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of relevant slides with metadata
        """
        # For now, this is a simple keyword search
        # This could be extended with vector search or other techniques
        relevant_slides = []
        query_terms = set(query.lower().split())
        
        # Calculate relevance scores for each slide
        relevance_scores = {}
        for slide_id, content in self.moad_content.items():
            content_lower = content.lower()
            
            # Calculate a simple relevance score based on term frequency
            score = sum(content_lower.count(term) for term in query_terms if term in content_lower)
            
            # Add bonus for slides with exact phrases
            for i in range(len(query_terms) - 1):
                phrase = ' '.join(list(query_terms)[i:i+2])
                if phrase in content_lower:
                    score += 5
            
            if score > 0:
                relevance_scores[slide_id] = score
        
        # Sort slides by relevance score
        sorted_slides = sorted(relevance_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Prepare slide data with previews for the top results
        for slide_id, score in sorted_slides[:max_results]:
            content = self.moad_content[slide_id]
            
            # Create a content preview (first 100 characters)
            content_preview = content[:200] + "..." if len(content) > 200 else content
            
            relevant_slides.append({
                "slide_id": slide_id,
                "content": content,
                "content_preview": content_preview,
                "relevance_score": score
            })
        
        return relevant_slides 