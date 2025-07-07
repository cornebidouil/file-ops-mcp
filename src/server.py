"""
Main server module for FileOps MCP.

This module provides the core server functionality and integrates all components.
"""
import os
import sys
import signal
import time
from typing import Dict, Any, List, Optional, Union, Callable
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

from .constants import config
from .utils.security import log_security_event

# Define lifespan manager
@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """
    Manage the server lifecycle.
    
    Args:
        server: The MCP server instance
        
    Yields:
        Dict[str, Any]: Server context
    """
    # Initialize resources
    print(f"Starting FileOps MCP server with working directory: {config.abs_working_dir}", file=sys.stderr)
    
    # Setup context
    context = {
        "start_time": time.time(),
    }
    
    try:
        yield context
    finally:
        # Cleanup
        run_time = time.time() - context["start_time"]
        print(f"FileOps MCP server shutting down after {run_time:.2f} seconds", file=sys.stderr)

# Create MCP server with lifespan
mcp = FastMCP("FileOps", lifespan=server_lifespan)

# Set up signal handlers for clean shutdown
def signal_handler(sig, frame):
    """Handle signals for clean shutdown."""
    print("Shutting down gracefully...", file=sys.stderr)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def initialize_server(
    working_dir: str,
    read_only: bool = False,
    hide_dot_files: bool = True,
    max_depth: int = 5,
    max_results: int = 100,
    git_enabled: bool = True,
    git_auto_commit: bool = True,
    git_username: str = "FileOps MCP",
    git_email: str = "fileops-mcp@no-reply.local",
) -> None:
    """
    Initialize the FileOps MCP server with the specified configuration.
    
    Args:
        working_dir: Working directory for all operations
        read_only: Whether to run in read-only mode
        hide_dot_files: Whether to hide files and directories starting with .
        max_depth: Maximum depth for directory tree traversal
        max_results: Maximum number of results for searches
        git_enabled: Whether to enable Git functionality
        git_auto_commit: Whether to automatically commit changes
        git_username: Username for Git commits
        git_email: Email for Git commits
    """
    # Set global configuration
    config.abs_working_dir = os.path.abspath(working_dir)
    config.read_only = read_only
    config.hide_dot_files = hide_dot_files
    config.max_depth = max(1, min(10, max_depth))  # Limit between 1 and 10
    config.max_results = max(1, min(1000, max_results))  # Limit between 1 and 1000
    config.git_enabled = git_enabled
    config.git_auto_commit = git_auto_commit
    config.git_username = git_username
    config.git_email = git_email
    
    # Log initialization
    print(f"FileOps MCP Server initialized with:", file=sys.stderr)
    print(f"  Working directory: {config.abs_working_dir}", file=sys.stderr)
    print(f"  Read-only mode: {config.read_only}", file=sys.stderr)
    print(f"  Hide dot files: {config.hide_dot_files}", file=sys.stderr)
    print(f"  Max depth: {config.max_depth}", file=sys.stderr)
    print(f"  Max results: {config.max_results}", file=sys.stderr)
    print(f"  Git enabled: {config.git_enabled}", file=sys.stderr)
    print(f"  Git auto-commit: {config.git_auto_commit}", file=sys.stderr)
    
    # Register tools and resources
    register_all_components()

def register_all_components():
    """Register all tools and resources with the MCP server."""
    # Import and register components
    from .resources.resource_handlers import register_resources
    from .operations.file_ops import register_file_operations
    from .operations.dir_ops import register_directory_operations
    from .operations.search_ops import register_search_operations
    from .operations.version_ops import register_version_operations
    from .operations.help_ops import register_help_operations
    from .operations.doc_ops import register_doc_operations
    
    # Register resources
    register_resources(mcp)
    
    # Register tool operations
    register_file_operations(mcp)
    register_directory_operations(mcp)
    register_search_operations(mcp)
    register_version_operations(mcp)
    register_help_operations(mcp)
    register_doc_operations(mcp)
