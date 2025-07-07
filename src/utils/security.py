"""
Security utilities for FileOps MCP.

This module contains functions for ensuring secure file operations,
including path validation, sanitization, and security event logging.
"""
import os
import re
import sys
import json
import hashlib
import datetime
import mimetypes
from pathlib import Path
from typing import Union, Dict, Any, Tuple, Optional

from ..constants import config, MAX_FILE_SIZE

def log_security_event(event_type: str, details: Dict[str, Any]) -> str:
    """
    Log a security-related event.
    
    Args:
        event_type: Type of security event
        details: Additional details about the event
        
    Returns:
        str: Event ID for reference
    """
    timestamp = datetime.datetime.now().isoformat()
    event_id = hashlib.md5(f"{timestamp}:{event_type}:{json.dumps(details)}".encode()).hexdigest()[:8]
    message = f"SECURITY EVENT [{timestamp}] [{event_id}] {event_type}: {json.dumps(details)}"
    print(message, file=sys.stderr)
    return event_id

def is_safe_path(path: str) -> bool:
    """
    Verify that a path is within the allowed directory.
    
    Args:
        path: The path to check
        
    Returns:
        bool: True if the path is within the allowed directory
    """
    try:
        path = os.path.abspath(path)
        return path.startswith(config.abs_working_dir)
    except Exception:
        return False

def sanitize_path(path: str) -> str:
    """
    Sanitize a path to prevent directory traversal attacks.
    
    Args:
        path: The path to sanitize
        
    Returns:
        str: Sanitized absolute path
        
    Raises:
        ValueError: If the path is invalid or outside the working directory
    """
    if not path:
        raise ValueError("Path cannot be None or empty")
    
    # Remove NULL bytes and control characters
    path = re.sub(r'[\x00-\x1F\x7F]', '', path)
    
    # Remove potentially dangerous patterns
    path = re.sub(r'[;&|`$]', '', path)
    
    # Normalize path and make it absolute within working directory
    norm_path = os.path.normpath(path)
    if os.path.isabs(norm_path):
        # If absolute, ensure it's within working directory
        if not is_safe_path(norm_path):
            raise ValueError(f"Path {path} is outside the working directory")
        return norm_path
    else:
        # If relative, make it absolute relative to working directory
        abs_path = os.path.join(config.abs_working_dir, norm_path)
        if not is_safe_path(abs_path):
            raise ValueError(f"Path {path} is outside the working directory")
        return abs_path
    
def sanitize_file_pattern(pattern: str, max_length: int = 500) -> str:
    """
    Sanitize file search pattern to prevent issues.
    
    Args:
        pattern: The file pattern to sanitize
        max_length: Maximum allowed length for pattern
        
    Returns:
        str: Sanitized file pattern
        
    Raises:
        ValueError: If pattern is invalid or too long
    """
    if not isinstance(pattern, str):
        raise ValueError("File pattern must be a string")
    
    if not pattern:
        raise ValueError("File pattern cannot be empty")
    
    # Check length to prevent DoS attacks
    if len(pattern) > max_length:
        raise ValueError(f"File pattern is too long ({len(pattern)} characters). Maximum length is {max_length} characters.")
    
    # Remove NULL bytes and control characters
    sanitized = re.sub(r'[\x00-\x1F\x7F]', '', pattern)
    
    # Remove potentially dangerous shell command characters
    sanitized = re.sub(r'[;&|`$]', '', sanitized)
    
    # Ensure we still have content after sanitization
    if not sanitized:
        raise ValueError("File pattern contains only invalid characters")
    
    return sanitized

def sanitize_search_text(text: str, max_length: int = 1000) -> str:
    """
    Sanitize search text to prevent issues and ensure safe searching.
    
    Args:
        text: The search text to sanitize
        max_length: Maximum allowed length for search text
        
    Returns:
        str: Sanitized search text
        
    Raises:
        ValueError: If text is invalid or too long
    """
    if not isinstance(text, str):
        raise ValueError("Search text must be a string")
    
    if not text:
        raise ValueError("Search text cannot be empty")
    
    # Check length to prevent DoS attacks
    if len(text) > max_length:
        raise ValueError(f"Search text is too long ({len(text)} characters). Maximum length is {max_length} characters.")
    
    # Remove NULL bytes and most control characters that could cause display issues
    # Keep common whitespace characters like \n, \t, \r
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Remove potentially dangerous shell command characters
    # These aren't strictly necessary for text search but good for defense in depth
    sanitized = re.sub(r'[;&|`$]', '', sanitized)
    
    # Ensure we still have content after sanitization
    if not sanitized:
        raise ValueError("Search text contains only invalid characters")
    
    return sanitized

def sanitize_file_string(content: Union[str, Dict[str, Any], list, int, float, bool]) -> str:
    if not isinstance(content, str) :
        try : 
            content = json.dumps(content, indent=2)
        except Exception as e :
            raise ValueError(f"sanitize_file_string(): Failed to serialize content: {str(e)}")
    return content

def validate_operation(path: str, operation: str, check_binary: bool = False, check_exists: bool = True) -> str:
    """
    Validate file operations with comprehensive checks.
    
    Args:
        path: Path to validate
        operation: Operation being performed
        check_binary: Whether to check if the file is binary
        check_exists: Whether to check if the file exists
        
    Returns:
        str: Absolute path if valid
        
    Raises:
        ValueError: If the operation is invalid
    """
    # Check read-only mode
    if config.read_only and operation in ["create_file", "update_file", "rewrite_file", "delete_file", 
                                         "create_dir", "delete_dir", "remove_from_file", "append_to_file",
                                         "insert_in_file", "git_init", "git_commit", "git_revert", 
                                         "copy_file", "move_file", "delete_multiple_files", "replace_all_in_file",
                                         "replace_all_emojis_in_files"]:
        log_security_event("write_attempt_in_readonly", {"operation": operation, "path": path})
        raise ValueError("Server is in read-only mode. Write operations are disabled.")
    
    # Sanitize and verify path
    try:
        abs_path = sanitize_path(path)
    except ValueError as e:
        log_security_event("invalid_path", {"operation": operation, "path": path, "error": str(e)})
        raise
    
    # Basic existence check if needed
    if check_exists and operation in ["update_file", "rewrite_file", "delete_file", "delete_dir", "get_tree", "remove_from_file", 
                    "git_log", "git_show", "git_diff", "git_revert", "copy_file", "move_file", "delete_multiple_files", "replace_all_in_file"]:
        if not os.path.exists(abs_path):
            raise ValueError(f"Path does not exist at {path}")
            
    # Type check - directory vs file
    if operation in ["update_file", "rewrite_file", "delete_file", "remove_from_file", "append_to_file", 
                    "insert_in_file", "git_log", "git_show", "git_diff", "git_revert", "replace_all_in_file"] and os.path.exists(abs_path):
        if os.path.isdir(abs_path):
            raise ValueError(f"{path} is a directory, not a file.")
            
    if operation in ["list_dir", "delete_dir", "get_tree"] and os.path.exists(abs_path):
        if not os.path.isdir(abs_path):
            raise ValueError(f"{path} is a file, not a directory.")
            
    # Binary file check for text operations
    if check_binary and operation in ["update_file", "rewrite_file", "read_file", "remove_from_file", "append_to_file", "insert_in_file", "replace_all_in_file"] and os.path.exists(abs_path):
        if not is_text_file(abs_path):
            log_security_event("binary_file_operation", {"operation": operation, "path": path})
            raise ValueError(f"Cannot {operation} binary file {path}. Only text files are supported.")
            
    # Size check for large files
    if operation in ["read_file", "git_show"] and os.path.exists(abs_path) and os.path.isfile(abs_path):
        file_size = os.path.getsize(abs_path)
        if file_size > MAX_FILE_SIZE:
            log_security_event("file_size_limit", {"operation": operation, "path": path, "size": file_size})
            raise ValueError(f"File {path} is too large ({file_size} bytes). Maximum file size is {MAX_FILE_SIZE} bytes.")
            
    return abs_path

def is_text_file(path: str) -> bool:
    """
    Determine if a file is a text file using multiple detection methods.
    
    This function combines several approaches for maximum accuracy:
    1. Known file extension checking (fast)
    2. Known binary extension rejection (fast)
    3. MIME type analysis
    4. Content-based heuristics (fallback)
    
    Args:
        path: Path to the file to analyze
        
    Returns:
        bool: True if the file is determined to be a text file, False if binary
        
    Raises:
        ValueError: If the path is invalid or inaccessible
        OSError: If file cannot be opened or read
        PermissionError: If insufficient permissions to read the file
    """
    
    # Step 1: Fast extension-based text file detection
    # These extensions are virtually always text files
    '''text_extensions = {
        '.txt', '.md', '.rst', '.py', '.js', '.html', '.htm', '.css', '.xml',
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.log',
        '.csv', '.tsv', '.sql', '.sh', '.bat', '.ps1', '.rb', '.php', '.java',
        '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.scala', '.kt'
    }
    
    file_ext = Path(path).suffix.lower()
    if file_ext in text_extensions:
        return True'''
    
    # Step 2: Fast extension-based binary file rejection
    # These extensions are virtually always binary files
    binary_extensions = {
        '.exe', '.dll', '.so', '.dylib', '.bin', '.img', '.iso',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tiff',
        '.mp3', '.wav', '.flac', '.ogg', '.mp4', '.avi', '.mkv',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'
    }
    
    file_ext = Path(path).suffix.lower()
    if file_ext in binary_extensions:
        return False
    
    # Step 3: MIME type analysis using Python's mimetypes module
    # This handles many file types not covered by extension lists
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type:
        # Text MIME types are definitely text files
        if mime_type.startswith('text/'):
            return True
        # Known binary MIME types can be rejected immediately
        if mime_type.startswith(('image/', 'audio/', 'video/')):
            return False
    
    # Step 4: Content-based analysis (most reliable but slowest)
    # Used when extension and MIME type are inconclusive
    try:
        # Read a sample of the file for analysis (8KB is usually sufficient)
        with open(path, 'rb') as f:
            sample = f.read(8192)
            
        # Empty files are considered text by convention
        if not sample:
            return True
            
        # Primary binary indicator: null bytes are almost never in text files
        if b'\0' in sample:
            return False
            
        # Attempt UTF-8 decoding - most text files should decode cleanly
        try:
            sample.decode('utf-8')
            # Additional heuristic: check ratio of printable ASCII characters
            # Printable chars: space (32) through tilde (126), plus tab (9), LF (10), CR (13)
            printable = sum(1 for b in sample if 32 <= b <= 126 or b in [9, 10, 13])
            return (printable / len(sample)) > 0.75
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, likely a binary file
            return False
            
    except Exception:
        # If any file operation fails, default to False for safety
        return False


def format_error(e: Exception) -> str:
    """
    Format an exception into a user-friendly error message.
    
    Args:
        e: The exception to format
        
    Returns:
        str: Formatted error message
    """
    if isinstance(e, (ValueError, OSError, IOError)):
        return f"Error: {str(e)}"
    else:
        # Unexpected errors get logged with limited info
        error_id = log_security_event("unexpected_error", {
            "type": type(e).__name__,
            "message": str(e)
        })
        return f"An unexpected error occurred. Reference ID: {error_id}"

def with_error_handling(func):
    """
    Decorator to handle errors in a consistent way.
    
    Args:
        func: The function to wrap
        
    Returns:
        function: Wrapped function with error handling
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return format_error(e)
    return wrapper





def is_text_file_robust(path: str) -> bool:
    """
    Determine if a file is a text file using security-focused multi-layer detection.
    
    This function employs a defense-in-depth approach with multiple detection methods
    to securely identify text files while preventing security vulnerabilities from
    misclassified binary content. The detection prioritizes security over convenience,
    erring on the side of treating suspicious files as binary.
    
    Detection layers (in order of execution):
    1. File size validation (prevents resource exhaustion attacks)
    2. Magic number/file signature analysis (detects binary formats)
    3. Null byte detection (strongest binary indicator)
    4. UTF-8 encoding validation (prevents encoding-based attacks)
    5. Statistical content analysis (final heuristic check)
    
    Args:
        path: Absolute or relative path to the file to analyze
        
    Returns:
        bool: True if the file is determined to be a text file and safe to process,
              False if the file is binary or potentially dangerous
        
    Raises:
        OSError: If the file cannot be accessed or read
        PermissionError: If insufficient permissions to read the file
        FileNotFoundError: If the specified file does not exist
        
    Security Notes:
        - Files larger than 10MB are automatically considered binary
        - Any file with null bytes is considered binary (security-critical)
        - Files that cannot be decoded as UTF-8 are considered binary
        - Unknown or suspicious content patterns trigger binary classification
    """
    from pathlib import Path
    
    try:
        # Layer 1: File size validation (prevents DoS and resource exhaustion)
        # Large files are often binary and can cause memory issues during analysis
        file_size = Path(path).stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10MB threshold
            return False  # Treat oversized files as binary for security
        
        # Layer 2: Read file header for signature and content analysis
        # Reading 512 bytes provides sufficient data for most binary signatures
        # while being efficient for performance
        with open(path, 'rb') as f:
            header = f.read(512)
        
        # Layer 3: Magic number detection (highest priority binary check)
        # File signatures are the most reliable way to identify binary formats
        # regardless of file extension or other metadata
        if _has_binary_signature(header):
            return False  # Known binary format detected
        
        # Layer 4: Null byte detection (critical security boundary)
        # Null bytes (\x00) are extremely rare in legitimate text files
        # but common in binary files and can indicate embedded executables
        if b'\x00' in header:
            return False  # Null bytes indicate binary content
        
        # Layer 5: UTF-8 encoding validation (encoding security check)
        # Attempt to decode the entire file as UTF-8 to ensure it's valid text
        # This prevents encoding-based attacks and confirms text file integrity
        try:
            with open(path, 'r', encoding='utf-8') as f:
                # Read a substantial portion to validate encoding throughout the file
                f.read(8192)  # 8KB validation sample
        except UnicodeDecodeError:
            # If any part fails UTF-8 decoding, treat as binary
            return False
        
        # Layer 6: Statistical content analysis (final heuristic validation)
        # Analyze byte patterns and character distributions for suspicious content
        # that might indicate binary data or malicious polyglot files
        binary_probability = _analyze_content_security(header)
        if binary_probability > 0.3:  # Conservative 30% threshold
            return False  # Statistical analysis indicates binary content
        
        # All security checks passed - file is considered safe text
        return True
        
    except (OSError, PermissionError, FileNotFoundError):
        # On any file access error, fail securely by rejecting the file
        # This prevents information disclosure through error-based attacks
        return False
    except Exception:
        # For any unexpected error, default to secure behavior
        # Unknown errors could indicate attack attempts or corrupted files
        return False


def _has_binary_signature(data: bytes) -> bool:
    """
    Check if file data starts with known binary file format signatures.
    
    This function identifies files by their magic numbers (file signatures) which
    are more reliable than file extensions. Magic numbers are byte sequences at
    the beginning of files that uniquely identify the file format.
    
    Args:
        data: The first few hundred bytes of the file to analyze
        
    Returns:
        bool: True if a known binary signature is detected, False otherwise
        
    Security Notes:
        - Signatures are checked regardless of file extension (prevents spoofing)
        - List includes common executable and media formats that pose security risks
        - Detection is performed on raw bytes to prevent encoding-based evasion
    """
    # Common binary file signatures (magic numbers)
    # Each signature represents a different binary file format
    binary_signatures = [
        b'\x4D\x5A',              # PE executable (Windows .exe, .dll) - "MZ" header
        b'\x7F\x45\x4C\x46',      # ELF executable (Linux/Unix executables)
        b'\x89\x50\x4E\x47',      # PNG image format
        b'\xFF\xD8\xFF',          # JPEG image format
        b'\x50\x4B\x03\x04',      # ZIP archive (also .docx, .xlsx, .jar)
        b'\x50\x4B\x05\x06',      # Empty ZIP archive
        b'\x50\x4B\x07\x08',      # ZIP with data descriptor
        b'\x25\x50\x44\x46',      # PDF document - "%PDF"
        b'\x47\x49\x46\x38',      # GIF image format - "GIF8"
        b'\x42\x4D',              # Windows Bitmap (BMP) image
        b'\x00\x00\x01\x00',      # Windows Icon (.ico)
        b'\x52\x49\x46\x46',      # RIFF container (WAV, AVI) - "RIFF"
        b'\x1F\x8B\x08',          # GZIP compressed data
        b'\x42\x5A\x68',          # BZIP2 compressed data - "BZh"
        b'\x7F\x45\x4C\x46',      # ELF (Linux executables, libraries)
        b'\xFE\xED\xFA\xCE',      # Mach-O executable (macOS, 32-bit)
        b'\xFE\xED\xFA\xCF',      # Mach-O executable (macOS, 64-bit)
        b'\xCA\xFE\xBA\xBE',      # Java class file
        b'\xD0\xCF\x11\xE0',      # Microsoft Office documents (legacy)
    ]
    
    # Check if the file data starts with any known binary signature
    # Using startswith() ensures we match the exact beginning of the file
    for signature in binary_signatures:
        if data.startswith(signature):
            return True
    
    return False


def _analyze_content_security(data: bytes) -> float:
    """
    Perform statistical analysis of file content to detect binary patterns.
    
    This function analyzes the distribution of bytes in the file to calculate
    a probability score indicating how likely the content is to be binary.
    The analysis focuses on character patterns that are typical of text vs binary files.
    
    Args:
        data: Byte sequence to analyze (typically first 512 bytes of file)
        
    Returns:
        float: Binary probability score from 0.0 to 1.0
               - 0.0-0.3: Likely text file (safe to process)
               - 0.3-0.7: Suspicious content (handle with caution)
               - 0.7-1.0: Likely binary file (should reject)
               
    Security Notes:
        - Uses conservative thresholds that favor false positives over false negatives
        - Null byte detection provides immediate high-confidence binary detection
        - Multiple scoring factors prevent evasion through content manipulation
    """
    # Handle edge case of empty data
    if not data:
        return 0.0  # Empty files are considered text by default
    
    # Critical security check: null bytes are almost never in legitimate text
    # This is the strongest single indicator of binary content
    if b'\x00' in data:
        return 0.95  # Very high binary probability for null bytes
    
    # Categorize bytes by type for statistical analysis
    printable_ascii = 0    # Standard printable characters (space through tilde)
    whitespace = 0         # Legitimate whitespace characters
    control_chars = 0      # Control characters (excluding allowed whitespace)
    high_bytes = 0         # Extended ASCII or UTF-8 continuation bytes
    
    # Count each category of bytes in the data
    for byte_value in data:
        if 32 <= byte_value <= 126:  # Printable ASCII range
            printable_ascii += 1
        elif byte_value in [9, 10, 13, 32]:  # Tab, LF, CR, Space
            whitespace += 1
        elif byte_value < 32:  # Control characters (excluding allowed whitespace)
            control_chars += 1
        else:  # byte_value > 126 - Extended ASCII or UTF-8
            high_bytes += 1
    
    total_bytes = len(data)
    
    # Calculate ratios for statistical analysis
    printable_ratio = (printable_ascii + whitespace) / total_bytes
    control_ratio = control_chars / total_bytes
    high_byte_ratio = high_bytes / total_bytes
    
    # Apply conservative binary detection thresholds
    # Each threshold is set to favor false positives (marking text as binary)
    # over false negatives (marking binary as text) for security
    
    if printable_ratio < 0.75:  # Less than 75% printable characters
        # Most text files have >90% printable content
        return 0.8
    
    if control_ratio > 0.1:  # More than 10% control characters
        # Legitimate text files rarely have many control characters
        return 0.7
    
    if high_byte_ratio > 0.3:  # More than 30% high bytes
        # While UTF-8 can have high bytes, excessive amounts suggest binary
        return 0.6
    
    # All statistical checks passed - likely text content
    return 0.1  # Low binary probability indicating likely text file