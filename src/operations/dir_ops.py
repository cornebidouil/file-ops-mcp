"""
Directory operations for FileOps MCP.

This module contains tools for directory operations such as listing contents,
creating and deleting directories, and getting directory trees.
"""
import os
import time
import shutil
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from ..constants import config
from ..utils.security import validate_operation, log_security_event, with_error_handling
from ..utils.path_utils import get_dir_info, filter_hidden_files
from ..utils.formatters import get_directory_tree, format_tree_for_display, format_directory_listing
from ..utils.git_utils import auto_commit_changes, GitError

def register_directory_operations(mcp: FastMCP) -> None:
    """
    Register directory operations with the MCP server.
    
    Args:
        mcp: The MCP server instance
    """
    @with_error_handling
    @mcp.tool()
    async def list_dir(path: str = ".") -> str:
        """
        List the contents of a directory with detailed information.
        
        Args:
            path: Path to the directory
            
        Returns:
            str: Formatted directory listing
            
        Raises:
            ValueError: If directory listing fails
        """
        abs_path = validate_operation(path, "list_dir")
        
        if not os.path.isdir(abs_path):
            raise ValueError(f"{path} is not a directory")
        
        try:
            entries = os.listdir(abs_path)
            return format_directory_listing(abs_path, entries)
        except PermissionError:
            raise ValueError(f"Permission denied for directory: {abs_path}")
        except OSError as e:
            raise ValueError(f"Error listing directory: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error listing directory: {str(e)}")

    @with_error_handling
    @mcp.tool()
    async def get_tree(path: str = ".") -> str:
        """
        Generate a visual tree representation of a directory structure.
        
        Args:
            path: Path to the directory
                
        Returns:
            str: Formatted directory tree
                
        Raises:
            ValueError: If tree generation fails
        """
        try:
            abs_path = validate_operation(path, "get_tree")
            
            if not os.path.isdir(abs_path):
                raise ValueError(f"{path} is not a directory")
            
            # Generate tree with depth limit from config
            try:
                tree = get_directory_tree(abs_path, max_depth=config.max_depth)
                
                if not tree:
                    return f"Error generating tree for {path}: No tree data returned"
                
                try:
                    formatted_tree = format_tree_for_display(tree)
                    return f"File tree for {path}:\n\n```\n{formatted_tree}```"
                except KeyError as ke:
                    # Handle specific KeyError issues in the tree formatting
                    return f"Error formatting directory tree: Missing key '{ke}' in tree data structure. This may be caused by reaching the maximum depth limit ({config.max_depth})."
                except Exception as format_err:
                    return f"Error formatting directory tree: {str(format_err)}. Tree data may be incomplete or malformed."
                    
            except Exception as tree_err:
                return f"Error generating directory tree structure: {str(tree_err)}"
                
        except Exception as e:
            # This is the outermost error handler
            error_details = f"Path: {path}"
            if 'abs_path' in locals():
                error_details += f", Absolute path: {abs_path}"
                error_details += f", Base name: {os.path.basename(abs_path)}"
            
            raise ValueError(f"Failed to generate directory tree: {str(e)}. {error_details}")

    @with_error_handling
    @mcp.tool()
    async def create_dir(path: str, commit_message: str = None) -> str:
        """
        Create a new directory.
        
        Args:
            path: Where to create the directory
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If directory creation fails
        """
        abs_path = validate_operation(path, "create_dir")
        
        if os.path.exists(abs_path):
            if os.path.isdir(abs_path):
                return f"Directory already exists at {path}"
            else:
                raise ValueError(f"A file already exists at {path}")
        
        try:
            os.makedirs(abs_path)
        except Exception as e:
            raise ValueError(f"Failed to create directory: {str(e)}")
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "create_dir", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully created directory: {path}{commit_result}"

    @with_error_handling
    @mcp.tool()
    async def delete_dir(path: str, recursive: bool = False, commit_message: str = None) -> str:
        """
        Delete a directory, recursively or not.
        
        Args:
            path: Path to the directory
            recursive: Whether to delete non-empty directories
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If directory deletion fails
        """
        abs_path = validate_operation(path, "delete_dir")
        
        if not os.path.exists(abs_path):
            raise ValueError(f"Directory does not exist at {path}")
        
        if not os.path.isdir(abs_path):
            raise ValueError(f"{path} is a file, not a directory")
        
        if not recursive and os.listdir(abs_path):
            raise ValueError(f"Directory {path} is not empty. Use recursive=True to delete anyway.")
        
        try:
            parent_dir = os.path.dirname(abs_path)
            
            if recursive:
                shutil.rmtree(abs_path)
            else:
                os.rmdir(abs_path)
        except Exception as e:
            raise ValueError(f"Failed to delete directory: {str(e)}")
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            # Commit from parent directory since the target directory is now gone
            commit = auto_commit_changes(parent_dir, "delete_dir", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully deleted directory: {path}{commit_result}"

    @with_error_handling
    @mcp.tool()
    async def get_stats(path: str) -> str:
        """
        Get detailed statistics and metadata about a file or directory.
        
        Args:
            path: Path to the file or directory
            
        Returns:
            str: Formatted statistics
            
        Raises:
            ValueError: If stats retrieval fails
        """
        abs_path = validate_operation(path, "get_stats")
        
        if not os.path.exists(abs_path):
            raise ValueError(f"Path does not exist: {path}")
        
        try:
            result = f"Statistics for: {path}\n\n"
            
            # Basic file/directory information
            stat_info = os.stat(abs_path)
            
            # Basic info
            result += f"Type: {'Directory' if os.path.isdir(abs_path) else 'File'}\n"
            result += f"Size: {stat_info.st_size} bytes\n"
            
            # Time info
            import datetime
            result += f"Created: {datetime.datetime.fromtimestamp(stat_info.st_ctime)}\n"
            result += f"Modified: {datetime.datetime.fromtimestamp(stat_info.st_mtime)}\n"
            result += f"Accessed: {datetime.datetime.fromtimestamp(stat_info.st_atime)}\n"
            
            # Permission info
            import stat
            mode = stat_info.st_mode
            perms = ""
            for who in "USR", "GRP", "OTH":
                for what in "R", "W", "X":
                    perm = getattr(stat, f"S_I{what}{who}")
                    perms += what.lower() if mode & perm else "-"
            result += f"Permissions: {perms}\n"
            
            # Owner info
            try:
                import pwd, grp
                user = pwd.getpwuid(stat_info.st_uid).pw_name
                group = grp.getgrgid(stat_info.st_gid).gr_name
                result += f"Owner: {user}:{group}\n"
            except (ImportError, KeyError):
                result += f"Owner ID: {stat_info.st_uid}:{stat_info.st_gid}\n"
            
            # For directories, count contents
            if os.path.isdir(abs_path):
                try:
                    entries = os.listdir(abs_path)
                    dirs = sum(1 for e in entries if os.path.isdir(os.path.join(abs_path, e)))
                    files = sum(1 for e in entries if os.path.isfile(os.path.join(abs_path, e)))
                    result += f"\nContents: {len(entries)} total entries\n"
                    result += f"- {dirs} directories\n"
                    result += f"- {files} files\n"
                except Exception as e:
                    result += f"\nError counting contents: {str(e)}\n"
                    
                # Git repository information
                try:
                    from ..utils.git_utils import get_repo, check_git_available, GitError
                    try:
                        check_git_available()
                        repo = get_repo(abs_path)
                        result += "\nGit Repository Information:\n"
                        result += f"- Repository root: {repo.working_dir}\n"
                        result += f"- Active branch: {repo.active_branch.name}\n"
                        
                        # Get commit count
                        try:
                            commit_count = sum(1 for _ in repo.iter_commits())
                            result += f"- Total commits: {commit_count}\n"
                        except Exception:
                            pass
                        
                        # Check if clean
                        result += f"- Clean working tree: {'Yes' if not repo.is_dirty() else 'No'}\n"
                    except GitError:
                        # Not a Git repository or Git not available
                        pass
                except ImportError:
                    # Git module not available
                    pass
            # For files, additional details
            else:
                import mimetypes
                mime_type, _ = mimetypes.guess_type(abs_path)
                result += f"MIME Type: {mime_type or 'application/octet-stream'}\n"
                
                # Check if text file and count lines
                from ..utils.security import is_text_file
                if is_text_file(abs_path):
                    try:
                        with open(abs_path, 'r', encoding='utf-8') as f:
                            lines = sum(1 for _ in f)
                        result += f"Line count: {lines}\n"
                    except Exception:
                        result += "Unable to count lines (possibly binary file)\n"
                
                # Get checksum
                from ..utils.path_utils import generate_checksum
                result += f"Checksum (SHA-256): {generate_checksum(abs_path)}\n"
                
                # Git file information
                try:
                    from ..utils.git_utils import get_repo, get_file_history, check_git_available, GitError
                    try:
                        check_git_available()
                        repo = get_repo(abs_path)
                        history = get_file_history(abs_path, max_count=1)
                        
                        if history:
                            commit = history[0]
                            result += "\nGit File Information:\n"
                            result += f"- Last commit: {commit['commit'][:8]}\n"
                            result += f"- Commit date: {commit['date']}\n"
                            result += f"- Author: {commit['author']}\n"
                            result += f"- Message: {commit['message'].strip()}\n"
                    except GitError:
                        # Not a Git repository, Git not available, or file not tracked
                        pass
                except ImportError:
                    # Git module not available
                    pass
                
            return result
        except Exception as e:
            raise ValueError(f"Error getting path statistics: {str(e)}")
