"""
Git utilities for FileOps MCP.

This module contains functions for working with Git repositories,
including initialization, commits, logs, and diffs.
"""
import os
import time
import re
from typing import Dict, Any, List, Optional, Tuple, Union

# Import git module
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

from ..constants import config
from .security import log_security_event, sanitize_path
from .path_utils import get_relative_path

class GitError(Exception):
    """Custom exception for Git-related errors."""
    pass

def check_git_available():
    """
    Check if Git functionality is available.
    
    Raises:
        GitError: If Git is not available
    """
    if not GIT_AVAILABLE:
        raise GitError("Git functionality is not available. Please install 'gitpython' package.")
    
    if not config.git_enabled:
        raise GitError("Git functionality is disabled in configuration.")

def get_repo(path: str) -> 'git.Repo':
    """
    Get Git repository for a path.
    
    Args:
        path: Path within a Git repository
        
    Returns:
        git.Repo: Git repository
        
    Raises:
        GitError: If path is not in a Git repository
    """
    check_git_available()
    
    try:
        # If path is a file, use its directory
        if os.path.isfile(path):
            path = os.path.dirname(path)
            
        # Try to find repository
        repo = git.Repo(path, search_parent_directories=True)
        
        # Validate repository root is within working directory
        repo_root = os.path.abspath(repo.working_dir)
        if not repo_root.startswith(config.abs_working_dir):
            raise GitError(f"Repository root {repo_root} is outside the working directory")
        
        return repo
    except git.InvalidGitRepositoryError:
        raise GitError(f"No Git repository found at or above {path}")
    except git.NoSuchPathError:
        raise GitError(f"Path does not exist: {path}")
    except Exception as e:
        raise GitError(f"Error accessing Git repository: {str(e)}")

def init_repo(path: str) -> str:
    """
    Initialize a new Git repository.
    
    Args:
        path: Path to initialize repository
        
    Returns:
        str: Success message
        
    Raises:
        GitError: If repository initialization fails
    """
    check_git_available()
    
    try:
        # Ensure path is a directory
        if os.path.isfile(path):
            path = os.path.dirname(path)
            
        # Check if already a Git repository
        try:
            git.Repo(path)
            return f"Repository already exists at {path}"
        except git.InvalidGitRepositoryError:
            pass
        
        # Initialize repository
        repo = git.Repo.init(path)
        
        # Set up initial configuration
        with repo.config_writer() as config_writer:
            config_writer.set_value("user", "name", config.git_username)
            config_writer.set_value("user", "email", config.git_email)
        
        # Create .gitignore if it doesn't exist
        gitignore_path = os.path.join(path, '.gitignore')
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, 'w') as f:
                f.write("# Automatically created by FileOps MCP\n")
                f.write("*.pyc\n__pycache__/\n.DS_Store\n")
        
        return f"Successfully initialized Git repository at {path}"
    except Exception as e:
        raise GitError(f"Failed to initialize Git repository: {str(e)}")

def commit_file(path: str, message: str = None, operation: str = None) -> str:
    """
    Commit changes to a file.
    
    Args:
        path: Path to the file
        message: Commit message (recommended for better version history)
        operation: Operation that triggered the commit
        
    Returns:
        str: Commit hash or None if no changes
        
    Raises:
        GitError: If commit fails
        
    Note:
        For better version history, provide descriptive commit messages that explain
        what changes were made and why. If no message is provided, a generic message
        will be generated based on the operation or filepath.
    """
    check_git_available()
    
    try:
        # Get repository
        repo = get_repo(path)
        
        # Get relative path from repo root
        rel_path = os.path.relpath(os.path.abspath(path), repo.working_dir)
        
        # Check if file is tracked or new
        is_new = rel_path not in repo.git.ls_files().split()
        
        # Stage file
        repo.git.add(rel_path)
        
        # Check if there are changes to commit
        if not repo.is_dirty():
            return "No changes to commit"
        
        # Generate commit message if not provided
        if not message:
            if operation:
                message = config.git_commit_template.format(
                    operation=operation,
                    path=rel_path
                )
            else:
                message = f"Updated {rel_path}"
        
        # Make commit
        commit = repo.index.commit(message)
        
        action = "Added" if is_new else "Updated"
        return f"{action} and committed {rel_path}: {commit.hexsha[:8]}"
    except Exception as e:
        raise GitError(f"Failed to commit changes: {str(e)}")

def get_file_history(path: str, max_count: int = 10) -> List[Dict[str, Any]]:
    """
    Get commit history for a file.
    
    Args:
        path: Path to the file
        max_count: Maximum number of commits to return
        
    Returns:
        List[Dict[str, Any]]: List of commit information
        
    Raises:
        GitError: If history retrieval fails
    """
    check_git_available()
    
    try:
        # Get repository
        repo = get_repo(path)
        
        # Get relative path from repo root
        rel_path = os.path.relpath(os.path.abspath(path), repo.working_dir)
        
        # Get commit history
        commits = list(repo.iter_commits(paths=rel_path, max_count=max_count))
        
        # Format commit information
        history = []
        for commit in commits:
            # Get changes in this commit for the specific file
            file_changes = []
            for parent in commit.parents:
                diff = parent.diff(commit, paths=rel_path)
                for d in diff:
                    change_type = d.change_type
                    if change_type == 'A':
                        file_changes.append(f"Added: {rel_path}")
                    elif change_type == 'D':
                        file_changes.append(f"Deleted: {rel_path}")
                    elif change_type == 'R':
                        file_changes.append(f"Renamed: {d.a_path} -> {d.b_path}")
                    elif change_type == 'M':
                        file_changes.append(f"Modified: {rel_path}")
            
            history.append({
                'commit': commit.hexsha,
                'author': f"{commit.author.name} <{commit.author.email}>",
                'date': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(commit.committed_date)),
                'message': commit.message,
                'changes': file_changes
            })
        
        return history
    except Exception as e:
        raise GitError(f"Failed to get file history: {str(e)}")

def get_file_at_commit(path: str, commit_id: str = "HEAD") -> str:
    """
    Get the contents of a file at a specific commit.
    
    Args:
        path: Path to the file
        commit_id: Commit ID or reference
        
    Returns:
        str: File contents
        
    Raises:
        GitError: If retrieval fails
    """
    check_git_available()
    
    try:
        # Get repository
        repo = get_repo(path)
        
        # Get relative path from repo root
        rel_path = os.path.relpath(os.path.abspath(path), repo.working_dir)
        
        # Resolve commit ID
        try:
            commit = repo.commit(commit_id)
        except git.BadName:
            raise GitError(f"Invalid commit reference: {commit_id}")
        
        # Get file contents at that commit
        try:
            blob = commit.tree / rel_path
            return blob.data_stream.read().decode('utf-8')
        except KeyError:
            raise GitError(f"File {rel_path} does not exist in commit {commit_id}")
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(f"Failed to get file at commit: {str(e)}")

def get_file_diff(path: str, commit1: str = "HEAD~1", commit2: str = "HEAD") -> str:
    """
    Get diff between two commits for a file.
    
    Args:
        path: Path to the file
        commit1: First commit ID or reference
        commit2: Second commit ID or reference
        
    Returns:
        str: Diff output
        
    Raises:
        GitError: If diff fails
    """
    check_git_available()
    
    try:
        # Get repository
        repo = get_repo(path)
        
        # Get relative path from repo root
        rel_path = os.path.relpath(os.path.abspath(path), repo.working_dir)
        
        # Get diff
        try:
            diff = repo.git.diff(commit1, commit2, "--", rel_path)
            if not diff:
                return "No differences found between these commits for this file."
            return diff
        except git.GitCommandError as e:
            # Check if error is due to file not existing in one of the commits
            if "does not exist" in str(e) or "exists on disk, but not in" in str(e):
                # Try to determine if file was added or deleted
                try:
                    repo.git.show(f"{commit1}:{rel_path}")
                    try:
                        repo.git.show(f"{commit2}:{rel_path}")
                        # File exists in both commits but diff failed for another reason
                        raise GitError(f"Failed to get diff: {str(e)}")
                    except git.GitCommandError:
                        # File exists in commit1 but not in commit2
                        return f"File was deleted between {commit1} and {commit2}"
                except git.GitCommandError:
                    try:
                        repo.git.show(f"{commit2}:{rel_path}")
                        # File exists in commit2 but not in commit1
                        return f"File was added between {commit1} and {commit2}"
                    except git.GitCommandError:
                        # File doesn't exist in either commit
                        raise GitError(f"File {rel_path} does not exist in either commit")
            
            raise GitError(f"Failed to get diff: {str(e)}")
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(f"Failed to get file diff: {str(e)}")

def revert_to_commit(path: str, commit_id: str) -> str:
    """
    Revert a file to its state at a specific commit.
    
    Args:
        path: Path to the file
        commit_id: Commit ID or reference
        
    Returns:
        str: Success message
        
    Raises:
        GitError: If revert fails
    """
    check_git_available()
    
    try:
        # Get repository
        repo = get_repo(path)
        
        # Get relative path from repo root
        rel_path = os.path.relpath(os.path.abspath(path), repo.working_dir)
        
        # Validate commit
        try:
            commit = repo.commit(commit_id)
        except git.BadName:
            raise GitError(f"Invalid commit reference: {commit_id}")
        
        # Check if file exists in the commit
        try:
            blob = commit.tree / rel_path
        except KeyError:
            raise GitError(f"File {rel_path} does not exist in commit {commit_id}")
        
        # Checkout file from commit
        repo.git.checkout(commit_id, "--", rel_path)
        
        # Commit the revert
        commit_msg = f"Reverted {rel_path} to state at {commit_id}"
        repo.git.add(rel_path)
        if repo.is_dirty():
            new_commit = repo.index.commit(commit_msg)
            return f"Reverted to commit {commit_id} and created new commit {new_commit.hexsha[:8]}"
        else:
            return f"File is already at the state of commit {commit_id}"
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(f"Failed to revert file: {str(e)}")

def get_repo_status(path: str) -> Dict[str, Any]:
    """
    Get status of a Git repository.
    
    Args:
        path: Path within repository
        
    Returns:
        Dict[str, Any]: Repository status
        
    Raises:
        GitError: If status retrieval fails
    """
    check_git_available()
    
    try:
        # Get repository
        repo = get_repo(path)
        
        # Get status
        status = {
            'path': repo.working_dir,
            'active_branch': str(repo.active_branch),
            'is_dirty': repo.is_dirty(),
            'untracked_files': repo.untracked_files,
            'staged_files': [],
            'changed_files': [],
            'latest_commit': None,
        }
        
        # Get staged and changed files
        for item in repo.index.diff("HEAD"):
            status['staged_files'].append(item.a_path)
        
        for item in repo.index.diff(None):
            status['changed_files'].append(item.a_path)
        
        # Get latest commit if available
        try:
            latest_commit = next(repo.iter_commits(max_count=1))
            status['latest_commit'] = {
                'hash': latest_commit.hexsha,
                'author': f"{latest_commit.author.name} <{latest_commit.author.email}>",
                'date': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(latest_commit.committed_date)),
                'message': latest_commit.message,
            }
        except StopIteration:
            # No commits yet
            pass
        
        return status
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(f"Failed to get repository status: {str(e)}")

def auto_commit_changes(path: str, operation: str, commit_message: str = None) -> Optional[str]:
    """
    Automatically commit changes if configured to do so.
    
    Args:
        path: Path to the file
        operation: Operation that triggered the commit
        commit_message: Custom commit message (optional)
        
    Returns:
        Optional[str]: Commit result or None if auto-commit is disabled
    """
    if not config.git_enabled or not config.git_auto_commit:
        return None
    
    try:
        # Check if path is in a Git repository
        try:
            repo = get_repo(path)
        except GitError:
            # Not in a Git repository, try to initialize one
            repo_path = os.path.dirname(path) if os.path.isfile(path) else path
            init_repo(repo_path)
        
        # Get relative path for better readability in commit message
        rel_path = os.path.relpath(os.path.abspath(path), repo.working_dir)
        
        # Format the final commit message with a standardized prefix
        formatted_message = None
        if commit_message:
            # If custom message is provided, add it after the standardized prefix
            formatted_message = f"[{operation}] {rel_path}: {commit_message}"
        
        # Commit changes with the formatted message
        return commit_file(path, message=formatted_message, operation=operation)
    except Exception as e:
        # Log error but don't interrupt the main operation
        log_security_event("auto_commit_error", {
            "path": path,
            "operation": operation,
            "error": str(e)
        })
        return f"Auto-commit failed: {str(e)}"

def get_current_branch(path: str) -> str:
    """
    Get the name of the current branch.
    
    Args:
        path: Path within the repository
        
    Returns:
        str: Name of the current branch
        
    Raises:
        GitError: If getting the branch fails
    """
    try:
        repo = get_repo(path)
        return str(repo.active_branch)
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(f"Failed to get current branch: {str(e)}")

def list_branches(path: str) -> List[Dict[str, Any]]:
    """
    Get a list of all branches in the repository.
    
    Args:
        path: Path within the repository
        
    Returns:
        List[Dict[str, Any]]: List of branch information
        
    Raises:
        GitError: If listing branches fails
    """
    try:
        repo = get_repo(path)
        current = str(repo.active_branch)
        
        branches = []
        for branch in repo.branches:
            branches.append({
                'name': branch.name,
                'is_current': branch.name == current,
                # Try to get the commit it points to
                'commit': branch.commit.hexsha,
                'last_commit_date': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(branch.commit.committed_date)),
                'last_commit_message': branch.commit.message.strip(),
            })
        
        return branches
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(f"Failed to list branches: {str(e)}")

def create_branch(path: str, branch_name: str) -> bool:
    """
    Create a new branch at the current HEAD.
    
    Args:
        path: Path within the repository
        branch_name: Name of the new branch
        
    Returns:
        bool: True if successful
        
    Raises:
        GitError: If creating the branch fails
    """
    try:
        repo = get_repo(path)
        
        # Check if branch already exists
        if branch_name in [b.name for b in repo.branches]:
            raise GitError(f"Branch '{branch_name}' already exists")
        
        # Create new branch at current HEAD
        repo.git.branch(branch_name)
        
        return True
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(f"Failed to create branch: {str(e)}")

def switch_branch(path: str, branch_name: str) -> bool:
    """
    Switch to a different branch.
    
    Args:
        path: Path within the repository
        branch_name: Name of the branch to switch to
        
    Returns:
        bool: True if successful
        
    Raises:
        GitError: If switching branches fails
    """
    try:
        repo = get_repo(path)
        
        # Check if branch exists
        if branch_name not in [b.name for b in repo.branches]:
            raise GitError(f"Branch '{branch_name}' does not exist")
        
        # Check for uncommitted changes
        if repo.is_dirty():
            raise GitError("Cannot switch branches with uncommitted changes. Commit or stash changes first.")
        
        # Switch branch
        repo.git.checkout(branch_name)
        
        return True
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(f"Failed to switch branch: {str(e)}")