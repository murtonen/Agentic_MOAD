from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Document(BaseModel):
    """Represents a document with content and metadata."""
    content: str
    metadata: Dict[str, Any] = {}
    
    class Config:
        arbitrary_types_allowed = True

class RetrievalAgent:
    """Agent responsible for retrieving relevant information from the MOAD."""
    
    def __init__(self, moad_content: Dict[str, Any]):
        """
        Initialize with the extracted MOAD content.
        
        Args:
            moad_content: Dictionary mapping slide IDs to slide content
        """
        self.moad_content = moad_content
        self.llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
        
        self.retrieval_prompt = PromptTemplate(
            input_variables=["query", "num_results"],
            template="""
            You are a retrieval agent for ServiceNow's Mother of All Decks (MOAD).
            Your task is to find the most relevant slides and content for the given query.
            
            Query: {query}
            
            Return the {num_results} most relevant slides that answer this query.
            ONLY return slides that are directly relevant to the query.
            """
        )
        
        self.retrieval_chain = LLMChain(llm=self.llm, prompt=self.retrieval_prompt)
    
    def retrieve(self, query: str, num_results: int = 5) -> List[Document]:
        """
        Retrieve relevant documents based on the query.
        
        Args:
            query: The user query
            num_results: Number of documents to retrieve
            
        Returns:
            List of Document objects
        """
        # Simple keyword matching for now, can be improved with vector search
        results = []
        
        # Rank slides based on relevance to query
        relevant_slides = {}
        for slide_id, content in self.moad_content.items():
            query_terms = query.lower().split()
            score = sum(1 for term in query_terms if term in content.lower())
            if score > 0:
                relevant_slides[slide_id] = score
        
        # Sort by relevance score
        sorted_slides = sorted(relevant_slides.items(), key=lambda x: x[1], reverse=True)
        
        # Take top results
        for slide_id, _ in sorted_slides[:num_results]:
            results.append(Document(
                content=self.moad_content[slide_id],
                metadata={"slide_id": slide_id}
            ))
        
        return results

class AnalysisAgent:
    """Agent responsible for analyzing retrieved information."""
    
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
        
        self.analysis_prompt = PromptTemplate(
            input_variables=["query", "documents"],
            template="""
            You are an analysis agent for ServiceNow's Mother of All Decks (MOAD).
            Your task is to analyze the retrieved documents and extract key information relevant to the query.
            
            Query: {query}
            
            Retrieved Documents:
            {documents}
            
            Analyze these documents and extract the key information that answers the query.
            ONLY use information explicitly stated in the retrieved documents.
            DO NOT add any information not present in the documents.
            """
        )
        
        self.analysis_chain = LLMChain(llm=self.llm, prompt=self.analysis_prompt)
    
    def analyze(self, query: str, documents: List[Document]) -> str:
        """
        Analyze retrieved documents to extract key information.
        
        Args:
            query: The user query
            documents: List of retrieved documents
            
        Returns:
            Analysis results
        """
        docs_text = "\n\n".join([f"Document {i+1}:\n{doc.content}" for i, doc in enumerate(documents)])
        return self.analysis_chain.run(query=query, documents=docs_text)

class VerificationAgent:
    """Agent responsible for verifying information accuracy."""
    
    def __init__(self, moad_content: Dict[str, Any]):
        self.moad_content = moad_content
        self.llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
        
        self.verification_prompt = PromptTemplate(
            input_variables=["analysis", "documents"],
            template="""
            You are a verification agent for ServiceNow's Mother of All Decks (MOAD).
            Your task is to verify that the analysis is accurate and supported by the source documents.
            
            Analysis:
            {analysis}
            
            Source Documents:
            {documents}
            
            Verify that all information in the analysis is directly supported by the source documents.
            Flag any information that is not supported or is an extrapolation.
            ONLY approve information that is explicitly stated in the source documents.
            """
        )
        
        self.verification_chain = LLMChain(llm=self.llm, prompt=self.verification_prompt)
    
    def verify(self, analysis: str, documents: List[Document]) -> Dict[str, Any]:
        """
        Verify the accuracy of the analysis against source documents.
        
        Args:
            analysis: Analysis results
            documents: List of retrieved documents
            
        Returns:
            Verification results
        """
        docs_text = "\n\n".join([f"Document {i+1}:\n{doc.content}" for i, doc in enumerate(documents)])
        verification = self.verification_chain.run(analysis=analysis, documents=docs_text)
        
        # Check if any unsupported information is flagged
        contains_unsupported = "not supported" in verification.lower() or "extrapolation" in verification.lower()
        
        return {
            "verified": not contains_unsupported,
            "feedback": verification
        }

class SummarizationAgent:
    """Agent responsible for creating concise summaries."""
    
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
        
        self.summarization_prompt = PromptTemplate(
            input_variables=["query", "analysis", "verification"],
            template="""
            You are a summarization agent for ServiceNow's Mother of All Decks (MOAD).
            Your task is to create a concise, useful summary of the verified information.
            
            Original Query: {query}
            
            Analysis:
            {analysis}
            
            Verification Notes:
            {verification}
            
            Create a concise summary that directly answers the query based on the verified information.
            The summary should be clear, informative, and to the point.
            ONLY include information that has been verified.
            DO NOT include any information not present in the analysis or any personal knowledge.
            """
        )
        
        self.summarization_chain = LLMChain(llm=self.llm, prompt=self.summarization_prompt)
    
    def summarize(self, query: str, analysis: str, verification: Dict[str, Any]) -> str:
        """
        Create a concise summary of the verified information.
        
        Args:
            query: The user query
            analysis: Analysis results
            verification: Verification results
            
        Returns:
            Concise summary
        """
        return self.summarization_chain.run(
            query=query,
            analysis=analysis,
            verification=verification["feedback"]
        ) 