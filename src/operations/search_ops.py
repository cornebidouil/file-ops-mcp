"""
Search operations for FileOps MCP.

This module contains tools for searching files and file content.
"""
import os
import re
import time
import glob
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from ..constants import config, SEARCH_TIMEOUT
from ..utils.security import validate_operation, is_text_file, log_security_event, with_error_handling, sanitize_file_string, sanitize_search_text, sanitize_file_pattern
from ..utils.path_utils import filter_hidden_files, get_relative_path

def register_search_operations(mcp: FastMCP) -> None:
    """
    Register search operations with the MCP server.
    
    Args:
        mcp: The MCP server instance
    """
    @with_error_handling
    @mcp.tool()
    async def search_files(path: str = ".", pattern: str = "*", max_results: Optional[int] = None) -> str:
        """
        Search for files matching a pattern.
        
        Args:
            path: Directory to search in
            pattern: File pattern to match
            max_results: Maximum number of results to return
            
        Returns:
            str: Formatted search results
            
        Raises:
            ValueError: If search fails
        """
        abs_path = validate_operation(path, "search_files")
        
        if not os.path.isdir(abs_path):
            raise ValueError(f"{path} is not a directory")
        
        # Limit maximum results
        if max_results is None:
            max_results = config.max_results
        else:
            max_results = min(config.max_results, max(1, max_results))
        
        # Sanitize pattern for security and performance
        pattern = sanitize_file_pattern(pattern)
        
        # Perform search with timeout protection
        start_time = time.time()
        results = []
        
        try:
            # Get all files matching the pattern
            for file_path in glob.glob(os.path.join(abs_path, "**", pattern), recursive=True):
                # Skip directories and hidden files
                if os.path.isdir(file_path) or (config.hide_dot_files and os.path.basename(file_path).startswith('.')):
                    continue
                    
                # Check if we're taking too long
                if time.time() - start_time > SEARCH_TIMEOUT:
                    results.append("... (search timeout, results truncated)")
                    break
                    
                # Add the file to results
                rel_path = get_relative_path(file_path)
                results.append(rel_path)
                
                # Check if we've reached the maximum number of results
                if len(results) >= max_results:
                    results.append(f"... (limited to {max_results} results)")
                    break
            
            if not results:
                return f"No files matching '{pattern}' found in {path}"
            
            return f"Found {len(results)} files matching '{pattern}' in {path}:\n\n" + "\n".join(results)
        except Exception as e:
            raise ValueError(f"Error searching files: {str(e)}")

    @with_error_handling
    @mcp.tool()
    async def find_in_files(path: str = ".", text: str = "", file_pattern: str = "*", max_results: Optional[int] = None) -> str:
        """
        Search for text content within files.
        
        Args:
            path: Directory to search in
            text: Text to search for
            file_pattern: File pattern to match
            max_results: Maximum number of results to return
            
        Returns:
            str: Formatted search results
            
        Raises:
            ValueError: If search fails
        """
        abs_path = validate_operation(path, "find_in_files")
        
        if not os.path.isdir(abs_path):
            raise ValueError(f"{path} is not a directory")
        
        if not text:
            raise ValueError("Search text cannot be empty")
        
        # Sanitize objects as json
        text = sanitize_file_string(text)
        
        # Sanitize search text for security and performance
        text = sanitize_search_text(text)
        
        # Limit maximum results
        if max_results is None:
            max_results = config.max_results
        else:
            max_results = min(config.max_results, max(1, max_results))
        
        # Sanitize pattern for security and performance
        file_pattern = sanitize_file_pattern(file_pattern)
        
        # Perform search with timeout protection
        start_time = time.time()
        results = []
        files_searched = 0
        
        try:
            # Get all files matching the pattern
            for file_path in glob.glob(os.path.join(abs_path, "**", file_pattern), recursive=True):
                # Skip directories and hidden files
                if os.path.isdir(file_path) or (config.hide_dot_files and os.path.basename(file_path).startswith('.')):
                    continue
                    
                # Check if we're taking too long
                if time.time() - start_time > SEARCH_TIMEOUT:
                    results.append(f"... (search timeout after searching {files_searched} files, results truncated)")
                    break
                    
                # Only search text files
                if not is_text_file(file_path):
                    continue
                    
                files_searched += 1
                
                # Search for the text in the file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        line_number = 0
                        for line in f:
                            line_number += 1
                            if text in line:
                                rel_path = get_relative_path(file_path)
                                results.append(f"{rel_path}:{line_number}: {line.strip()}")
                                
                                # Check if we've reached the maximum number of results
                                if len(results) >= max_results:
                                    results.append(f"... (limited to {max_results} results)")
                                    break
                        
                        # Break the outer loop if we've reached the maximum number of results
                        if len(results) >= max_results and results[-1].startswith("... (limited to"):
                            break
                except Exception:
                    # Skip files that can't be read
                    continue
            
            if not results:
                return f"No occurrences of '{text}' found in files matching '{file_pattern}' in {path}"
            
            return f"Found {len(results) - (1 if results[-1].startswith('...') else 0)} occurrences of '{text}' in files matching '{file_pattern}' in {path} (searched {files_searched} files):\n\n" + "\n".join(results)
        except Exception as e:
            raise ValueError(f"Error searching in files: {str(e)}")

    @with_error_handling
    @mcp.tool()
    async def search_in_file(file_path: str, text: str, max_results: Optional[int] = None) -> str:
        """
        Search for text content within a specific file.
        
        Args:
            file_path: Path to the file to search in
            text: Text to search for
            max_results: Maximum number of results to return
            
        Returns:
            str: Formatted search results
            
        Raises:
            ValueError: If search fails or file doesn't exist
        """
        abs_path = validate_operation(file_path, "search_in_file", check_binary=True)
        
        if not os.path.isfile(abs_path):
            raise ValueError(f"{file_path} is not a file")
        
        if not text:
            raise ValueError("Search text cannot be empty")
        
        # Sanitize objects as json
        text = sanitize_file_string(text)
            
        # Sanitize search text for security and performance
        text = sanitize_search_text(text)
        
        # Limit maximum results
        if max_results is None:
            max_results = config.max_results
        else:
            max_results = min(config.max_results, max(1, max_results))
        
        # Only search text files
        if not is_text_file(abs_path):
            raise ValueError(f"Cannot search in binary file {file_path}. Only text files are supported.")
        
        # Get relative path for consistent display
        rel_path = get_relative_path(abs_path)
        
        # Perform search with timeout protection
        start_time = time.time()
        results = []
        
        try:
            # Search for the text in the file
            with open(abs_path, 'r', encoding='utf-8') as f:
                line_number = 0
                for line in f:
                    line_number += 1
                    
                    # Check if we're taking too long
                    if time.time() - start_time > SEARCH_TIMEOUT:
                        results.append("... (search timeout, results truncated)")
                        break
                    
                    if text in line:
                        # Use same format as find_in_files: file:line_number: content
                        results.append(f"{rel_path}:{line_number}: {line.strip()}")
                        
                        # Check if we've reached the maximum number of results
                        if len(results) >= max_results:
                            results.append(f"... (limited to {max_results} results)")
                            break
            
            if not results:
                return f"No occurrences of '{text}' found in {file_path}"
            
            return f"Found {len(results) - (1 if results[-1].startswith('...') else 0)} occurrences of '{text}' in {file_path}:\n\n" + "\n".join(results)
        except Exception as e:
            raise ValueError(f"Error searching in file: {str(e)}")
