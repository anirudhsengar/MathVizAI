"""
File management utilities for MathVizAI
"""
import os
import json
from datetime import datetime
from typing import Dict, Any
import config


class FileManager:
    """Handles file operations and output directory management"""
    
    def __init__(self, query: str):
        """
        Initialize file manager for a specific query
        
        Args:
            query: The mathematical query (used for folder naming)
        """
        self.query = query
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create sanitized folder name from query
        sanitized_query = self._sanitize_filename(query[:50])
        self.session_folder = os.path.join(
            config.OUTPUT_DIR, 
            f"{self.timestamp}_{sanitized_query}"
        )
        
        # Create output directory structure
        self._create_directories()
    
    def _sanitize_filename(self, text: str) -> str:
        """Remove invalid characters from filename"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, '_')
        return text.strip()
    
    def _create_directories(self):
        """Create necessary directories for this session"""
        os.makedirs(self.session_folder, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['solver', 'evaluator', 'script', 'video', 'audio', 'final']
        for subdir in subdirs:
            os.makedirs(os.path.join(self.session_folder, subdir), exist_ok=True)
    
    def save_text(self, content: str, filename: str, subfolder: str = '') -> str:
        """
        Save text content to file
        
        Args:
            content: Text content to save
            filename: Name of the file
            subfolder: Subfolder within session folder
        
        Returns:
            Full path to saved file
        """
        if subfolder:
            filepath = os.path.join(self.session_folder, subfolder, filename)
        else:
            filepath = os.path.join(self.session_folder, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def save_json(self, data: Dict[Any, Any], filename: str, subfolder: str = '') -> str:
        """
        Save JSON data to file
        
        Args:
            data: Dictionary to save as JSON
            filename: Name of the file
            subfolder: Subfolder within session folder
        
        Returns:
            Full path to saved file
        """
        if subfolder:
            filepath = os.path.join(self.session_folder, subfolder, filename)
        else:
            filepath = os.path.join(self.session_folder, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def get_path(self, filename: str, subfolder: str = '') -> str:
        """Get full path for a file"""
        if subfolder:
            return os.path.join(self.session_folder, subfolder, filename)
        return os.path.join(self.session_folder, filename)
    
    def save_metadata(self, metadata: Dict[Any, Any]):
        """Save session metadata"""
        self.save_json(metadata, 'metadata.json')
