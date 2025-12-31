"""
RAG Client module - handles retrieval of context from VectorStore and Golden Set
"""
import os
import logging
import glob
import numpy as np
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
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            base_dir = os.path.join(project_root, "VectorStore")
            self.golden_set_dir = os.path.join(project_root, "golden_set")
        else:
            self.golden_set_dir = os.path.abspath(os.path.join(base_dir, "..", "golden_set"))
            
        self.store = FaissStore(base_dir=base_dir)
        self.embedder = Embedder()
        self.default_repos = ['3b1b_manim', '3b1b_videos']
        
        # Cache for golden set embeddings
        self.golden_set_cache = []
        self._load_golden_set()
        
    def _load_golden_set(self):
        """Loads and embeds golden set examples into memory."""
        if not os.path.exists(self.golden_set_dir):
            logger.warning(f"Golden set directory not found: {self.golden_set_dir}")
            return

        files = glob.glob(os.path.join(self.golden_set_dir, "*.py"))
        if not files:
            logger.warning("No golden set examples found.")
            return

        logger.info(f"Loading {len(files)} golden set examples...")
        
        # Simple check for simple caching (could be improved)
        texts = []
        metadatas = []
        
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                texts.append(content)
                metadatas.append({"file_path": os.path.basename(fpath), "repo": "golden_set"})
            except Exception as e:
                logger.error(f"Failed to read golden set file {fpath}: {e}")

        if texts:
            try:
                embeddings = self.embedder.embed(texts)
                for text, embedding, meta in zip(texts, embeddings, metadatas):
                    self.golden_set_cache.append({
                        "text": text,
                        "embedding": embedding,
                        "metadata": meta
                    })
                logger.info(f"Loaded {len(self.golden_set_cache)} golden set examples.")
            except Exception as e:
                logger.error(f"Failed to embed golden set: {e}")

    def _retrieve_golden_set(self, query_embedding: List[float], top_k: int = 2) -> List[Dict]:
        """Finds best matching golden set examples."""
        if not self.golden_set_cache:
            return []
            
        q_vec = np.array(query_embedding)
        norm_q = np.linalg.norm(q_vec)
        if norm_q == 0:
            return []
            
        results = []
        for item in self.golden_set_cache:
            vec = np.array(item['embedding'])
            norm_v = np.linalg.norm(vec)
            if norm_v == 0:
                score = 0
            else:
                score = np.dot(q_vec, vec) / (norm_q * norm_v)
            
            results.append({
                **item,
                "score": score,
                "source_repo": "GOLDEN_SET"
            })
            
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def retrieve_context(self, query: str, repos: Optional[List[str]] = None, top_k: int = 5) -> str:
        """
        Retrieve context for a given query from specified repositories and Golden Set.
        
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
        
        # 1. Get Golden Set Matches (High Priority)
        golden_results = self._retrieve_golden_set(query_embedding, top_k=2)
        all_results.extend(golden_results)
        
        # 2. Get Vector Store Matches
        for repo in repos:
            if not self.store._repo_exists(repo):
                # Try simple mapping if exact match fails (e.g. 3b1b_manim -> manim)
                # But for now, just log and skip
                # logger.warning(f"Repository {repo} not found in store")
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
        # Note: Golden set items might naturally have different score ranges, 
        # but usually they are high quality so we might want to ensure they appear?
        # For now, simplistic sorting is fine.
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Take top K globally across all repos (but insure at least 1 golden set if available?)
        # Let's just take top K + 1 to include more context.
        final_results = all_results[:top_k + 2] 
        
        return self._format_results(final_results)
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format retrieval results into a string for the LLM.
        """
        if not results:
            return "No relevant context found."
            
        formatted = "RELEVANT CODE EXAMPLES (Golden Set & Docs):\n"
        formatted += "=" * 40 + "\n\n"
        
        for i, res in enumerate(results):
            meta = res.get('metadata', {})
            file_path = meta.get('file_path', 'unknown')
            repo = res.get('source_repo', 'unknown')
            content = res.get('text', '')
            score = res.get('score', 0.0)
            
            # Special header for Golden Set
            if repo == "GOLDEN_SET":
                formatted += f"★ GOLDEN SET EXAMPLE ★ (Match: {score:.4f})\n"
                formatted += f"File: {file_path}\n"
            else:
                formatted += f"Example {i+1} (Source: {repo}/{file_path}, Score: {score:.4f}):\n"
                
            formatted += "-" * 20 + "\n"
            formatted += f"{content}\n"
            formatted += "-" * 20 + "\n\n"
            
        return formatted
