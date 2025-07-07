"""
Documentation operations for FileOps MCP.

This module contains tools for providing documentation and guidance.
"""
import os
from mcp.server.fastmcp import FastMCP

from ..utils.security import with_error_handling
from ..constants import config


def register_doc_operations(mcp: FastMCP) -> None:
    """
    Register documentation operations with the MCP server.
    
    Args:
        mcp: The MCP server instance
    """
    
    @with_error_handling
    @mcp.tool()
    async def get_fileops_commandments() -> str:
        """
        Get the FileOps Sixteen Commandments for MCP tool usage.
        
        Returns the complete content of the FileOps-MCP-16-Commandments.md file
        which contains essential guidelines for using MCP tools effectively.
        
        Returns:
            str: The complete content of the FileOps commandments document
        """
        # Get the path to the commandments file
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs")
        commandments_path = os.path.join(docs_dir, "FileOps-MCP-16-Commandments.md")
        
        try:
            with open(commandments_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"""FileOps MCP - Sixteen Commandments

{content}

---
Note: These commandments provide essential guidelines for effective MCP tool usage.
Follow them to ensure proper file operations and maintain code quality.
"""
        except FileNotFoundError:
            return f"Error: FileOps commandments file not found at: {commandments_path}"
        except Exception as e:
            return f"Error reading FileOps commandments: {str(e)}"
