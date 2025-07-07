"""
Constants and configuration settings for FileOps MCP.
"""
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class FileOpsConfig:
    """Configuration class for FileOps MCP server."""
    
    # File system settings
    abs_working_dir: str = ""
    read_only: bool = False
    hide_dot_files: bool = True
    max_depth: int = 5
    max_results: int = 100
    
    # Git settings
    git_enabled: bool = True
    git_auto_commit: bool = True
    git_username: str = "FileOps MCP"
    git_email: str = "fileops-mcp@no-reply.local"
    git_commit_template: str = "[{operation}] {path}"

    def __post_init__(self):
        """Validate and adjust configuration values."""
        # Ensure max_depth is between 1 and 10
        self.max_depth = max(1, min(10, self.max_depth))
        
        # Ensure max_results is between 1 and 1000
        self.max_results = max(1, min(1000, self.max_results))
        
        # Ensure working directory is absolute
        if self.abs_working_dir:
            self.abs_working_dir = os.path.abspath(self.abs_working_dir)

# Default configuration instance
config = FileOpsConfig()

# File operation types for logging and monitoring
FILE_OPERATIONS = [
    "read_file", "read_multiple_files", "read_image", "create_file", "update_file", "rewrite_file",
    "delete_file", "remove_from_file", "append_to_file", "insert_in_file",
    "copy_file", "copy_multiple_files", "move_file", "move_multiple_files", "file_exists", 
    "delete_multiple_files", "replace_all_in_file"
]

# Directory operation types for logging and monitoring
DIR_OPERATIONS = [
    "list_dir", "get_tree", "create_dir", "delete_dir", 
    "get_stats"
]

# Search operation types for logging and monitoring
SEARCH_OPERATIONS = [
    "search_files", "find_in_files", "search_in_file"
]

# Git operation types for logging and monitoring
GIT_OPERATIONS = [
    "git_init", "git_commit", "git_log", "git_show",
    "git_diff", "git_revert", "git_status",
    "git_branch_list", "git_branch_create", "git_branch_switch"
]

# Documentation operation types for logging and monitoring
DOC_OPERATIONS = [
    "get_fileops_commandments"
]

# All valid operations
ALL_OPERATIONS = FILE_OPERATIONS + DIR_OPERATIONS + SEARCH_OPERATIONS + GIT_OPERATIONS + DOC_OPERATIONS + ["help"]

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Operation timeout in seconds
OPERATION_TIMEOUT = 30

# Search timeout in seconds
SEARCH_TIMEOUT = 20

# Default transports
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
