"""
Resource handlers for the FileOps MCP server.

This module contains resource handlers for accessing files, directories,
and version control information.
"""
from typing import Tuple, Dict, Any, List, Optional
import asyncio

from mcp.server.fastmcp import FastMCP, Context

from ..utils.security import with_error_handling
from ..constants import ALL_OPERATIONS
from ..utils.git_utils import GitError

# Define standalone wrapper functions since we can't import them directly

async def standalone_read_file(path: str) -> str:
    """Wrapper function to read file contents"""
    # Create temporary FastMCP to access the registered tool
    temp_mcp = FastMCP("ResourceTemp")
    
    # Register file operations on this temporary server
    from ..operations.file_ops import register_file_operations
    register_file_operations(temp_mcp)
    
    # Find the read_file tool by name
    for name, func in temp_mcp._tools.items():
        if name.endswith("read_file"):
            return await func(path)
    
    # Fallback if tool not found
    return f"Error: Unable to find read_file tool"

async def standalone_list_directory(path: str) -> str:
    """Wrapper function to list directory contents"""
    # Create temporary FastMCP to access the registered tool
    temp_mcp = FastMCP("ResourceTemp")
    
    # Register directory operations on this temporary server
    from ..operations.dir_ops import register_directory_operations
    register_directory_operations(temp_mcp)
    
    # Find the list_dir tool by name
    for name, func in temp_mcp._tools.items():
        if name.endswith("list_dir"):
            return await func(path)
    
    # Fallback if tool not found
    return f"Error: Unable to find list_dir tool"

async def standalone_get_file_tree(path: str) -> str:
    """Wrapper function to get file tree"""
    # Create temporary FastMCP to access the registered tool
    temp_mcp = FastMCP("ResourceTemp")
    
    # Register directory operations on this temporary server
    from ..operations.dir_ops import register_directory_operations
    register_directory_operations(temp_mcp)
    
    # Find the get_tree tool by name
    for name, func in temp_mcp._tools.items():
        if name.endswith("get_tree"):
            return await func(path)
    
    # Fallback if tool not found
    return f"Error: Unable to find get_tree tool"

async def standalone_get_path_stats(path: str) -> str:
    """Wrapper function to get path stats"""
    # Create temporary FastMCP to access the registered tool
    temp_mcp = FastMCP("ResourceTemp")
    
    # Register directory operations on this temporary server
    from ..operations.dir_ops import register_directory_operations
    register_directory_operations(temp_mcp)
    
    # Find the get_stats tool by name
    for name, func in temp_mcp._tools.items():
        if name.endswith("get_stats"):
            return await func(path)
    
    # Fallback if tool not found
    return f"Error: Unable to find get_stats tool"

async def standalone_git_log(path: str, max_count: int = 10) -> str:
    """Wrapper function to get git log"""
    # Create temporary FastMCP to access the registered tool
    temp_mcp = FastMCP("ResourceTemp")
    
    # Register version operations on this temporary server
    from ..operations.version_ops import register_version_operations
    register_version_operations(temp_mcp)
    
    # Find the git_log tool by name
    for name, func in temp_mcp._tools.items():
        if name.endswith("git_log"):
            return await func(path, max_count)
    
    # Fallback if tool not found
    return f"Error: Unable to find git_log tool"

async def standalone_git_show(path: str, commit_id: str = "HEAD") -> str:
    """Wrapper function to show git version"""
    # Create temporary FastMCP to access the registered tool
    temp_mcp = FastMCP("ResourceTemp")
    
    # Register version operations on this temporary server
    from ..operations.version_ops import register_version_operations
    register_version_operations(temp_mcp)
    
    # Find the git_show tool by name
    for name, func in temp_mcp._tools.items():
        if name.endswith("git_show"):
            return await func(path, commit_id)
    
    # Fallback if tool not found
    return f"Error: Unable to find git_show tool"

async def standalone_git_status(path: str) -> str:
    """Wrapper function to get git status"""
    # Create temporary FastMCP to access the registered tool
    temp_mcp = FastMCP("ResourceTemp")
    
    # Register version operations on this temporary server
    from ..operations.version_ops import register_version_operations
    register_version_operations(temp_mcp)
    
    # Find the git_status tool by name
    for name, func in temp_mcp._tools.items():
        if name.endswith("git_status"):
            return await func(path)
    
    # Fallback if tool not found
    return f"Error: Unable to find git_status tool"

# Use help_ops functions directly since they're not wrapped in a register function
from ..operations.help_ops import get_operations_help

def register_resources(mcp: FastMCP) -> None:
    """
    Register all resource handlers with the MCP server.
    
    Args:
        mcp: The MCP server instance
    """
    # File resources
    @with_error_handling
    @mcp.resource("file://{path}")
    async def get_file_resource(path: str) -> str:
        """
        Retrieve the contents of a text file.
        
        Args:
            path: Path to the file to read
            
        Returns:
            str: File metadata and contents, or an error message
        """
        return await standalone_read_file(path)
    
    # Directory resources
    @with_error_handling
    @mcp.resource("dir://{path}")
    async def list_directory_resource(path: str) -> str:
        """
        List the contents of a directory with detailed information.
        
        Args:
            path: Path to the directory to list
            
        Returns:
            str: Formatted directory listing or error message
        """
        return await standalone_list_directory(path)
    
    @with_error_handling
    @mcp.resource("filetree://{path}")
    async def get_file_tree_resource(path: str) -> str:
        """
        Generate a visual tree representation of a directory structure.
        
        Args:
            path: Path to the root directory to visualize
            
        Returns:
            str: Formatted ASCII tree or error message
        """
        return await standalone_get_file_tree(path)
    
    @with_error_handling
    @mcp.resource("stats://{path}")
    async def get_path_stats_resource(path: str) -> str:
        """
        Get detailed statistics and metadata about a file or directory.
        
        Args:
            path: Path to the file or directory to analyze
            
        Returns:
            str: Formatted statistics or error message
        """
        return await standalone_get_path_stats(path)
    
    # Git resources
    @with_error_handling
    @mcp.resource("gitlog://{path}")
    async def get_git_log_resource(path: str) -> str:
        """
        Get the commit history for a file.
        
        Args:
            path: Path to the file
            
        Returns:
            str: Formatted commit history or error message
        """
        try:
            return await standalone_git_log(path)
        except ValueError as e:
            return f"Error: {str(e)}"
    
    @with_error_handling
    @mcp.resource("gitversion://{path}")
    async def get_git_version_resource(path: str) -> str:
        """
        Get the current version of a file (HEAD).
        
        Args:
            path: Path to the file
            
        Returns:
            str: File contents at HEAD or error message
        """
        try:
            return await standalone_git_show(path)
        except ValueError as e:
            return f"Error: {str(e)}"
    
    @with_error_handling
    @mcp.resource("gitversion://{path}?version={commit_id}")
    async def get_git_version_with_commit_resource(path: str, commit_id: str) -> str:
        """
        Get a specific version of a file by commit ID.
        
        Args:
            path: Path to the file
            commit_id: Commit ID or reference
            
        Returns:
            str: File contents at that commit or error message
        """
        try:
            return await standalone_git_show(path, commit_id)
        except ValueError as e:
            return f"Error: {str(e)}"
    
    @with_error_handling
    @mcp.resource("gitstatus://{path}")
    async def get_git_status_resource(path: str) -> str:
        """
        Get the status of a Git repository.
        
        Args:
            path: Path within the repository
            
        Returns:
            str: Formatted repository status or error message
        """
        try:
            return await standalone_git_status(path)
        except ValueError as e:
            return f"Error: {str(e)}"
    
    # Help resources
    @with_error_handling
    @mcp.resource("help://operations")
    async def get_help_resource() -> str:
        """
        Get help information about all available operations.
        
        Returns:
            str: Formatted help information
        """
        return get_operations_help()
