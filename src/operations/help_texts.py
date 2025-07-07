"""
Help text definitions for FileOps MCP operations.
"""

HELP_TEXTS = {
    "copy_file": """
copy_file: Copy a file from source path to destination path

Arguments:
- path: Path to the source file (required)
- dest_path: Path to the destination file (required, or use content)
- content: Alternative way to specify destination path (if dest_path is not provided)
- commit_message: Custom Git commit message (optional)

Example:
copy_file(path="original.txt", dest_path="copy.txt", commit_message="Create backup of configuration file")
copy_file(path="src/config.json", content="backup/config.json")

Notes:
- Works with both text and binary files
- Creates parent directories automatically if needed
- Verifies copy with checksum comparison
- Not available in read-only mode
- If Git is enabled, automatically commits the new file with the provided message or a default one
""",
    "copy_multiple_files": """
copy_multiple_files: Copy multiple files from source paths to destination paths or directory

Arguments:
- source_paths: List of paths to the source files (required)
- dest_paths: List of destination file paths (must match length of source_paths if provided)
- dest_dir: Destination directory (alternative to dest_paths - all files copied here with same names)
- commit_message: Custom Git commit message (optional)

Example:
copy_multiple_files(source_paths=["file1.txt", "file2.txt"], dest_paths=["backup1.txt", "backup2.txt"], commit_message="Create backups of configuration files")
copy_multiple_files(source_paths=["src/config.json", "src/settings.py"], dest_dir="backup", commit_message="Backup source configuration files")
copy_multiple_files(source_paths=["logs/app.log", "logs/error.log", "logs/access.log"], dest_dir="archive/2024")

Notes:
- Works with both text and binary files
- Either dest_paths or dest_dir must be provided, but not both
- If dest_paths is used, its length must match source_paths length
- If dest_dir is used, all files are copied to that directory with their original filenames
- Creates parent directories automatically if needed
- Uses atomic copy operations for each file with checksum verification
- Continues processing other files even if some copies fail
- Provides detailed success/failure reporting for each file
- Verifies each copy with checksum comparison to ensure data integrity
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
""",
    "move_file": """
move_file: Move (rename) a file from source path to destination path

Arguments:
- path: Path to the source file (required)
- dest_path: Path to the destination file (required, or use content)
- content: Alternative way to specify destination path (if dest_path is not provided)
- commit_message: Custom Git commit message (optional)

Example:
move_file(path="draft.txt", dest_path="final.txt", commit_message="Rename draft to final version")
move_file(path="reports/old.pdf", content="archive/2023/report.pdf")

Notes:
- Works with both text and binary files
- Creates parent directories automatically if needed
- Uses atomic rename when possible, falls back to copy+delete when necessary
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
""",
    "move_multiple_files": """
move_multiple_files: Move multiple files from source paths to destination paths or directory

Arguments:
- source_paths: List of paths to the source files (required)
- dest_paths: List of destination file paths (must match length of source_paths if provided)
- dest_dir: Destination directory (alternative to dest_paths - all files moved here with same names)
- commit_message: Custom Git commit message (optional)

Example:
move_multiple_files(source_paths=["file1.txt", "file2.txt"], dest_paths=["new1.txt", "new2.txt"], commit_message="Reorganize project files")
move_multiple_files(source_paths=["draft1.md", "draft2.md"], dest_dir="archive", commit_message="Archive draft documents")
move_multiple_files(source_paths=["temp/a.log", "temp/b.log", "temp/c.log"], dest_dir="logs/processed")

Notes:
- Works with both text and binary files
- Either dest_paths or dest_dir must be provided, but not both
- If dest_paths is used, its length must match source_paths length
- If dest_dir is used, all files are moved to that directory with their original filenames
- Creates parent directories automatically if needed
- Uses atomic operations for each file move
- Continues processing other files even if some moves fail
- Provides detailed success/failure reporting for each file
- Uses atomic rename when possible, falls back to copy+delete when necessary
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
""",
    "read_file": """
read_file: Read the contents of a text file

Arguments:
- path: Path to the file to read (required)
- start_line: Optional starting line number (1-indexed, inclusive). If not specified, reads from beginning.
- end_line: Optional ending line number (1-indexed, inclusive). If not specified, reads to end.

Example:
read_file(path="example.txt")
read_file(path="config.py", start_line=10)
read_file(path="log.txt", end_line=50)
read_file(path="source.py", start_line=25, end_line=75)

Notes:
- Only text files are supported (not binary files)
- Files larger than 10MB cannot be read
- Path must be within the working directory
- Line numbers are 1-indexed (first line is line 1)
- start_line must be <= end_line when both are specified
- Line range information is displayed when using start_line or end_line
""",
    "read_multiple_files": """
read_multiple_files: Read the contents of multiple text files

Arguments:
- paths: List of paths to the files to read (required)

Example:
read_multiple_files(paths=["config.json", "README.md"])

Notes:
- Only text files are supported (not binary files)
- Files larger than 10MB cannot be read
- Results include file info and content for each successfully read file
- Failed files (binary, non-existent, etc.) are reported at the end
- All paths must be within the working directory
""",
    "list_dir": """
list_dir: List the contents of a directory with detailed information

Arguments:
- path: Path to the directory to list (default: ".")

Example:
list_dir(path="src")

Notes:
- Hidden files (starting with '.') are filtered by default
- File sizes are displayed in human-readable format (bytes, KB, MB)
- MIME types are detected for each file
""",
    "get_tree": """
get_tree: Get a tree view of a directory

Arguments:
- path: Path to the directory to visualize (default: ".")

Example:
get_tree(path="src")

Notes:
- Tree depth is limited by max_depth (default: 5)
- Hidden files (starting with '.') are filtered by default
- Large directory trees are truncated with "..." indicators
""",
    "get_stats": """
get_stats: Get detailed information about a file or directory

Arguments:
- path: Path to the file or directory to analyze (required)

Example:
get_stats(path="example.txt")

Notes:
- For files: Shows size, timestamps, permissions, MIME type, line count (for text files), and checksum
- For directories: Shows size, timestamps, permissions, and content counts
- If the path is in a Git repository, additional Git information is shown
""",
    "create_file": """
create_file: Create a new text file with the specified content

Arguments:
- path: Where to create the file (required)
- content: Text content or object to write to the file. If an object is provided,
          it will be serialized as JSON (default: "")
- commit_message: Custom Git commit message (optional)

Example:
create_file(path="notes.txt", content="Meeting notes for today", commit_message="Add initial meeting notes")
create_file(path="config.json", content={"debug": true, "port": 8080}, commit_message="Create configuration file")

Notes:
- Parent directories will be created automatically if they don't exist
- Uses atomic write operations for safety
- Objects are automatically serialized as JSON
- Not available in read-only mode
- If Git is enabled, automatically commits the new file
- When providing a custom commit_message, it will be formatted as "[create_file] path: your_message"
- This standardized format ensures consistent commit message formatting
""",
    "update_file": """
update_file: Update specific text within a file by replacing matching content

Arguments:
- path: Path to the file to update (required)
- old_string: Text or object to find and replace. If an object is provided, it will be serialized as JSON (required)
- new_string: Replacement text or object. If an object is provided, it will be serialized as JSON (required)
- commit_message: Custom Git commit message (optional)
- old_str: Alternative parameter name for old_string (backup for LLM compatibility)
- new_str: Alternative parameter name for new_string (backup for LLM compatibility)

Example:
update_file(path="README.md", old_string="# Draft", new_string="# Final Version", commit_message="Update document status to final")
update_file(path="config.json", old_string={"debug": false}, new_string={"debug": true}, commit_message="Enable debug mode")
update_file(path="README.md", old_str="# Draft", new_str="# Final Version")

Notes:
- Only works with text files (not binary files)
- Uses exact string matching (not regex)
- Objects are automatically serialized as JSON for comparison and replacement
- Provides before/after checksums for verification
- Uses atomic write operations for safety
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
- Backup parameters old_str and new_str can be used when LLMs transform parameter names
- Either (old_string, new_string) or (old_str, new_str) must be provided, but not both
""",
    "rewrite_file": """
rewrite_file: Replace the entire content of a file

Arguments:
- path: Path to the file to rewrite (required)
- content: New content for the file. If an object is provided,
          it will be serialized as JSON (required)
- commit_message: Custom Git commit message (optional)

Example:
rewrite_file(path="notes.txt", content="Updated notes", commit_message="Complete rewrite with new format")
rewrite_file(path="settings.json", content={"theme": "dark", "language": "en"}, commit_message="Reset to default settings")

Notes:
- Only works with text files (not binary files)
- Objects are automatically serialized as JSON
- Provides before/after checksums for verification
- Uses atomic write operations for safety
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
""",
    "delete_file": """
delete_file: Delete a file

Arguments:
- path: Path to the file to delete (required)
- commit_message: Custom Git commit message (optional)

Example:
delete_file(path="temp.txt", commit_message="Remove temporary configuration file")

Notes:
- Cannot delete directories (use delete_dir instead)
- Not available in read-only mode
- If Git is enabled, automatically commits the deletion with the provided message or a default one
""",
    "create_dir": """
create_dir: Create a new directory

Arguments:
- path: Where to create the directory (required)
- commit_message: Custom Git commit message (optional)

Example:
create_dir(path="new_folder", commit_message="Add folder for project assets")

Notes:
- Parent directories will be created automatically if they don't exist
- Not available in read-only mode
- If Git is enabled, automatically commits the new directory with the provided message or a default one
""",
    "delete_dir": """
delete_dir: Delete a directory

Arguments:
- path: Path to the directory to delete (required)
- recursive: Whether to delete non-empty directories (default: False)
- commit_message: Custom Git commit message (optional)

Example:
delete_dir(path="old_folder")
delete_dir(path="old_folder", recursive=True, commit_message="Remove deprecated project files")

Notes:
- By default, only empty directories can be deleted
- Use recursive=True to delete non-empty directories
- Not available in read-only mode
- If Git is enabled, automatically commits the deletion with the provided message or a default one
""",
    "search_files": """
search_files: Search for files matching a pattern

Arguments:
- path: Directory to search in (default: ".")
- pattern: File pattern to match (default: "*", max 500 characters)
- max_results: Maximum number of results to return (default: server limit)

Example:
search_files(path="src", pattern="*.py")
search_files(path="docs", pattern="*.md", max_results=10)

Notes:
- Uses glob patterns (*, ?, [abc], [!abc])
- File pattern is sanitized for security and limited to 500 characters
- Results are limited to max_results (default: 100)
- Hidden files (starting with '.') are filtered by default
""",
    "find_in_files": """
find_in_files: Search for text content within files

Arguments:
- path: Directory to search in (default: ".")
- text: Text to search for (required, max 1000 characters)
- file_pattern: File pattern to match (default: "*", max 500 characters)
- max_results: Maximum number of results to return (default: server limit)

Example:
find_in_files(path="src", text="TODO", file_pattern="*.py")
find_in_files(path=".", text="error", file_pattern="*.log", max_results=20)

Notes:
- Only searches in text files (not binary files)
- Results include file path, line number, and matching line
- Results are limited to max_results (default: 100)
- Both search text and file pattern are sanitized for security
- Search text length is limited to 1000 characters, file pattern to 500 characters
- Hidden files (starting with '.') are filtered by default
""",
    "search_in_file": """
search_in_file: Search for text content within a specific file

Arguments:
- file_path: Path to the file to search in (required)
- text: Text to search for (required, max 1000 characters)
- max_results: Maximum number of results to return (default: server limit)

Example:
search_in_file(file_path="src/main.py", text="TODO")
search_in_file(file_path="log.txt", text="error", max_results=10)

Notes:
- Only works with text files (not binary files)
- Results include file path, line number, and matching line content in format "file:line: content"
- Results are limited to max_results (default: 100)
- Search text is sanitized for security (removes control characters and shell metacharacters)
- Search text length is limited to 1000 characters to prevent performance issues
- File path must be within the working directory
- Output format is consistent with find_in_files for easy parsing
""",
    "git_init": """
git_init: Initialize a Git repository

Arguments:
- path: Path to initialize repository (default: ".")

Example:
git_init(path="my_project")

Notes:
- Creates a new Git repository with initial configuration
- Creates a basic .gitignore file if one doesn't exist
- Not available in read-only mode
- Requires gitpython package to be installed
""",
    "git_commit": """
git_commit: Commit changes to a file or directory

Arguments:
- path: Path to the file or directory to commit (required)
- message: Commit message (optional, but recommended for better version tracking)

Example:
git_commit(path="README.md", message="Update API documentation with new endpoints")

Notes:
- Commits the specified file or all changed files in the specified directory
- If message is not provided, a default message is generated
- For better version history, provide descriptive commit messages that explain the nature of the changes
- Provided commit messages are used as-is without any automatic formatting
- Not available in read-only mode
- Requires gitpython package to be installed
""",
    "git_log": """
git_log: Show commit history for a file

Arguments:
- path: Path to the file (required)
- max_count: Maximum number of commits to show (default: 10)

Example:
git_log(path="src/main.py", max_count=5)

Notes:
- Shows commit hash, author, date, and message
- Includes file-specific changes in each commit
- Limited to max_count commits (maximum 50)
- Requires gitpython package to be installed
""",
    "git_show": """
git_show: Show file content at a specific commit

Arguments:
- path: Path to the file (required)
- commit_id: Commit ID or reference (default: "HEAD")

Example:
git_show(path="config.json", commit_id="abc1234")
git_show(path="README.md", commit_id="HEAD~2")

Notes:
- Retrieves the content of a file at a specific commit
- Can use commit hash or references like HEAD, HEAD~1, etc.
- Requires gitpython package to be installed
""",
    "git_diff": """
git_diff: Show differences between two commits for a file

Arguments:
- path: Path to the file (required)
- commit1: First commit ID or reference (default: "HEAD~1")
- commit2: Second commit ID or reference (default: "HEAD")

Example:
git_diff(path="src/main.py")
git_diff(path="README.md", commit1="abc1234", commit2="def5678")

Notes:
- Shows changes between two commits in unified diff format
- Can use commit hashes or references like HEAD, HEAD~1, etc.
- Requires gitpython package to be installed
""",
    "git_revert": """
git_revert: Revert a file to a previous version

Arguments:
- path: Path to the file (required)
- commit_id: Commit ID or reference to revert to (required)

Example:
git_revert(path="config.json", commit_id="abc1234")

Notes:
- Reverts the file to its state at the specified commit
- Creates a new commit with the reversion
- Not available in read-only mode
- Requires gitpython package to be installed
""",
    "git_status": """
git_status: Show Git repository status

Arguments:
- path: Path within the repository (default: ".")

Example:
git_status(path="src")

Notes:
- Shows current branch, working tree status, and latest commit
- Lists staged, changed, and untracked files
- Requires gitpython package to be installed
""",
    "help": """
help: Get help information about available operations

Arguments:
- topic: Topic to get help on (default: "operations")

Example:
help()
help(topic="git_commit")

Notes:
- Use "operations" as the topic to get a list of all available operations
- Use a specific operation name as the topic to get detailed help on that operation
""",
    "remove_from_file": """
remove_from_file: Remove specific text from a file

Arguments:
- path: Path to the file to update (required)
- old_string: Text or object to find and remove. If an object is provided, it will be serialized as JSON (required)
- commit_message: Custom Git commit message (optional)

Example:
remove_from_file(path="README.md", old_string="# Draft", commit_message="Remove draft marker from documentation")
remove_from_file(path="config.json", old_string={"temp_setting": true}, commit_message="Remove temporary configuration")

Notes:
- Only works with text files (not binary files)
- Uses exact string matching (not regex)
- Objects are automatically serialized as JSON for comparison
- Provides before/after checksums for verification
- Uses atomic write operations for safety
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
""",
    "append_to_file": """
append_to_file: Append content to the end of a file

Arguments:
- path: Path to the file to append to (required)
- content: Text content or object to append. If an object is provided,
          it will be serialized as JSON (required)
- commit_message: Custom Git commit message (optional)

Example:
append_to_file(path="log.txt", content="New log entry", commit_message="Add audit log entry for user access")
append_to_file(path="notes.md", content="\\n\\n## Additional Notes")
append_to_file(path="data.json", content={"timestamp": "2024-01-01", "event": "user_login"}, commit_message="Add new event to log")

Notes:
- Only works with text files (not binary files)
- Creates the file if it doesn't exist
- Creates parent directories if they don't exist
- Objects are automatically serialized as JSON
- Provides before/after checksums for verification
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
""",
    "insert_in_file": """
insert_in_file: Insert content at a specific position in a file

Arguments:
- path: Path to the file to insert into (required)
- content: Text content or object to insert. If an object is provided,
          it will be serialized as JSON (required)
- after_line: Line number to insert after (0-indexed) (use only one positioning method)
- before_line: Line number to insert before (0-indexed) (use only one positioning method)
- after_pattern: Pattern to search for and insert after the first occurrence (use only one positioning method)
- commit_message: Custom Git commit message (optional)

Example:
insert_in_file(path="src/main.py", content="    # TODO: Refactor this method\\n", after_line=42)
insert_in_file(path="src/class.py", content="    def new_method(self):\\n        return 'Hello'\\n", after_pattern="def __init__")
insert_in_file(path="README.md", content="## Prerequisites\\n\\n", before_line=5, commit_message="Add prerequisites section")
insert_in_file(path="config.json", content={"new_feature": {"enabled": true}}, after_pattern='"existing_config":', commit_message="Add new feature configuration")

Notes:
- Only works with text files (not binary files)
- Requires exactly one position specifier (after_line, before_line, or after_pattern)
- Line numbers are 0-indexed (first line is line 0)
- After_pattern inserts after the first occurrence of the pattern
- Objects are automatically serialized as JSON
- If inserting mid-file, automatically adds a newline to the content if not already present
- Uses atomic write operations for safety
- Provides before/after checksums for verification
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
""",
    "git_branch_list": """
git_branch_list: List all branches in the repository

Arguments:
- path: Path within the repository (default: ".")

Example:
git_branch_list(path=".")

Notes:
- Shows all local branches with current branch marked with an asterisk (*)
- Includes last commit date, hash, and message for each branch
- Requires gitpython package to be installed
""",
    "git_branch_create": """
git_branch_create: Create a new branch at the current HEAD

Arguments:
- path: Path within the repository (required)
- branch_name: Name of the new branch (required)

Example:
git_branch_create(path=".", branch_name="feature-x")

Notes:
- Creates a new branch at the current HEAD position
- Does not switch to the newly created branch
- Not available in read-only mode
- Requires gitpython package to be installed
""",
    "git_branch_switch": """
git_branch_switch: Switch to a different branch

Arguments:
- path: Path within the repository (required)
- branch_name: Name of the branch to switch to (required)

Example:
git_branch_switch(path=".", branch_name="feature-x")

Notes:
- Switches to the specified branch
- Requires all changes to be committed first
- Not available in read-only mode
- Requires gitpython package to be installed
""",
    "file_exists": """
file_exists: Check if a file exists at the specified path

Arguments:
- path: Path to check for file existence (required)

Example:
file_exists(path="config.json")
file_exists(path="logs/error.log")

Notes:
- Returns detailed information if the file exists, including size and checksum
- Distinguishes between files and directories at the specified path
- Safe for use in read-only mode (no modifications are made)
- Path must be within the working directory
- Useful for conditional operations or verification before other file operations
""",
    "delete_multiple_files": """
delete_multiple_files: Delete multiple files from the specified paths

Arguments:
- paths: List of paths to the files to delete (required)
- commit_message: Custom Git commit message (optional)

Example:
delete_multiple_files(paths=["temp1.txt", "temp2.txt", "cache.log"], commit_message="Clean up temporary files")
delete_multiple_files(paths=["old/file1.txt", "old/file2.txt"])

Notes:
- Batch processing with detailed success/failure reporting for each file
- Individual file validation and error handling - continues even if some deletions fail
- Only deletes files, not directories (use delete_dir for directories)
- Not available in read-only mode
- If Git is enabled, automatically commits the deletions with the provided message or a default one
- Provides comprehensive summary of successful and failed deletions
- Each file path must be within the working directory
""",
    "read_image": """
read_image: Read and return an image file as a Pillow Image object

Arguments:
- path: Path to the image file to read (required)

Example:
read_image(path="screenshots/interface.png")
read_image(path="assets/logo.jpg")

Notes:
- Supports common image formats (JPEG, PNG, GIF, BMP, TIFF, WEBP)
- Returns a Pillow Image object that can be displayed or processed by the MCP client
- Image files are validated for security (no executable content)
- Path must be within the working directory
- File size is limited to 10MB for security and performance
- Only image files are supported (binary format validation applied)
- Uses Pillow (PIL) library for robust image format support
- Image metadata and format information are preserved in the returned object
""",
    "replace_all_in_file": """
replace_all_in_file: Replace ALL occurrences of specific text within a file

Arguments:
- path: Path to the file to update (required)
- old_string: Text or object to find and replace. If an object is provided, it will be serialized as JSON (required)
- new_string: Replacement text or object. If an object is provided, it will be serialized as JSON (required)
- commit_message: Custom Git commit message (optional)
- old_str: Alternative parameter name for old_string (backup for LLM compatibility)
- new_str: Alternative parameter name for new_string (backup for LLM compatibility)

Example:
replace_all_in_file(path="README.md", old_string="TODO", new_string="DONE", commit_message="Mark all TODOs as completed")
replace_all_in_file(path="config.json", old_string={"debug": false}, new_string={"debug": true}, commit_message="Enable debug mode everywhere")
replace_all_in_file(path="app.py", old_str="localhost", new_str="production.example.com")

Notes:
- Only works with text files (not binary files)
- Replaces EVERY occurrence of the old_string throughout the entire file (unlike update_file which may only replace the first occurrence)
- Uses exact string matching (not regex)
- Objects are automatically serialized as JSON for comparison and replacement
- Reports the number of replacements made for verification
- Provides before/after checksums for verification
- Uses atomic write operations for safety
- Not available in read-only mode
- If Git is enabled, automatically commits the changes with the provided message or a default one
- Backup parameters old_str and new_str can be used when LLMs transform parameter names
- Either (old_string, new_string) or (old_str, new_str) must be provided, but not both
""",
    "get_fileops_commandments": """
get_fileops_commandments: Get the FileOps Sixteen Commandments for MCP tool usage

Arguments:
None - this tool takes no arguments

Example:
get_fileops_commandments()

Notes:
- Returns the complete content of the FileOps-MCP-16-Commandments.md file
- Provides essential guidelines for effective use of MCP tools
- Contains best practices for file operations, security considerations, and workflow patterns
- Safe for use in read-only mode (no modifications are made)
- The commandments serve as a comprehensive reference for proper MCP tool usage
- Helps ensure consistent and secure file operations across all interactions
- Essential reading for understanding the proper workflow when working with FileOps MCP tools
""",
}