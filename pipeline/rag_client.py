"""
RAG Client module - handles retrieval of context from VectorStore
"""
import os
import logging
from typing import List, Dict, Optional, Any
from store import FaissStore
from embedding import Embedder
import config

logger = logging.getLogger(__name__)

class RAGClient:
    """
    Client for retrieving relevant code and videos from the VectorStore.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the RAG client.
        
        Args:
            base_dir: Optional base directory for VectorStore
        """
        if base_dir is None:
            # Default to VectorStore in the project root
            # Assuming this file is in pipeline/rag_client.py
            # and VectorStore is in MathVizAI/VectorStore
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            base_dir = os.path.join(project_root, "VectorStore")
            
        self.store = FaissStore(base_dir=base_dir)
        self.embedder = Embedder()
        self.default_repos = ['3b1b_manim', '3b1b_videos']
        
    def retrieve_context(self, query: str, repos: Optional[List[str]] = None, top_k: int = 5) -> str:
        """
        Retrieve context for a given query from specified repositories.
        
        Args:
            query: Natural language query
            repos: List of repository names to search (defaults to configured repos)
            top_k: Number of results to retrieve per repository
            
        Returns:
            Formatted string containing retrieved context
        """
        if repos is None:
            repos = self.default_repos
            
        print(f"  🔍 Retrieving context for: '{query}'")
        
        # Generate embedding for the query
        try:
            query_embedding = self.embedder.embed(query)[0]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return f"Error retrieving context: {str(e)}"
            
        all_results = []
        
        for repo in repos:
            if not self.store._repo_exists(repo):
                # Try simple mapping if exact match fails (e.g. 3b1b_manim -> manim)
                # But for now, just log and skip
                logger.warning(f"Repository {repo} not found in store")
                continue
                
            try:
                results = self.store.search_repo(
                    repo_name=repo,
                    query_embedding=query_embedding,
                    top_k=top_k
                )
                
                for res in results:
                    res['source_repo'] = repo
                    all_results.append(res)
                    
            except Exception as e:
                logger.error(f"Error searching repo {repo}: {e}")
                
        # Sort combined results by score (descending)
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Take top K globally across all repos
        final_results = all_results[:top_k]
        
        return self._format_results(final_results)
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format retrieval results into a string for the LLM.
        """
        if not results:
            return "No relevant context found."
            
        formatted = "RELEVANT CODE EXAMPLES FROM REPOSITORY:\n"
        formatted += "=" * 40 + "\n\n"
        
        for i, res in enumerate(results):
            meta = res.get('metadata', {})
            file_path = meta.get('file_path', 'unknown')
            repo = res.get('source_repo', 'unknown')
            content = res.get('text', '')
            score = res.get('score', 0.0)
            
            formatted += f"Example {i+1} (Source: {repo}/{file_path}, Score: {score:.4f}):\n"
            formatted += "-" * 20 + "\n"
            formatted += f"{content}\n"
            formatted += "-" * 20 + "\n\n"
            
        return formatted
