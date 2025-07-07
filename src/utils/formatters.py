"""
Formatting utilities for FileOps MCP.

This module contains functions for formatting output in various formats,
such as directory trees, file listings, and Git diffs.
"""
import os
import time
import json
from typing import Dict, Any, List, Optional

from ..constants import config

def format_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/(1024*1024):.1f} MB"

def get_directory_tree(path: str, max_depth: int = 5, current_depth: int = 0) -> Dict[str, Any]:
    """
    Generate a nested dictionary representing a directory tree.
    
    Args:
        path: Path to the directory
        max_depth: Maximum depth to traverse
        current_depth: Current depth of traversal
        
    Returns:
        Dict[str, Any]: Directory tree as a nested dictionary
    """
    if current_depth > max_depth:
        return {"truncated": True}
    
    if not os.path.isdir(path):
        return None
    
    name = os.path.basename(path)
    
    result = {"name": name, "type": "directory", "children": []}
    
    try:
        entries = sorted(os.listdir(path))
        for entry in entries:
            if config.hide_dot_files and entry.startswith('.'):
                continue
                
            entry_path = os.path.join(path, entry)
            if os.path.isdir(entry_path):
                child = get_directory_tree(entry_path, max_depth, current_depth + 1)
                if child:
                    result["children"].append(child)
            elif os.path.isfile(entry_path):
                result["children"].append({"name": entry, "type": "file"})
    except PermissionError:
        result["error"] = "Permission denied"
    except OSError as e:
        result["error"] = str(e)
    
    return result

def format_tree_for_display(tree: Dict[str, Any], indent: str = "", is_last: bool = True) -> str:
    """
    Format a directory tree dictionary as a string for display.
    
    Args:
        tree: Directory tree dictionary
        indent: Current indentation
        is_last: Whether this is the last item in its level
        
    Returns:
        str: Formatted tree string
    """
    if not tree:
        return ""
    
    if tree.get("truncated"):
        marker = "└── " if is_last else "├── "
        return f"{indent}{marker}...\n"
    
    marker = "└── " if is_last else "├── "
    result = f"{indent}{marker}{tree['name']}\n"
    
    if tree.get("error"):
        result += f"{indent}    └── Error: {tree['error']}\n"
        return result
    
    if tree.get("type") == "file":
        return result
    
    children = tree.get("children", [])
    if not children:
        return result
    
    new_indent = indent + ("    " if is_last else "│   ")
    
    for i, child in enumerate(children):
        is_last_child = i == len(children) - 1
        result += format_tree_for_display(child, new_indent, is_last_child)
    
    return result

def format_file_contents(path: str, content: str, include_metadata: bool = True) -> str:
    """
    Format file contents with optional metadata.
    
    Args:
        path: Path to the file
        content: File content
        include_metadata: Whether to include file metadata
        
    Returns:
        str: Formatted file content
    """
    if not include_metadata:
        return content
    
    try:
        file_size = os.path.getsize(path)
        checksum = None
        try:
            import hashlib
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    h.update(chunk)
            checksum = h.hexdigest()
        except Exception:
            pass
        
        metadata = f"File: {path}\nSize: {file_size} bytes"
        if checksum:
            metadata += f"\nChecksum (SHA-256): {checksum}"
        
        return f"{metadata}\n\nContent:\n\n{content}"
    except Exception as e:
        return f"Error retrieving file metadata: {str(e)}\n\nContent:\n\n{content}"

def format_directory_listing(path: str, entries: List[str]) -> str:
    """
    Format directory listing with file details.
    
    Args:
        path: Path to the directory
        entries: List of directory entries
        
    Returns:
        str: Formatted directory listing
    """
    import mimetypes
    
    result = f"Directory: {path}\n\n"
    
    dirs = []
    files = []
    
    # Process entries with timeout protection
    start_time = time.time()
    entry_count = 0
    
    for entry in sorted(entries):
        # Check timeout periodically
        entry_count += 1
        if entry_count % 100 == 0 and time.time() - start_time > 10:  # 10 second timeout
            result += "... (listing truncated due to timeout)\n"
            break
            
        if config.hide_dot_files and entry.startswith('.'):
            continue
            
        full_path = os.path.join(path, entry)
        try:
            # Use os.path.isdir with error handling for path access issues
            if os.path.isdir(full_path):
                dirs.append((entry, full_path))
            else:
                files.append((entry, full_path))
        except (PermissionError, OSError):
            # If we can't determine type, treat as a file with access issues
            files.append((entry, full_path, "access_error"))
    
    if dirs:
        result += "Directories:\n"
        for name, full_path in dirs:
            result += f"📁 {name}/\n"
        result += "\n"
        
    if files:
        result += "Files:\n"
        for file_info in files:
            if len(file_info) == 3:  # This is a file with access error
                name, _, _ = file_info
                result += f"📄 {name} (access error)\n"
                continue
                
            name, full_path = file_info
            try:
                size = os.path.getsize(full_path)
                size_str = format_size(size)
                
                # Use a try/except specifically for mime type to handle that error separately
                try:
                    mime_type, _ = mimetypes.guess_type(full_path)
                    mime_str = mime_type or 'application/octet-stream'
                except Exception:
                    mime_str = 'unknown/type'
                    
                result += f"📄 {name} ({size_str}, {mime_str})\n"
            except PermissionError:
                result += f"📄 {name} (permission denied)\n"
            except OSError as e:
                result += f"📄 {name} (error: {str(e)})\n"
            except Exception as e:
                result += f"📄 {name} (unexpected error)\n"
    
    if not dirs and not files:
        result += "Directory is empty."
        
    return result

def format_git_log(log_entries: List[Dict[str, Any]]) -> str:
    """
    Format Git log entries for display.
    
    Args:
        log_entries: List of Git log entry dictionaries
        
    Returns:
        str: Formatted Git log
    """
    if not log_entries:
        return "No commit history available."
    
    result = "Commit History:\n\n"
    
    for entry in log_entries:
        result += f"Commit: {entry['commit']}\n"
        result += f"Author: {entry['author']}\n"
        result += f"Date: {entry['date']}\n"
        result += f"Message: {entry['message']}\n"
        if 'changes' in entry and entry['changes']:
            result += "Changes:\n"
            for change in entry['changes']:
                result += f"  {change}\n"
        result += "\n"
    
    return result

def format_git_diff(diff_content: str) -> str:
    """
    Format Git diff output for display.
    
    Args:
        diff_content: Raw diff content
        
    Returns:
        str: Formatted diff
    """
    # Simple formatting for now - could be enhanced with syntax highlighting
    if not diff_content:
        return "No differences found."
    
    return "Diff:\n\n" + diff_content
