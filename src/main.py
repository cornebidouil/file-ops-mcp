#!/usr/bin/env -S uv run --script
# -*- coding: utf-8 -*-
# /// script
# dependencies = ["mcp>=1.2.0", "gitpython>=3.1.30", "pillow>=10.0.0",]
# requires-python = ">=3.10"
# ///
"""
Main entry point for FileOps MCP Server.
"""
import os
import sys
import signal
import argparse
from pathlib import Path
import json

# Add the src directory to the path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import server module
from src.server import mcp, initialize_server

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="FileOps MCP Server - File operations with versioning")
    
    # Basic configuration
    parser.add_argument(
        "--working-dir", 
        help="Working directory for all operations", 
        default="."
    )
    parser.add_argument(
        "--read-only", 
        action="store_true", 
        help="Run in read-only mode"
    )
    
    # File visibility
    visibility_group = parser.add_mutually_exclusive_group()
    visibility_group.add_argument(
        "--hide-dot-files", 
        action="store_true", 
        help="Hide files and directories starting with .", 
        default=True
    )
    visibility_group.add_argument(
        "--show-dot-files", 
        action="store_true", 
        help="Show files and directories starting with .", 
        default=False
    )
    
    # Limits
    parser.add_argument(
        "--max-depth", 
        type=int, 
        help="Maximum depth for directory tree traversal", 
        default=5
    )
    parser.add_argument(
        "--max-results", 
        type=int, 
        help="Maximum number of results for searches", 
        default=100
    )
    
    # Git configuration
    parser.add_argument(
        "--disable-git", 
        action="store_true", 
        help="Disable Git functionality"
    )
    parser.add_argument(
        "--disable-auto-commit", 
        action="store_true", 
        help="Disable automatic commit of changes"
    )
    parser.add_argument(
        "--git-username", 
        help="Username for Git commits", 
        default="FileOps MCP"
    )
    parser.add_argument(
        "--git-email", 
        help="Email for Git commits", 
        default="fileops-mcp@no-reply.local"
    )
    
    # Transport
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse"], 
        default="stdio", 
        help="Transport to use (stdio or sse)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port for SSE transport (default: 8000)"
    )
    parser.add_argument(
        "--host", 
        default="localhost", 
        help="Host for SSE transport (default: localhost)"
    )
    
    # Configuration file
    parser.add_argument(
        "--config", 
        help="Path to JSON configuration file"
    )
    
    return parser.parse_args()

def load_config_file(config_path):
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading configuration file: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Run the FileOps MCP server with command-line arguments."""
    args = parse_args()
    
    # Load configuration from file if specified
    config_from_file = {}
    if args.config:
        config_from_file = load_config_file(args.config)
    
    # Get the configuration values, prioritizing command-line arguments
    working_dir = args.working_dir if args.working_dir != "." or not config_from_file.get("working_dir") else config_from_file.get("working_dir")
    read_only = args.read_only or config_from_file.get("read_only", False)
    hide_dot_files = args.hide_dot_files and not args.show_dot_files if args.hide_dot_files or args.show_dot_files else config_from_file.get("hide_dot_files", True)
    max_depth = args.max_depth if args.max_depth != 5 or not config_from_file.get("max_depth") else config_from_file.get("max_depth")
    max_results = args.max_results if args.max_results != 100 or not config_from_file.get("max_results") else config_from_file.get("max_results")
    git_enabled = not args.disable_git if not args.disable_git or not config_from_file.get("git_enabled") else config_from_file.get("git_enabled")
    git_auto_commit = not args.disable_auto_commit if not args.disable_auto_commit or not config_from_file.get("git_auto_commit") else config_from_file.get("git_auto_commit")
    git_username = args.git_username if args.git_username != "FileOps MCP" or not config_from_file.get("git_username") else config_from_file.get("git_username")
    git_email = args.git_email if args.git_email != "fileops-mcp@no-reply.local" or not config_from_file.get("git_email") else config_from_file.get("git_email")
    
    # Check if Git support is available
    if git_enabled:
        try:
            import git
            print("Git support is enabled", file=sys.stderr)
        except ImportError:
            print("Warning: gitpython module not found. Git functionality will be disabled.", file=sys.stderr)
            git_enabled = False
    
    # Validate working directory
    working_dir = os.path.abspath(working_dir)
    if not os.path.exists(working_dir):
        print(f"Error: Working directory does not exist: {working_dir}", file=sys.stderr)
        return 1
    if not os.path.isdir(working_dir):
        print(f"Error: Working directory is not a directory: {working_dir}", file=sys.stderr)
        return 1
    
    # Initialize the server
    try:
        initialize_server(
            working_dir=working_dir,
            read_only=read_only,
            hide_dot_files=hide_dot_files,
            max_depth=max_depth,
            max_results=max_results,
            git_enabled=git_enabled,
            git_auto_commit=git_auto_commit,
            git_username=git_username,
            git_email=git_email,
        )
    except Exception as e:
        print(f"Error initializing server: {e}", file=sys.stderr)
        raise e
        #return 1
    
    # Run the server with the specified transport
    transport = args.transport if args.transport != "stdio" or not config_from_file.get("transport") else config_from_file.get("transport")
    host = args.host if args.host != "localhost" or not config_from_file.get("host") else config_from_file.get("host")
    port = args.port if args.port != 8000 or not config_from_file.get("port") else config_from_file.get("port")
    
    if transport == "stdio":
        print("Starting server with stdio transport", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        print(f"Starting server with SSE transport on {host}:{port}", file=sys.stderr)
        mcp.run(transport="sse", host=host, port=port)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
