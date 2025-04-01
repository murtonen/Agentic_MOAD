import os
import json
import logging
from typing import Dict, List, Any
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI API to generate responses"""
    
    def __init__(self):
        """Initialize the OpenAI service with API key"""
        self.api_key = os.environ.get('OPENAI_API_KEY')
        
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables")
        else:
            logger.info("OpenAI service initialized successfully")
    
    def generate_response(self, query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a response to a query using context from embeddings
        
        Args:
            query: The user query
            context: List of context chunks with content
        
        Returns:
            Dictionary containing summary and sources information
        """
        try:
            if not self.api_key:
                return {
                    'summary': "ERROR: OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable.",
                    'sources': []
                }
            
            # Format context chunks
            formatted_context = ""
            sources = []
            
            for i, chunk in enumerate(context):
                # Extract content and metadata for the prompt
                content = chunk.get('content', '')
                slide_title = chunk.get('title', f'Source {i+1}')
                slide_number = chunk.get('slide_number')
                
                # Add to formatted context
                formatted_context += f"\n--- SOURCE {i+1} ---\n"
                formatted_context += f"Title: {slide_title}\n"
                if slide_number:
                    formatted_context += f"Slide: {slide_number}\n"
                formatted_context += f"Content: {content}\n"
                
                # Add to sources for the response
                sources.append({
                    'title': slide_title,
                    'content': content[:150] + '...' if len(content) > 150 else content,
                    'slide_number': slide_number
                })
            
            # Create system prompt
            system_prompt = """
            You are a ServiceNow expert providing information about ServiceNow products, licenses, and features.
            Your task is to answer questions accurately based ONLY on the provided source information.
            If the information provided doesn't contain an answer, say so clearly.
            Format your answers in a structured way using markdown and bullet points when appropriate.
            For license comparisons, use consistent symbols (✓ for included, ✗ for not included) and structure.
            """
            
            # Create user prompt
            user_prompt = f"""
            Question: {query}
            
            Please provide an accurate answer based ONLY on the following sources:
            
            {formatted_context}
            
            Answer the question in a concise way, maintaining accuracy and using ONLY the information in these sources.
            """
            
            # Call OpenAI API
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o",  # Or use a different model as needed
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,  # Keep it factual
                max_tokens=800
            )
            
            # Extract response
            summary = response.choices[0].message.content.strip()
            
            # Return formatted result
            return {
                'summary': summary,
                'sources': sources
            }
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {str(e)}", exc_info=True)
            return {
                'summary': f"An error occurred while generating a response: {str(e)}",
                'sources': []
            } 