"""
Version control operations for FileOps MCP.

This module contains tools for Git-based version control operations.
"""
import os
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from ..utils.security import validate_operation, log_security_event, with_error_handling
from ..utils.path_utils import get_file_info, get_dir_info
from ..utils.git_utils import (
    GitError, check_git_available, init_repo, commit_file,
    get_file_history, get_file_at_commit, get_file_diff,
    revert_to_commit, get_repo_status
)

def register_version_operations(mcp: FastMCP) -> None:
    """
    Register version control operations with the MCP server.
    
    Args:
        mcp: The MCP server instance
    """
    @with_error_handling
    @mcp.tool()
    async def git_init(path: str = ".") -> str:
        """
        Initialize a Git repository.
        
        Args:
            path: Path to initialize repository
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If repository initialization fails
        """
        abs_path = validate_operation(path, "git_init")
        
        try:
            return init_repo(abs_path)
        except GitError as e:
            raise ValueError(str(e))

    @with_error_handling
    @mcp.tool()
    async def git_commit(path: str, message: str = None) -> str:
        """
        Commit changes to a file or directory.
        
        Args:
            path: Path to the file or directory
            message: Commit message (recommended for better version tracking)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If commit fails
            
        Note:
            Providing a descriptive commit message is highly recommended for better version
            history. A good commit message explains the nature of the changes and why they
            were made. If no message is provided, a generic message will be generated.
        """
        abs_path = validate_operation(path, "git_commit")
        
        try:
            return commit_file(abs_path, message)
        except GitError as e:
            raise ValueError(str(e))

    @with_error_handling
    @mcp.tool()
    async def git_log(path: str, max_count: int = 10) -> str:
        """
        Get commit history for a file.
        
        Args:
            path: Path to the file
            max_count: Maximum number of commits to return
            
        Returns:
            str: Formatted commit history
            
        Raises:
            ValueError: If history retrieval fails
        """
        abs_path = validate_operation(path, "git_log")
        
        try:
            # Limit maximum results
            max_count = min(50, max(1, max_count))
            
            history = get_file_history(abs_path, max_count)
            
            if not history:
                return f"No commit history found for {path}"
            
            # Format the history
            result = f"Commit history for {path}:\n\n"
            
            for i, commit in enumerate(history):
                result += f"{i+1}. Commit: {commit['commit'][:8]}\n"
                result += f"   Author: {commit['author']}\n"
                result += f"   Date: {commit['date']}\n"
                result += f"   Message: {commit['message']}\n"
                
                if commit.get('changes'):
                    result += "   Changes:\n"
                    for change in commit['changes']:
                        result += f"   - {change}\n"
                
                result += "\n"
            
            return result
        except GitError as e:
            raise ValueError(str(e))

    @with_error_handling
    @mcp.tool()
    async def git_show(path: str, commit_id: str = "HEAD") -> str:
        """
        Show a file's content at a specific commit.
        
        Args:
            path: Path to the file
            commit_id: Commit ID or reference
            
        Returns:
            str: File contents at that commit
            
        Raises:
            ValueError: If file retrieval fails
        """
        abs_path = validate_operation(path, "git_show")
        
        try:
            content = get_file_at_commit(abs_path, commit_id)
            
            # Get file info
            filename = os.path.basename(abs_path)
            
            return f"Contents of {filename} at commit {commit_id}:\n\n{content}"
        except GitError as e:
            raise ValueError(str(e))

    @with_error_handling
    @mcp.tool()
    async def git_diff(path: str, commit1: str = "HEAD~1", commit2: str = "HEAD") -> str:
        """
        Show differences between two commits for a file.
        
        Args:
            path: Path to the file
            commit1: First commit ID or reference
            commit2: Second commit ID or reference
            
        Returns:
            str: Diff output
            
        Raises:
            ValueError: If diff fails
        """
        abs_path = validate_operation(path, "git_diff")
        
        try:
            diff = get_file_diff(abs_path, commit1, commit2)
            
            filename = os.path.basename(abs_path)
            return f"Differences for {filename} between {commit1} and {commit2}:\n\n{diff}"
        except GitError as e:
            raise ValueError(str(e))

    @with_error_handling
    @mcp.tool()
    async def git_revert(path: str, commit_id: str) -> str:
        """
        Revert a file to its state at a specific commit.
        
        Args:
            path: Path to the file
            commit_id: Commit ID or reference
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If revert fails
        """
        abs_path = validate_operation(path, "git_revert")
        
        try:
            return revert_to_commit(abs_path, commit_id)
        except GitError as e:
            raise ValueError(str(e))

    @with_error_handling
    @mcp.tool()
    async def git_status(path: str = ".") -> str:
        """
        Show the status of a Git repository.
        
        Args:
            path: Path within repository
            
        Returns:
            str: Formatted repository status
            
        Raises:
            ValueError: If status retrieval fails
        """
        abs_path = validate_operation(path, "git_status")
        
        try:
            status = get_repo_status(abs_path)
            
            result = f"Git repository status for {status['path']}:\n\n"
            
            # Current branch
            result += f"Branch: {status['active_branch']}\n\n"
            
            # Working tree status
            result += f"Working tree: {'Dirty (has uncommitted changes)' if status['is_dirty'] else 'Clean'}\n\n"
            
            # Latest commit
            if status.get('latest_commit'):
                commit = status['latest_commit']
                result += "Latest commit:\n"
                result += f"  Hash: {commit['hash'][:8]}\n"
                result += f"  Author: {commit['author']}\n"
                result += f"  Date: {commit['date']}\n"
                result += f"  Message: {commit['message']}\n\n"
            else:
                result += "No commits yet.\n\n"
            
            # Staged files
            if status['staged_files']:
                result += "Staged files:\n"
                for file in status['staged_files']:
                    result += f"  {file}\n"
                result += "\n"
            
            # Changed files
            if status['changed_files']:
                result += "Changed files (not staged):\n"
                for file in status['changed_files']:
                    result += f"  {file}\n"
                result += "\n"
            
            # Untracked files
            if status['untracked_files']:
                result += "Untracked files:\n"
                for file in status['untracked_files']:
                    result += f"  {file}\n"
                result += "\n"
            
            return result
        except GitError as e:
            raise ValueError(str(e))


    @with_error_handling
    @mcp.tool()
    async def git_branch_list(path: str = ".") -> str:
        """
        List all branches in the repository.
        
        Args:
            path: Path within repository
            
        Returns:
            str: Formatted list of branches
            
        Raises:
            ValueError: If listing branches fails
        """
        abs_path = validate_operation(path, "git_branch_list")
        
        try:
            # Get branches
            from ..utils.git_utils import list_branches, get_current_branch
            branches = list_branches(abs_path)
            current = get_current_branch(abs_path)
            
            if not branches:
                return "No branches found in the repository."
            
            # Format the output
            result = f"Branches in repository at {path}:\n\n"
            
            for branch in branches:
                marker = "*" if branch["is_current"] else " "
                result += f"{marker} {branch['name']}"
                
                # Add last commit info
                result += f" - {branch['last_commit_date']}"
                result += f" ({branch['commit'][:8]})"
                
                # Add commit message preview (first line only)
                message = branch['last_commit_message'].split("\n")[0]
                if len(message) > 50:
                    message = message[:47] + "..."
                result += f" {message}\n"
            
            return result
        except GitError as e:
            raise ValueError(str(e))

    @with_error_handling
    @mcp.tool()
    async def git_branch_create(path: str, branch_name: str) -> str:
        """
        Create a new branch at the current HEAD.
        
        Args:
            path: Path within repository
            branch_name: Name of the new branch
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If branch creation fails
        """
        abs_path = validate_operation(path, "git_branch_create")
        
        if not branch_name:
            raise ValueError("Branch name is required")
        
        try:
            # Create branch
            from ..utils.git_utils import create_branch, get_current_branch
            create_branch(abs_path, branch_name)
            current = get_current_branch(abs_path)
            
            return f"Successfully created branch '{branch_name}' at the current HEAD on branch '{current}'"
        except GitError as e:
            raise ValueError(str(e))

    @with_error_handling
    @mcp.tool()
    async def git_branch_switch(path: str, branch_name: str) -> str:
        """
        Switch to a different branch.
        
        Args:
            path: Path within repository
            branch_name: Name of the branch to switch to
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If branch switching fails
        """
        abs_path = validate_operation(path, "git_branch_switch")
        
        if not branch_name:
            raise ValueError("Branch name is required")
        
        try:
            # Get current branch first for better message
            from ..utils.git_utils import switch_branch, get_current_branch
            old_branch = get_current_branch(abs_path)
            
            # Switch branch
            switch_branch(abs_path, branch_name)
            
            return f"Successfully switched from branch '{old_branch}' to '{branch_name}'"
        except GitError as e:
            raise ValueError(str(e))