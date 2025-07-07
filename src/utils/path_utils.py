"""
Path utilities for FileOps MCP.

This module contains functions for working with file paths,
including path validation, normalization, and metadata extraction.
"""
import os
import hashlib
import datetime
import mimetypes
import stat
from typing import Dict, Any, Optional, List, Union

from ..constants import config

def generate_checksum(path: str) -> str:
    """
    Generate SHA-256 checksum for a file.
    
    Args:
        path: Path to the file
        
    Returns:
        str: SHA-256 checksum as a hexadecimal string
        
    Raises:
        ValueError: If checksum generation fails
    """
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        raise ValueError(f"Failed to generate checksum: {str(e)}")

def get_file_info(path: str) -> Dict[str, Any]:
    """
    Get detailed information about a file.
    
    Args:
        path: Path to the file
        
    Returns:
        Dict[str, Any]: Dictionary containing file information
    """
    stats = {}
    
    try:
        abs_path = os.path.abspath(path)
        
        # Basic file information
        stat_info = os.stat(abs_path)
        mime_type, _ = mimetypes.guess_type(abs_path)
        
        stats["path"] = path
        stats["type"] = "file"
        stats["size"] = stat_info.st_size
        stats["mime_type"] = mime_type or "application/octet-stream"
        stats["created"] = datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat()
        stats["modified"] = datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat()
        stats["accessed"] = datetime.datetime.fromtimestamp(stat_info.st_atime).isoformat()
        
        # Permission information
        mode = stat_info.st_mode
        perms = ""
        for who in "USR", "GRP", "OTH":
            for what in "R", "W", "X":
                perm = getattr(stat, f"S_I{what}{who}")
                perms += what.lower() if mode & perm else "-"
        stats["permissions"] = perms
        
        # Checksum for files
        if os.path.isfile(abs_path):
            stats["checksum"] = generate_checksum(abs_path)
            
            # Count lines for text files
            if mime_type and (mime_type.startswith('text/') or mime_type in ('application/json', 'application/xml', 'application/javascript')):
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        stats["line_count"] = sum(1 for _ in f)
                except UnicodeDecodeError:
                    stats["line_count"] = None
    except Exception as e:
        stats["error"] = str(e)
    
    return stats

def get_dir_info(path: str, include_contents: bool = True) -> Dict[str, Any]:
    """
    Get detailed information about a directory.
    
    Args:
        path: Path to the directory
        include_contents: Whether to include contents information
        
    Returns:
        Dict[str, Any]: Dictionary containing directory information
    """
    stats = {}
    
    try:
        abs_path = os.path.abspath(path)
        
        # Basic directory information
        stat_info = os.stat(abs_path)
        
        stats["path"] = path
        stats["type"] = "directory"
        stats["created"] = datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat()
        stats["modified"] = datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat()
        stats["accessed"] = datetime.datetime.fromtimestamp(stat_info.st_atime).isoformat()
        
        # Permission information
        mode = stat_info.st_mode
        perms = ""
        for who in "USR", "GRP", "OTH":
            for what in "R", "W", "X":
                perm = getattr(stat, f"S_I{what}{who}")
                perms += what.lower() if mode & perm else "-"
        stats["permissions"] = perms
        
        # Content counts
        if include_contents:
            try:
                entries = os.listdir(abs_path)
                dirs = sum(1 for e in entries if os.path.isdir(os.path.join(abs_path, e)))
                files = sum(1 for e in entries if os.path.isfile(os.path.join(abs_path, e)))
                
                stats["entry_count"] = len(entries)
                stats["dir_count"] = dirs
                stats["file_count"] = files
            except Exception as e:
                stats["error"] = str(e)
    except Exception as e:
        stats["error"] = str(e)
    
    return stats

def filter_hidden_files(entries: List[str]) -> List[str]:
    """
    Filter out hidden files and directories if configured to do so.
    
    Args:
        entries: List of file or directory names
        
    Returns:
        List[str]: Filtered list of entries
    """
    if config.hide_dot_files:
        return [entry for entry in entries if not entry.startswith('.')]
    return entries

def get_relative_path(path: str) -> str:
    """
    Get path relative to the working directory.
    
    Args:
        path: Absolute path
        
    Returns:
        str: Path relative to working directory
    """
    if not path.startswith(config.abs_working_dir):
        return path  # Not within working directory
    
    rel_path = os.path.relpath(path, config.abs_working_dir)
    if rel_path == ".":
        return ""
    return rel_path
