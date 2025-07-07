"""
Help operations for FileOps MCP.

This module contains tools for providing help and documentation.
"""
from typing import Optional
from mcp.server.fastmcp import FastMCP

from ..utils.security import with_error_handling
from .help_texts import HELP_TEXTS
from ..constants import ALL_OPERATIONS

def register_help_operations(mcp: FastMCP) -> None:
    """
    Register help operations with the MCP server.
    
    Args:
        mcp: The MCP server instance
    """
    @with_error_handling
    @mcp.tool()
    async def help(topic: str = "operations") -> str:
        """
        Get help information about available operations.
        
        Args:
            topic: Topic to get help on (default: "operations")
            
        Returns:
            str: Formatted help information
        """
        if not topic or topic == "operations":
            return get_operations_help()
        elif topic in ALL_OPERATIONS:
            return HELP_TEXTS.get(topic, f"No help available for operation: {topic}")
        else:
            return f"Unknown help topic: {topic}. Valid topics are: operations, " + ", ".join(ALL_OPERATIONS)

def get_operations_help() -> str:
    """
    Get help information about all available operations.
    
    Returns:
        str: Formatted help information
    """
    return """
FileOps Tool - Available Operations:

File Operations:
- read_file: Read the contents of a text file
- read_multiple_files: Read the contents of multiple text files
- read_image: Read and return an image file as a Pillow Image object
- create_file: Create a new text file with the specified content
- update_file: Update specific text within a file by replacing matching content
- rewrite_file: Replace the entire content of a file
- delete_file: Delete a file
- remove_from_file: Remove specific text from a file
- append_to_file: Append content to the end of a file
- insert_in_file: Insert content at a specific position in a file
- copy_file: Copy a file from source path to destination path
- copy_multiple_files: Copy multiple files from source paths to destination paths or directory
- move_file: Move (rename) a file from source path to destination path
- move_multiple_files: Move multiple files from source paths to destination paths or directory
- file_exists: Check if a file exists at the specified path
- delete_multiple_files: Delete multiple files from the specified paths
- replace_all_in_file: Replace ALL occurrences of specific text within a file

Directory Operations:
- list_dir: List the contents of a directory with detailed information
- get_tree: Get a tree view of a directory
- create_dir: Create a new directory
- delete_dir: Delete a directory
- get_stats: Get detailed information about a file or directory

Search Operations:
- search_files: Search for files matching a pattern
- find_in_files: Search for text content within files
- search_in_file: Search for text content within a specific file

Version Control Operations:
- git_init: Initialize a Git repository
- git_commit: Commit changes to a file or directory
- git_log: Show commit history for a file
- git_show: Show file content at a specific commit
- git_diff: Show differences between two commits
- git_revert: Revert a file to a previous version
- git_status: Show Git repository status
- git_branch_list: List all branches in the repository
- git_branch_create: Create a new branch
- git_branch_switch: Switch to a different branch

Documentation Operations:
- get_fileops_commandments: Get the FileOps Sixteen Commandments for MCP tool usage

Help:
- help: Get help information about available operations

For detailed help on a specific operation, use the operation name as the topic:
help(topic="operation_name")
"""
