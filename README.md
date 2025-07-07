# FileOps MCP Server

A comprehensive MCP server that enables safe filesystem operations with Git version control through Claude and other LLM clients.

## Overview

FileOps allows LLMs to:
- Create, read, update, and delete text files
- Create and delete directories
- Generate visual file trees optimized for LLMs
- Search for files matching patterns
- Version files with Git integration (new)
- All with configurable security restrictions

## Features

### Resources

| URI Pattern | Description |
|-------------|-------------|
| `file://{path}` | Access file contents |
| `dir://{path}` | View directory contents |
| `filetree://{path}` | Get formatted directory tree |
| `stats://{path}` | Get detailed file/directory statistics |
| `gitlog://{path}` | View Git commit history (new) |
| `gitversion://{path}` | View file at current version (new) |
| `gitversion://{path}?version={commit_id}` | View file at specific commit (new) |
| `gitstatus://{path}` | View Git repository status (new) |

### Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `read_file` | Read file contents | `path`: File to read<br>`start_line`: Optional starting line number (1-indexed)<br>`end_line`: Optional ending line number (1-indexed) |
| `read_multiple_files` | Read multiple files at once | `paths`: List of file paths to read |
| `create_file` | Create new text files | `path`: Location<br>`content`: File content<br>`commit_message`: Custom Git commit message (optional) |
| `update_file` | Change text within files | `path`: Target file<br>`old_string`: Text to replace<br>`new_string`: Replacement text<br>`old_str`: Alternative parameter name for old_string (backup for LLM compatibility)<br>`new_str`: Alternative parameter name for new_string (backup for LLM compatibility)<br>`commit_message`: Custom Git commit message (optional) |
| `rewrite_file` | Replace entire file | `path`: Target file<br>`content`: New content<br>`commit_message`: Custom Git commit message (optional) |
| `delete_file` | Remove files | `path`: File to delete<br>`commit_message`: Custom Git commit message (optional) |
| `remove_from_file` | Remove specific text | `path`: Target file<br>`old_string`: Text to remove<br>`commit_message`: Custom Git commit message (optional) |
| `append_to_file` | Add text to end of file | `path`: Target file<br>`content`: Text to append<br>`commit_message`: Custom Git commit message (optional) |
| `insert_in_file` | Insert text at specific position | `path`: Target file<br>`content`: Text to insert<br>`after_line`: Line number to insert after (0-indexed) OR<br>`before_line`: Line number to insert before (0-indexed) OR<br>`after_pattern`: Text pattern to insert after<br>`commit_message`: Custom Git commit message (optional) |
| `copy_file` | Copy a file | `path`: Source file<br>`dest_path`: Destination file<br>`commit_message`: Custom Git commit message (optional) |
| `move_file` | Move/rename a file | `path`: Source file<br>`dest_path`: Destination file<br>`commit_message`: Custom Git commit message (optional) |
| `move_multiple_files` | Move multiple files | `source_paths`: List of source file paths<br>`dest_paths`: List of destination file paths (must match source_paths length if provided)<br>`dest_dir`: Destination directory (alternative to dest_paths)<br>`commit_message`: Custom Git commit message (optional) |
| `create_dir` | Create new folders | `path`: Directory to create<br>`commit_message`: Custom Git commit message (optional) |
| `delete_dir` | Remove directories | `path`: Directory to remove<br>`recursive`: Delete with contents (optional)<br>`commit_message`: Custom Git commit message (optional) |
| `get_tree` | Display folder structure | `path`: Starting directory<br>`max_depth`: Tree depth (optional) |
| `search_files` | Find files by pattern | `directory`: Where to search<br>`pattern`: What to find<br>`max_results`: Limit results (optional) |
| `find_in_files` | Search text in files | `directory`: Where to search<br>`text`: Text to find<br>`file_pattern`: File filter (optional)<br>`max_results`: Limit results (optional) |
| `git_init` | Initialize repository | `path`: Where to create repository (new) |
| `git_commit` | Commit changes | `path`: File or directory<br>`message`: Descriptive commit message (recommended) |
| `git_log` | View commit history | `path`: File path<br>`max_count`: Number of commits (new) |
| `git_show` | View file at commit | `path`: File path<br>`commit_id`: Commit reference (new) |
| `git_diff` | Compare versions | `path`: File path<br>`commit1`: Base commit<br>`commit2`: Compare commit (new) |
| `git_revert` | Restore previous version | `path`: File path<br>`commit_id`: Target commit (new) |
| `git_status` | Show repository status | `path`: Repository path (new) |
| `git_branch_list` | List all branches | `path`: Repository path (new) |
| `git_branch_create` | Create a new branch | `path`: Repository path<br>`branch_name`: Name for new branch (new) |
| `git_branch_switch` | Switch to branch | `path`: Repository path<br>`branch_name`: Target branch (new) |

## Installation & Setup

### Quick Start with UV

```bash
# Install UV (if needed)
  # For macOS/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  
  # For Windows PowerShell
  powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"

# Clone the repository
git clone https://github.com/yourusername/fileops-mcp.git
cd fileops-mcp

# Set up environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Test in development mode
uv run src/main.py

# Or run with specific options
uv run src/main.py --working-dir /path/to/dir --read-only
```

### Alternative with pip

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from PyPI
pip install fileops-mcp

# Or install locally
pip install -e .

# Test the server
python -m src.main
```

### Claude Desktop Configuration

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Roaming\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "fileops": {
      "command": "uv",
      "args": [
        "--directory",
        "Z:/Claude/mcp-server/fileops-mcp",
        "run",
        "src/main.py"
      ],
      "env": {
        "WORKING_DIR": "Z:/Claude/mcp-server/fileops-mcp/working-dir",
        "READ_ONLY": "false",
        "GIT_ENABLED": "true",
        "GIT_AUTO_COMMIT": "true"
      }
    }
  }
}
```

### Using MCP CLI for Installation

If you have the MCP CLI installed, you can use it to install the server directly:

```bash
# Install in Claude Desktop
uv run mcp install src/main.py --name "FileOps" --env WORKING_DIR="/path/to/dir" --env GIT_ENABLED="true"
```

## Usage Examples

### In Claude Desktop

- "Please create a new file with today's notes at ~/Documents/notes.txt"
- "Show me what files are in my Downloads folder"
- "Read the content of my README.md file and suggest improvements"
- "Read lines 10-50 from my log.txt file to see recent entries"
- "Read both the package.json and tsconfig.json files to understand the project setup"
- "Update my TODO.txt file by replacing 'In Progress' with 'Completed'"
- "Insert a new method in my Python class after the constructor"
- "Generate a file tree view of my project directory"
- "Search for all Python files in my project"
- "Find all occurrences of 'TODO' in my project files"
- "Copy my config.json file to config.backup.json"
- "Move my draft.txt file to final/published.txt"
- "Move all my .log files from temp/ to archive/ directory"
- "Initialize a Git repository in my project folder" (new)
- "Show me the commit history for main.py" (new)
- "Compare the current version of config.json with the previous version" (new)
- "Revert README.md to the version from 2 commits ago" (new)
- "List all branches in my repository" (new)
- "Create a new branch called 'feature-login'" (new)
- "Switch to the 'develop' branch" (new)

## Git Integration Features

The new Git integration allows you to:

1. **Track Changes**: Every file modification is automatically committed (optional)
2. **View History**: See who changed what and when
3. **Compare Versions**: See differences between file versions
4. **Restore Previous Versions**: Revert files to earlier states
5. **Manage Repositories**: Initialize, commit, and check status
6. **Work with Branches**: Create branches for different features or versions
7. **Switch Between Branches**: Change your working branch to isolate changes
8. **Use Custom Commit Messages**: Add descriptive commit messages that are automatically formatted with a standardized prefix: `[operation] path: your_message`

Git branching enables you to:
- Work on multiple features simultaneously without interference
- Create isolated environments for testing
- Maintain different versions of your files
- Keep the main branch stable while developing in feature branches

By default, Git operations will automatically commit changes, but this can be disabled with `--disable-auto-commit`.

## Configuration Options

You can configure the server using:

### Environment Variables
- `WORKING_DIR`: Directory to allow access to (default: current directory)
- `READ_ONLY`: Set to "true" to disable all write operations (default: "false")
- `HIDE_DOT_FILES`: Set to "false" to show hidden files (default: "true")
- `MAX_DEPTH`: Maximum depth for directory traversal (default: 5, max: 10)
- `MAX_RESULTS`: Maximum results for search operations (default: 100, max: 1000)
- `GIT_ENABLED`: Set to "false" to disable Git functionality (default: "true")
- `GIT_AUTO_COMMIT`: Set to "false" to disable automatic commits (default: "true")
- `GIT_USERNAME`: Username for Git commits (default: "FileOps MCP")
- `GIT_EMAIL`: Email for Git commits (default: "fileops-mcp@no-reply.local")

### Command Line Arguments
```bash
# Run with specific options
uv run src/main.py --working-dir /path/to/dir --read-only --max-depth 3 --disable-auto-commit
```

### Configuration File
Create a JSON file with your settings:
```json
{
  "working_dir": "/path/to/dir",
  "read_only": true,
  "hide_dot_files": true,
  "max_depth": 3,
  "max_results": 50,
  "git_enabled": true,
  "git_auto_commit": false,
  "git_username": "Claude User",
  "git_email": "claude@example.com"
}
```

Then run with:
```bash
uv run src/main.py --config /path/to/config.json
```

## Development

Contributions are welcome! To set up a development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/fileops-mcp.git
cd fileops-mcp

# Create a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest
```

## Project Structure

```
fileops-mcp/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Entry point and CLI
│   ├── server.py             # MCP server definition
│   ├── constants.py          # Configuration constants
│   ├── operations/
│   │   ├── __init__.py
│   │   ├── file_ops.py       # File operations
│   │   ├── dir_ops.py        # Directory operations
│   │   ├── search_ops.py     # Search operations
│   │   ├── version_ops.py    # Git operations
│   │   ├── help_ops.py       # Help operations
│   │   └── help_texts.py     # Help text definitions
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── security.py       # Security utilities
│   │   ├── path_utils.py     # Path handling utilities
│   │   ├── git_utils.py      # Git integration utilities
│   │   └── formatters.py     # Output formatting utilities
│   └── resources/
│       ├── __init__.py
│       └── resource_handlers.py  # Resource endpoint handlers
├── tests/                        # Test directory
├── docs/                         # Documentation
└── examples/                     # Example scripts and usage
```

## Troubleshooting

- **Permission errors**: Ensure the server has access to the specified directories
- **Path not allowed**: Check that the path is within the allowed directories
- **Binary file errors**: Only text files can be read or modified
- **File size limits**: Files larger than 10MB cannot be read
- **Search timeouts**: Use more specific patterns for large directories
- **Git errors**: Ensure gitpython is installed and the repository is properly initialized

## Implementation Notes

### Recent Feature Additions

#### insert_in_file Tool (May 2025)

The `insert_in_file` tool provides precise control for inserting content at specific positions within a file. This feature allows Claude to:
- Insert code exactly where it belongs (e.g., adding methods to a class)
- Add content at specific line positions with `after_line` or `before_line`
- Insert content after pattern matches with `after_pattern`
- Maintain proper code structure when adding functionality
- Preserve formatting and context in existing files

Implementation includes:
- Secure validation of all inputs and file operations
- Three flexible positioning options (after line, before line, or after pattern)
- Thorough error handling and guidance
- Comprehensive test suite
- Atomic file operations with rollback capability
- Git integration for version control

```python
# Example usage
result = await fileops(
    operation="insert_in_file",
    path="src/myclass.py",
    content="    def new_method(self):\n        return 'Hello World'\n",
    after_pattern="def __init__"  # Insert after constructor
)
```

#### read_multiple_files Tool (May 2025)

The `read_multiple_files` tool was added to improve efficiency when working with multiple related files. This feature allows Claude to:
- Read multiple files in a single operation
- Analyze related configuration files together
- Process imports and dependencies across files
- Get comprehensive context from multiple sources

Implementation includes:
- Core function in file_ops.py with proper security validation
- Comprehensive test coverage
- Full documentation in help texts and manual
- User-friendly error handling for binary and non-existent files

```python
# Example usage
result = await fileops(
    operation="read_multiple_files", 
    paths=["package.json", "tsconfig.json", "README.md"]
)
```


## License

MIT License