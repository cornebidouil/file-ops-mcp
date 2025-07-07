"""
File operations for FileOps MCP.

This module contains tools for file operations such as reading multiple files,
creating, updating, deleting, copying, and moving files.
"""
import os
import time
import json
from typing import Dict, Any, Optional, Union

from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

from ..constants import config, MAX_FILE_SIZE
from ..utils.security import validate_operation, log_security_event, is_text_file, with_error_handling, sanitize_file_string
from ..utils.path_utils import generate_checksum
from ..utils.formatters import format_file_contents
from ..utils.git_utils import auto_commit_changes, GitError

def register_file_operations(mcp: FastMCP) -> None:
    """
    Register file operations with the MCP server.
    
    Args:
        mcp: The MCP server instance
    """
    
    @with_error_handling
    @mcp.tool()
    async def copy_file(source_path: str, dest_path: str, commit_message: str = None) -> str:
        """
        Copy a file from source path to destination path.
        
        Args:
            source_path: Path to the source file
            dest_path: Path to the destination file
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If file copy fails
        """
        # Validate source and destination paths
        source_abs_path = validate_operation(source_path, "copy_file", check_binary=False)
        dest_abs_path = validate_operation(dest_path, "create_file", check_exists=False)
        
        # Check if source is a file
        if not os.path.isfile(source_abs_path):
            raise ValueError(f"Source {source_path} is not a file")
            
        # Check if destination exists
        if os.path.exists(dest_abs_path):
            raise ValueError(f"Destination {dest_path} already exists. Use rewrite_file operation to replace it.")
            
        # Ensure destination directory exists
        dest_dir = os.path.dirname(dest_abs_path)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        # Get source file info for verification
        source_size = os.path.getsize(source_abs_path)
        source_checksum = generate_checksum(source_abs_path)
        
        # Use atomic copy operation with proper error handling
        temp_path = f"{dest_abs_path}.tmp.{os.getpid()}.{int(time.time())}"
        try:
            # Read source file
            with open(source_abs_path, 'rb') as src:
                # Write to temporary destination
                with open(temp_path, 'wb') as dst:
                    dst.write(src.read())
            # Atomic rename to destination
            os.replace(temp_path, dest_abs_path)
        except Exception as e:
            # Clean up temp file if copy failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise ValueError(f"Failed to copy file: {str(e)}")
            
        # Get destination file info for verification
        dest_size = os.path.getsize(dest_abs_path)
        dest_checksum = generate_checksum(dest_abs_path)
        
        # Verify copy was successful
        if source_size != dest_size or source_checksum != dest_checksum:
            # Delete the destination file as it may be corrupt
            try:
                os.remove(dest_abs_path)
            except:
                pass
            raise ValueError(f"Copy verification failed: checksums do not match")
            
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(dest_abs_path, "copy_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
            
        return f"Successfully copied file: {source_path} to {dest_path}\nSize: {dest_size} bytes\nChecksum: {dest_checksum}{commit_result}"
    
    @with_error_handling
    @mcp.tool()
    async def copy_multiple_files(source_paths: list[str], dest_paths: list[str] = None, dest_dir: str = None, commit_message: str = None) -> str:
        """
        Copy multiple files from source paths to destination paths or directory.
        
        Args:
            source_paths: List of paths to the source files
            dest_paths: List of destination file paths (must match length of source_paths if provided)
            dest_dir: Destination directory (alternative to dest_paths - all files copied here with same names)
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success and failure summary
            
        Raises:
            ValueError: If parameter validation fails
        """
        if not source_paths:
            raise ValueError("No source file paths provided")
        
        # Validate that exactly one destination method is provided
        if dest_paths is None and dest_dir is None:
            raise ValueError("Either dest_paths or dest_dir must be provided")
        if dest_paths is not None and dest_dir is not None:
            raise ValueError("Only one of dest_paths or dest_dir can be provided, not both")
        
        # If dest_paths is provided, validate length matches source_paths
        if dest_paths is not None and len(dest_paths) != len(source_paths):
            raise ValueError(f"Length of dest_paths ({len(dest_paths)}) must match length of source_paths ({len(source_paths)})")
        
        # If dest_dir is provided, validate it's a valid directory path and create destination paths
        if dest_dir is not None:
            dest_dir_abs = validate_operation(dest_dir, "create_dir", check_exists=False)
            # Create destination directory if it doesn't exist
            if not os.path.exists(dest_dir_abs):
                os.makedirs(dest_dir_abs)
            elif not os.path.isdir(dest_dir_abs):
                raise ValueError(f"Destination path {dest_dir} exists but is not a directory")
            
            # Generate dest_paths from dest_dir and source filenames
            dest_paths = []
            for source_path in source_paths:
                filename = os.path.basename(source_path)
                dest_paths.append(os.path.join(dest_dir, filename))
        
        # Track results
        successful_copies = []
        failed_copies = []
        copied_files = []  # For Git commit tracking
        
        # Process each file copy
        for i, (source_path, dest_path) in enumerate(zip(source_paths, dest_paths)):
            try:
                # Validate source and destination paths
                source_abs_path = validate_operation(source_path, "copy_file", check_binary=False)
                dest_abs_path = validate_operation(dest_path, "create_file", check_exists=False)
                
                # Check if source is a file
                if not os.path.isfile(source_abs_path):
                    failed_copies.append(f"{source_path} -> {dest_path} (source is not a file)")
                    continue
                    
                # Check if destination exists
                if os.path.exists(dest_abs_path):
                    failed_copies.append(f"{source_path} -> {dest_path} (destination already exists)")
                    continue
                    
                # Ensure destination directory exists
                dest_dir_path = os.path.dirname(dest_abs_path)
                if dest_dir_path and not os.path.exists(dest_dir_path):
                    os.makedirs(dest_dir_path)
                    
                # Get source file info for verification
                source_size = os.path.getsize(source_abs_path)
                source_checksum = generate_checksum(source_abs_path)
                
                # Use atomic copy operation with proper error handling
                temp_path = f"{dest_abs_path}.tmp.{os.getpid()}.{int(time.time())}"
                try:
                    # Read source file
                    with open(source_abs_path, 'rb') as src:
                        # Write to temporary destination
                        with open(temp_path, 'wb') as dst:
                            dst.write(src.read())
                    # Atomic rename to destination
                    os.replace(temp_path, dest_abs_path)
                except Exception as e:
                    # Clean up temp file if copy failed
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                    failed_copies.append(f"{source_path} -> {dest_path} (failed to copy: {str(e)})")
                    continue
                    
                # Get destination file info for verification
                dest_size = os.path.getsize(dest_abs_path)
                dest_checksum = generate_checksum(dest_abs_path)
                
                # Verify copy was successful
                if source_size != dest_size or source_checksum != dest_checksum:
                    # Delete the destination file as it may be corrupt
                    try:
                        os.remove(dest_abs_path)
                    except:
                        pass
                    failed_copies.append(f"{source_path} -> {dest_path} (verification failed: checksums do not match)")
                    continue
                
                successful_copies.append(f"{source_path} -> {dest_path}")
                copied_files.append(dest_abs_path)
                
            except Exception as e:
                failed_copies.append(f"{source_path} -> {dest_path} (error: {str(e)})")
        
        # Prepare result summary
        total_files = len(source_paths)
        success_count = len(successful_copies)
        failure_count = len(failed_copies)
        
        result_lines = [f"Copy operation completed: {success_count}/{total_files} files copied successfully"]
        
        if successful_copies:
            result_lines.append("\nSuccessfully copied files:")
            for copy in successful_copies:
                result_lines.append(f"  ✓ {copy}")
        
        if failed_copies:
            result_lines.append(f"\nFailed to copy {failure_count} files:")
            for copy in failed_copies:
                result_lines.append(f"  ✗ {copy}")
        
        # Auto-commit if enabled and there were successful copies
        if copied_files:
            commit_result = ""
            try:
                # Use the first copied file's directory for Git operations
                commit_path = os.path.dirname(copied_files[0]) if copied_files else "."
                commit = auto_commit_changes(commit_path, "copy_multiple_files", commit_message)
                if commit:
                    commit_result = f"\n{commit}"
            except GitError as e:
                commit_result = f"\nNote: {str(e)}"
            
            if commit_result:
                result_lines.append(commit_result)
        
        return "\n".join(result_lines)

    @with_error_handling
    @mcp.tool()
    async def replace_all_emojis_in_files(file_paths: list[str], emoji_mapping: Dict[str, str] = None, commit_message: str = None) -> str:
        """
        Replace all emoji occurrences in multiple text files with text representations.
        
        This tool processes multiple files to replace Unicode emoji characters with
        their text equivalents, helping to resolve encoding issues and improve
        text compatibility across different systems.
        
        Default Emoji Mapping (125+ patterns - expanded from docs/missing_emoji_mappings.md):
        
        Status & Actions: 🔧 -> [API], ⚡ -> [FAST], 🚀 -> [PERF], 📦 -> [PKG], 🎯 -> [TARGET], 
        🔒 -> [SEC], 💡 -> [TIP], 🔥 -> [FIRE], 💪 -> [STRONG], 🧪 -> [TEST]
        
        Files & Data: 📁 -> [DIR], 📂 -> [FOLDER], 📄 -> [FILE], 📝 -> [NOTE], 📋 -> [LIST], 
        📖 -> [BOOK], 📊 -> [CHART], 📈 -> [CHART], 📉 -> [CHART]
        
        Technology & Devices: 💻 -> [COMP], 🖥️ -> [DESKTOP], 📱 -> [MOBILE], 🐳 -> [DOCKER], 
        🌐 -> [NET], 📶 -> [NET], 🔌 -> [PLUG], ⚙️ -> [GEAR]
        
        Results & Status: ✅ -> [PASS], ❌ -> [FAIL], ⚠️ -> [WARN], ℹ️ -> [INFO], 
        ❓ -> [QUESTION], ❗ -> [EXCLAIM2], 🚨 -> [ERR], 🎉 -> [SUCCESS]
        
        Intelligence & Processing: 🧠 -> [MEMORY], 🧮 -> [COMPUTE], 🤖 -> [BOT], 🔮 -> [PREDICT]
        
        Connection & Flow: 🔗 -> [LINK], 🔄 -> [CYCLE], 🔁 -> [REPEAT], 🔂 -> [REPEAT_ONE], 
        🔃 -> [VERTICAL]
        
        Places & Environment: 🏠 -> [HOST], 🏆 -> [AWARD], 🎪 -> [STRATEGY], 🏢 -> [OFFICE], 
        🏭 -> [FACTORY]
        
        Tools & Objects: 🧹 -> [CLEANUP], 🗑️ -> [GARBAGE], ✍️ -> [WRITE], 🖊️ -> [PEN], 
        🔨 -> [BUILD]
        
        Programming Languages: 🐼 -> [PANDAS], 🐍 -> [PYTHON], 🐧 -> [LINUX], 🦀 -> [RUST]
        
        Navigation: ➡️ -> [RIGHT], ⬅️ -> [LEFT], ⬆️ -> [UP], ⬇️ -> [DOWN]
        
        Communication: 💬 -> [COMMENT], 💭 -> [THOUGHT], 🗨️ -> [SPEAK], 📞 -> [PHONE], 
        📧 -> [EMAIL]
        
        And 90+ more comprehensive patterns for complete emoji coverage!
        
        Args:
            file_paths: List of paths to the text files to process
            emoji_mapping: Optional custom emoji mapping dictionary that will be merged 
                          with the default mapping. Any emoji in this dictionary will 
                          override the default replacement for that emoji, and new 
                          emojis will be added to the mapping. The default mapping 
                          remains intact for all other emojis.
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Summary of processing results including files processed, 
                 total replacements made, and any errors encountered
                 
        Raises:
            ValueError: If file paths are invalid, files are binary, or processing fails
            
        Security Notes:
            - Only processes text files (binary files are rejected for security)
            - Validates all file paths to prevent directory traversal attacks
            - Uses atomic file operations to prevent data corruption
            - Maintains file checksums for integrity verification
        """
        # Validate input parameters
        if not file_paths:
            raise ValueError("No file paths provided")
        
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list of strings")
        
        # Default comprehensive emoji mapping based on docs/fix_emojis.py
        default_emoji_mapping = {
            # Basic status indicators
            '\U0001f527': '[API]',      # 🔧 wrench
            '\U000026a1': '[FAST]',     # ⚡ lightning
            '\U0001f680': '[PERF]',     # 🚀 rocket
            '\U0001f4e6': '[PKG]',      # 📦 package
            '\U0001f4ca': '[CHART]',    # 📊 chart
            '\U0001f4c8': '[CHART]',    # 📈 chart increasing
            '\U0001f4c9': '[CHART]',    # 📉 chart decreasing
            '\U0001f3af': '[TARGET]',   # 🎯 target
            '\U0001f512': '[SEC]',      # 🔒 lock
            '\U0001f30d': '[GLOBAL]',   # 🌍 globe
            '\U0001f30e': '[WEB]',      # 🌎 globe
            '\U0001f4f6': '[NET]',      # 📶 network
            '\U0001f310': '[NET]',      # 🌐 network
            '\U0001f4a1': '[TIP]',      # 💡 bulb
            '\U0001f3c1': '[FINAL]',    # 🏁 checkered flag
            '\U0001f389': '[SUCCESS]',  # 🎉 party
            '\U0001f38a': '[DONE]',     # 🎊 confetti
            '\U0001f40c': '[SLOW]',     # 🐌 snail
            '\U0001f433': '[DOCKER]',   # 🐳 whale
            '\U0001f6e1\ufe0f': '[SHIELD]', # 🛡️ shield
            '\U0001f6e1': '[SHIELD]',   # 🛡 shield
            '\U0001f6a8': '[ERR]',      # 🚨 siren
            '\U0001f50d': '[SEARCH]',   # 🔍 magnifying glass
            '\U0001f514': '[CONN]',     # 🔔 bell
            '\U0001f525': '[FIRE]',     # 🔥 fire
            '\U0001f4aa': '[STRONG]',   # 💪 muscle
            '\U0001f9ea': '[TEST]',     # 🧪 test tube
            '\U0001f4dd': '[NOTE]',     # 📝 memo
            '\U0001f4cb': '[LIST]',     # 📋 clipboard
            '\U0001f4c4': '[FILE]',     # 📄 document
            '\U0001f4c1': '[DIR]',      # 📁 folder
            '\U0001f4c2': '[FOLDER]',   # 📂 open folder
            '\U0001f4d6': '[BOOK]',     # 📖 book
            '\U0001f4bb': '[COMP]',     # 💻 computer
            '\U0001f5a5\ufe0f': '[DESKTOP]', # 🖥️ desktop
            '\U0001f5a5': '[DESKTOP]',  # 🖥 desktop
            '\U0001f4f1': '[MOBILE]',   # 📱 mobile
            '\U000023f1\ufe0f': '[TIMER]', # ⏱️ timer
            '\U000023f1': '[TIMER]',    # ⏱ timer
            '\U0001f552': '[TIME]',     # 🕒 clock
            '\U0001f195': '[NEW]',      # 🆕 new
            '\U0001f199': '[UP]',       # 🆙 up
            '\U0001f19a': '[VS]',       # 🆚 vs
            '\U0001f4a5': '[BOOM]',     # 💥 explosion
            '\U0001f525': '[HOT]',      # 🔥 fire
            '\U00002744\ufe0f': '[COLD]', # ❄️ snowflake
            '\U00002744': '[COLD]',     # ❄ snowflake
            '\U0001f522': '[NUMS]',     # 🔢 numbers
            '\U0001f523': '[SYMBOLS]',  # 🔣 symbols
            '\U0001f524': '[ABC]',      # 🔤 letters
            '\U00002699\ufe0f': '[GEAR]', # ⚙️ gear
            '\U00002699': '[GEAR]',     # ⚙ gear
            '\U00002696\ufe0f': '[BALANCE]', # ⚖️ balance
            '\U00002696': '[BALANCE]',  # ⚖ balance
            '\U0001f4e4': '[OUTBOX]',   # 📤 outbox
            '\U0001f4e5': '[INBOX]',    # 📥 inbox
            '\U0001f4ed': '[EMPTY]',    # 📭 mailbox
            '\U0001f4ec': '[MAIL]',     # 📬 mailbox
            '\U0001f4ea': '[MAILBOX]',  # 📪 closed mailbox
            '\U0001f4e8': '[ENVELOPE]', # 📨 envelope
            '\U0001f194': '[ID]',       # 🆔 ID
            '\U0001f50c': '[PLUG]',     # 🔌 plug
            '\U0001f4de': '[PHONE]',    # 📞 telephone
            '\U0001f4e0': '[FAX]',      # 📠 fax
            '\U0001f4fc': '[VHS]',      # 📼 videocassette
            '\U0001f4fd\ufe0f': '[FILM]', # 📽️ film projector
            '\U0001f4fd': '[FILM]',     # 📽 film projector
            '\U0001f3a5': '[CAMERA]',   # 🎥 movie camera
            '\U0001f4f7': '[PHOTO]',    # 📷 camera
            '\U0001f4f8': '[FLASH]',    # 📸 camera with flash
            '\U0001f50e': '[ZOOM]',     # 🔎 magnifying glass
            '\U0001f50f': '[LOCK]',     # 🔏 lock with pen
            '\U0001f510': '[UNLOCK]',   # 🔐 lock with key
            '\U0001f511': '[KEY]',      # 🔑 key
            '\U0001f513': '[OPEN]',     # 🔓 unlocked
            '\U0001f6aa': '[DOOR]',     # 🚪 door
            '\U0001f4ac': '[COMMENT]',  # 💬 speech balloon
            '\U0001f4ad': '[THOUGHT]',  # 💭 thought balloon
            '\U0001f5e8\ufe0f': '[SPEAK]', # 🗨️ left speech bubble
            '\U0001f5e8': '[SPEAK]',    # 🗨 left speech bubble
            '\U0001f5ef\ufe0f': '[ANGRY]', # 🗯️ right anger bubble
            '\U0001f5ef': '[ANGRY]',    # 🗯 right anger bubble
            '\U0001f4f0': '[NEWS]',     # 📰 newspaper
            '\U0001f4f3': '[VIBRATE]',  # 📳 vibration mode
            '\U0001f4f4': '[SILENT]',   # 📴 mobile phone off
            '\U0001f4f5': '[NO_MOBILE]', # 📵 no mobile phones
            '\U0001f4f6': '[SIGNAL]',   # 📶 antenna bars
            '\U0001f4f7': '[CAMERA2]',  # 📷 camera
            '\U0001f4f9': '[VIDEO]',    # 📹 video camera
            '\U0001f4fa': '[TV]',       # 📺 television
            '\U0001f4fb': '[RADIO]',    # 📻 radio
            '\U0001f4fc': '[TAPE]',     # 📼 videocassette
            '\U0001f50a': '[LOUD]',     # 🔊 speaker high volume
            '\U0001f50b': '[LOW]',      # 🔋 battery
            '\U0001f50c': '[ELECTRIC]', # 🔌 electric plug
            '\U0001f4af': '[100]',      # 💯 hundred points
            
            # Add checkmark and X emojis
            '\u2705': '[PASS]',         # ✅ check mark
            '\u274c': '[FAIL]',         # ❌ cross mark
            '\u26a0\ufe0f': '[WARN]',   # ⚠️ warning
            '\u26a0': '[WARN]',         # ⚠ warning
            '\u2139\ufe0f': '[INFO]',   # ℹ️ information
            '\u2139': '[INFO]',         # ℹ information
            '\u2753': '[QUESTION]',     # ❓ question mark
            '\u2754': '[QUESTION2]',    # ❔ white question mark
            '\u2755': '[EXCLAIM]',      # ❕ white exclamation mark
            '\u2757': '[EXCLAIM2]',     # ❗ exclamation mark
            '\u27a1\ufe0f': '[RIGHT]',  # ➡️ right arrow
            '\u27a1': '[RIGHT]',        # ➡ right arrow
            '\u2b05\ufe0f': '[LEFT]',   # ⬅️ left arrow
            '\u2b05': '[LEFT]',         # ⬅ left arrow
            '\u2b06\ufe0f': '[UP]',     # ⬆️ up arrow
            '\u2b06': '[UP]',           # ⬆ up arrow
            '\u2b07\ufe0f': '[DOWN]',   # ⬇️ down arrow
            '\u2b07': '[DOWN]',         # ⬇ down arrow
            
            # Missing emoji mappings from docs/missing_emoji_mappings.md
            # Brain/Intelligence Category
            '\U0001f9e0': '[MEMORY]',   # 🧠 brain
            '\U0001f9ee': '[COMPUTE]',  # 🧮 abacus
            '\U0001f916': '[BOT]',      # 🤖 robot
            '\U0001f52e': '[PREDICT]',  # 🔮 crystal ball
            
            # Connection/Process Category
            '\U0001f517': '[LINK]',     # 🔗 link
            '\U0001f504': '[CYCLE]',    # 🔄 counterclockwise arrows
            '\U0001f501': '[REPEAT]',   # 🔁 repeat button
            '\U0001f502': '[REPEAT_ONE]', # 🔂 repeat single
            '\U0001f503': '[VERTICAL]', # 🔃 clockwise vertical arrows
            
            # Places/Environment Category
            '\U0001f3e0': '[HOST]',     # 🏠 house
            '\U0001f3c6': '[AWARD]',    # 🏆 trophy
            '\U0001f3aa': '[STRATEGY]', # 🎪 circus tent
            '\U0001f3e2': '[OFFICE]',   # 🏢 office building
            '\U0001f3ed': '[FACTORY]',  # 🏭 factory
            
            # Tools/Objects Category
            '\U0001f9f9': '[CLEANUP]',  # 🧹 broom
            '\U0001f5d1\ufe0f': '[GARBAGE]', # 🗑️ wastebasket
            '\U0001f5d1': '[GARBAGE]',  # 🗑 wastebasket
            '\u270d\ufe0f': '[WRITE]',  # ✍️ writing hand
            '\u270d': '[WRITE]',        # ✍ writing hand
            '\U0001f58a\ufe0f': '[PEN]', # 🖊️ pen
            '\U0001f58a': '[PEN]',      # 🖊 pen
            '\U0001f528': '[BUILD]',    # 🔨 hammer
            
            # Animals Category (Context-Specific)
            '\U0001f43c': '[PANDAS]',   # 🐼 panda
            '\U0001f40d': '[PYTHON]',   # 🐍 snake
            '\U0001f427': '[LINUX]',    # 🐧 penguin
            '\U0001f980': '[RUST]',     # 🦀 crab
            
            # Symbols and Punctuation
            '\u2022': '-',              # • bullet point to dash
        }
        
        # Start with default mapping and merge/override with custom mapping if provided
        active_mapping = default_emoji_mapping.copy()
        
        if emoji_mapping is not None:
            if not isinstance(emoji_mapping, dict):
                raise ValueError("emoji_mapping must be a dictionary")
            # Update default mapping with custom mappings (overrides existing, adds new)
            active_mapping.update(emoji_mapping)
        
        # Track processing results
        successful_files = []
        failed_files = []
        total_replacements = 0
        processed_file_paths = []  # For Git commit tracking
        
        # Process each file
        for file_path in file_paths:
            try:
                # Validate file path and security checks
                abs_path = validate_operation(file_path, "replace_all_emojis_in_files", check_binary=True)
                
                # Check if file exists and is a text file
                if not os.path.exists(abs_path):
                    failed_files.append(f"{file_path} (file does not exist)")
                    continue
                
                if not os.path.isfile(abs_path):
                    failed_files.append(f"{file_path} (not a regular file)")
                    continue
                
                # Get original file info
                original_checksum = generate_checksum(abs_path)
                file_size = os.path.getsize(abs_path)
                
                # Read file content with proper error handling
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    failed_files.append(f"{file_path} (binary file - text files only)")
                    continue
                except Exception as e:
                    failed_files.append(f"{file_path} (read error: {str(e)})")
                    continue
                
                # Track changes for this file
                original_content = content
                file_replacements = 0
                
                # Apply emoji replacements
                for emoji_char, replacement in active_mapping.items():
                    if emoji_char in content:
                        count = content.count(emoji_char)
                        content = content.replace(emoji_char, replacement)
                        file_replacements += count
                
                # Only write file if changes were made
                if file_replacements > 0:
                    # Validate new content size
                    if len(content) > MAX_FILE_SIZE:
                        failed_files.append(f"{file_path} (resulting file too large: {len(content)} bytes)")
                        continue
                    
                    # Use atomic write operation with proper error handling
                    temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
                    try:
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        os.replace(temp_path, abs_path)
                    except Exception as e:
                        # Clean up temp file if write failed
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                        failed_files.append(f"{file_path} (write error: {str(e)})")
                        continue
                    
                    # Verify write was successful
                    new_checksum = generate_checksum(abs_path)
                    successful_files.append(f"{file_path} ({file_replacements} replacements)")
                    total_replacements += file_replacements
                    processed_file_paths.append(abs_path)
                else:
                    # No emojis found, but file was processed successfully
                    successful_files.append(f"{file_path} (no emojis found)")
                    
            except Exception as e:
                failed_files.append(f"{file_path} (error: {str(e)})")
        
        # Prepare result summary
        total_files = len(file_paths)
        success_count = len(successful_files)
        failure_count = len(failed_files)
        
        result_lines = [
            f"Emoji replacement completed: {success_count}/{total_files} files processed successfully",
            f"Total emoji replacements made: {total_replacements}"
        ]
        
        if successful_files:
            result_lines.append("\nSuccessfully processed files:")
            for file_info in successful_files:
                result_lines.append(f"  ✓ {file_info}")
        
        if failed_files:
            result_lines.append(f"\nFailed to process {failure_count} files:")
            for file_info in failed_files:
                result_lines.append(f"  ✗ {file_info}")
        
        # Auto-commit if enabled and there were successful replacements
        if processed_file_paths:
            commit_result = ""
            try:
                # Use the first processed file's directory for Git operations
                commit_path = os.path.dirname(processed_file_paths[0]) if processed_file_paths else "."
                commit = auto_commit_changes(commit_path, "replace_all_emojis_in_files", commit_message)
                if commit:
                    commit_result = f"\n{commit}"
            except GitError as e:
                commit_result = f"\nNote: {str(e)}"
            
            if commit_result:
                result_lines.append(commit_result)
        
        # Add information about the emoji mapping used
        if emoji_mapping is not None:
            overrides = len([k for k in emoji_mapping.keys() if k in default_emoji_mapping])
            additions = len([k for k in emoji_mapping.keys() if k not in default_emoji_mapping])
            mapping_info = f"\nUsed emoji mapping: Default mapping ({len(default_emoji_mapping)} patterns) + Custom overrides ({overrides} patterns) + Custom additions ({additions} patterns) = {len(active_mapping)} total patterns"
        else:
            mapping_info = f"\nUsed emoji mapping: Default mapping with {len(active_mapping)} emoji patterns"
        result_lines.append(mapping_info)
        
        return "\n".join(result_lines)

    @with_error_handling
    @mcp.tool()
    async def move_file(source_path: str, dest_path: str, commit_message: str = None) -> str:
        """
        Move (rename) a file from source path to destination path.
        
        Args:
            source_path: Path to the source file
            dest_path: Path to the destination file
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If file move fails
        """
        # Validate source and destination paths
        source_abs_path = validate_operation(source_path, "move_file", check_binary=False)
        dest_abs_path = validate_operation(dest_path, "create_file", check_exists=False)
        
        # Check if source is a file
        if not os.path.isfile(source_abs_path):
            raise ValueError(f"Source {source_path} is not a file")
            
        # Check if destination exists
        if os.path.exists(dest_abs_path):
            raise ValueError(f"Destination {dest_path} already exists. Use rewrite_file operation to replace it.")
            
        # Ensure destination directory exists
        dest_dir = os.path.dirname(dest_abs_path)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        # Get source file info for verification
        source_size = os.path.getsize(source_abs_path)
        source_checksum = generate_checksum(source_abs_path)
        
        # Move the file
        try:
            # Attempt atomic move
            os.rename(source_abs_path, dest_abs_path)
        except OSError:
            # If atomic move fails (e.g., across different filesystems), fallback to copy + delete
            try:
                # Copy the file
                with open(source_abs_path, 'rb') as src:
                    with open(dest_abs_path, 'wb') as dst:
                        dst.write(src.read())
                
                # Verify copy succeeded
                dest_size = os.path.getsize(dest_abs_path)
                dest_checksum = generate_checksum(dest_abs_path)
                
                if source_size != dest_size or source_checksum != dest_checksum:
                    # Clean up failed copy
                    os.remove(dest_abs_path)
                    raise ValueError("Move verification failed: checksums do not match")
                
                # Delete the source file
                os.remove(source_abs_path)
            except Exception as e:
                # Clean up partial move if it failed
                if os.path.exists(dest_abs_path):
                    try:
                        os.remove(dest_abs_path)
                    except:
                        pass
                raise ValueError(f"Failed to move file: {str(e)}")
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(dest_abs_path, "move_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully moved file: {source_path} to {dest_path}{commit_result}"

    
    @with_error_handling
    @mcp.tool()
    async def move_multiple_files(source_paths: list[str], dest_paths: list[str] = None, dest_dir: str = None, commit_message: str = None) -> str:
        """
        Move multiple files from source paths to destination paths or directory.
        
        Args:
            source_paths: List of paths to the source files
            dest_paths: List of destination file paths (must match length of source_paths if provided)
            dest_dir: Destination directory (alternative to dest_paths - all files moved here with same names)
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success and failure summary
            
        Raises:
            ValueError: If parameter validation fails
        """
        if not source_paths:
            raise ValueError("No source file paths provided")
        
        # Validate that exactly one destination method is provided
        if dest_paths is None and dest_dir is None:
            raise ValueError("Either dest_paths or dest_dir must be provided")
        if dest_paths is not None and dest_dir is not None:
            raise ValueError("Only one of dest_paths or dest_dir can be provided, not both")
        
        # If dest_paths is provided, validate length matches source_paths
        if dest_paths is not None and len(dest_paths) != len(source_paths):
            raise ValueError(f"Length of dest_paths ({len(dest_paths)}) must match length of source_paths ({len(source_paths)})")
        
        # If dest_dir is provided, validate it's a valid directory path and create destination paths
        if dest_dir is not None:
            dest_dir_abs = validate_operation(dest_dir, "create_dir", check_exists=False)
            # Create destination directory if it doesn't exist
            if not os.path.exists(dest_dir_abs):
                os.makedirs(dest_dir_abs)
            elif not os.path.isdir(dest_dir_abs):
                raise ValueError(f"Destination path {dest_dir} exists but is not a directory")
            
            # Generate dest_paths from dest_dir and source filenames
            dest_paths = []
            for source_path in source_paths:
                filename = os.path.basename(source_path)
                dest_paths.append(os.path.join(dest_dir, filename))
        
        # Track results
        successful_moves = []
        failed_moves = []
        moved_files = []  # For Git commit tracking
        
        # Process each file move
        for i, (source_path, dest_path) in enumerate(zip(source_paths, dest_paths)):
            try:
                # Validate source and destination paths
                source_abs_path = validate_operation(source_path, "move_file", check_binary=False)
                dest_abs_path = validate_operation(dest_path, "create_file", check_exists=False)
                
                # Check if source is a file
                if not os.path.isfile(source_abs_path):
                    failed_moves.append(f"{source_path} -> {dest_path} (source is not a file)")
                    continue
                    
                # Check if destination exists
                if os.path.exists(dest_abs_path):
                    failed_moves.append(f"{source_path} -> {dest_path} (destination already exists)")
                    continue
                    
                # Ensure destination directory exists
                dest_dir_path = os.path.dirname(dest_abs_path)
                if dest_dir_path and not os.path.exists(dest_dir_path):
                    os.makedirs(dest_dir_path)
                    
                # Get source file info for verification
                source_size = os.path.getsize(source_abs_path)
                source_checksum = generate_checksum(source_abs_path)
                
                # Move the file
                try:
                    # Attempt atomic move
                    os.rename(source_abs_path, dest_abs_path)
                except OSError:
                    # If atomic move fails (e.g., across different filesystems), fallback to copy + delete
                    try:
                        # Copy the file
                        with open(source_abs_path, 'rb') as src:
                            with open(dest_abs_path, 'wb') as dst:
                                dst.write(src.read())
                        
                        # Verify copy succeeded
                        dest_size = os.path.getsize(dest_abs_path)
                        dest_checksum = generate_checksum(dest_abs_path)
                        
                        if source_size != dest_size or source_checksum != dest_checksum:
                            # Clean up failed copy
                            if os.path.exists(dest_abs_path):
                                os.remove(dest_abs_path)
                            failed_moves.append(f"{source_path} -> {dest_path} (verification failed: checksums do not match)")
                            continue
                        
                        # Delete the source file
                        os.remove(source_abs_path)
                    except Exception as e:
                        # Clean up partial move if it failed
                        if os.path.exists(dest_abs_path):
                            try:
                                os.remove(dest_abs_path)
                            except:
                                pass
                        failed_moves.append(f"{source_path} -> {dest_path} (failed to move: {str(e)})")
                        continue
                
                successful_moves.append(f"{source_path} -> {dest_path}")
                moved_files.append(dest_abs_path)
                
            except Exception as e:
                failed_moves.append(f"{source_path} -> {dest_path} (error: {str(e)})")
        
        # Prepare result summary
        total_files = len(source_paths)
        success_count = len(successful_moves)
        failure_count = len(failed_moves)
        
        result_lines = [f"Move operation completed: {success_count}/{total_files} files moved successfully"]
        
        if successful_moves:
            result_lines.append("\nSuccessfully moved files:")
            for move in successful_moves:
                result_lines.append(f"  ✓ {move}")
        
        if failed_moves:
            result_lines.append(f"\nFailed to move {failure_count} files:")
            for move in failed_moves:
                result_lines.append(f"  ✗ {move}")
        
        # Auto-commit if enabled and there were successful moves
        if moved_files:
            commit_result = ""
            try:
                # Use the first moved file's directory for Git operations
                commit_path = os.path.dirname(moved_files[0]) if moved_files else "."
                commit = auto_commit_changes(commit_path, "move_multiple_files", commit_message)
                if commit:
                    commit_result = f"\n{commit}"
            except GitError as e:
                commit_result = f"\nNote: {str(e)}"
            
            if commit_result:
                result_lines.append(commit_result)
        
        return "\n".join(result_lines)

    @with_error_handling
    @mcp.tool()
    async def replace_all_emojis_in_files(file_paths: list[str], emoji_mapping: Dict[str, str] = None, commit_message: str = None) -> str:
        """
        Replace all emoji occurrences in multiple text files with text representations.
        
        This tool processes multiple files to replace Unicode emoji characters with
        their text equivalents, helping to resolve encoding issues and improve
        text compatibility across different systems.
        
        Default Emoji Mapping (125+ patterns - expanded from docs/missing_emoji_mappings.md):
        
        Status & Actions: 🔧 -> [API], ⚡ -> [FAST], 🚀 -> [PERF], 📦 -> [PKG], 🎯 -> [TARGET], 
        🔒 -> [SEC], 💡 -> [TIP], 🔥 -> [FIRE], 💪 -> [STRONG], 🧪 -> [TEST]
        
        Files & Data: 📁 -> [DIR], 📂 -> [FOLDER], 📄 -> [FILE], 📝 -> [NOTE], 📋 -> [LIST], 
        📖 -> [BOOK], 📊 -> [CHART], 📈 -> [CHART], 📉 -> [CHART]
        
        Technology & Devices: 💻 -> [COMP], 🖥️ -> [DESKTOP], 📱 -> [MOBILE], 🐳 -> [DOCKER], 
        🌐 -> [NET], 📶 -> [NET], 🔌 -> [PLUG], ⚙️ -> [GEAR]
        
        Results & Status: ✅ -> [PASS], ❌ -> [FAIL], ⚠️ -> [WARN], ℹ️ -> [INFO], 
        ❓ -> [QUESTION], ❗ -> [EXCLAIM2], 🚨 -> [ERR], 🎉 -> [SUCCESS]
        
        Intelligence & Processing: 🧠 -> [MEMORY], 🧮 -> [COMPUTE], 🤖 -> [BOT], 🔮 -> [PREDICT]
        
        Connection & Flow: 🔗 -> [LINK], 🔄 -> [CYCLE], 🔁 -> [REPEAT], 🔂 -> [REPEAT_ONE], 
        🔃 -> [VERTICAL]
        
        Places & Environment: 🏠 -> [HOST], 🏆 -> [AWARD], 🎪 -> [STRATEGY], 🏢 -> [OFFICE], 
        🏭 -> [FACTORY]
        
        Tools & Objects: 🧹 -> [CLEANUP], 🗑️ -> [GARBAGE], ✍️ -> [WRITE], 🖊️ -> [PEN], 
        🔨 -> [BUILD]
        
        Programming Languages: 🐼 -> [PANDAS], 🐍 -> [PYTHON], 🐧 -> [LINUX], 🦀 -> [RUST]
        
        Navigation: ➡️ -> [RIGHT], ⬅️ -> [LEFT], ⬆️ -> [UP], ⬇️ -> [DOWN]
        
        Communication: 💬 -> [COMMENT], 💭 -> [THOUGHT], 🗨️ -> [SPEAK], 📞 -> [PHONE], 
        📧 -> [EMAIL]
        
        And 90+ more comprehensive patterns for complete emoji coverage!
        
        Args:
            file_paths: List of paths to the text files to process
            emoji_mapping: Optional custom emoji mapping dictionary that will be merged 
                          with the default mapping. Any emoji in this dictionary will 
                          override the default replacement for that emoji, and new 
                          emojis will be added to the mapping. The default mapping 
                          remains intact for all other emojis.
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Summary of processing results including files processed, 
                 total replacements made, and any errors encountered
                 
        Raises:
            ValueError: If file paths are invalid, files are binary, or processing fails
            
        Security Notes:
            - Only processes text files (binary files are rejected for security)
            - Validates all file paths to prevent directory traversal attacks
            - Uses atomic file operations to prevent data corruption
            - Maintains file checksums for integrity verification
        """
        # Validate input parameters
        if not file_paths:
            raise ValueError("No file paths provided")
        
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list of strings")
        
        # Default comprehensive emoji mapping based on docs/fix_emojis.py
        default_emoji_mapping = {
            # Basic status indicators
            '\U0001f527': '[API]',      # 🔧 wrench
            '\U000026a1': '[FAST]',     # ⚡ lightning
            '\U0001f680': '[PERF]',     # 🚀 rocket
            '\U0001f4e6': '[PKG]',      # 📦 package
            '\U0001f4ca': '[CHART]',    # 📊 chart
            '\U0001f4c8': '[CHART]',    # 📈 chart increasing
            '\U0001f4c9': '[CHART]',    # 📉 chart decreasing
            '\U0001f3af': '[TARGET]',   # 🎯 target
            '\U0001f512': '[SEC]',      # 🔒 lock
            '\U0001f30d': '[GLOBAL]',   # 🌍 globe
            '\U0001f30e': '[WEB]',      # 🌎 globe
            '\U0001f4f6': '[NET]',      # 📶 network
            '\U0001f310': '[NET]',      # 🌐 network
            '\U0001f4a1': '[TIP]',      # 💡 bulb
            '\U0001f3c1': '[FINAL]',    # 🏁 checkered flag
            '\U0001f389': '[SUCCESS]',  # 🎉 party
            '\U0001f38a': '[DONE]',     # 🎊 confetti
            '\U0001f40c': '[SLOW]',     # 🐌 snail
            '\U0001f433': '[DOCKER]',   # 🐳 whale
            '\U0001f6e1\ufe0f': '[SHIELD]', # 🛡️ shield
            '\U0001f6e1': '[SHIELD]',   # 🛡 shield
            '\U0001f6a8': '[ERR]',      # 🚨 siren
            '\U0001f50d': '[SEARCH]',   # 🔍 magnifying glass
            '\U0001f514': '[CONN]',     # 🔔 bell
            '\U0001f525': '[FIRE]',     # 🔥 fire
            '\U0001f4aa': '[STRONG]',   # 💪 muscle
            '\U0001f9ea': '[TEST]',     # 🧪 test tube
            '\U0001f4dd': '[NOTE]',     # 📝 memo
            '\U0001f4cb': '[LIST]',     # 📋 clipboard
            '\U0001f4c4': '[FILE]',     # 📄 document
            '\U0001f4c1': '[DIR]',      # 📁 folder
            '\U0001f4c2': '[FOLDER]',   # 📂 open folder
            '\U0001f4d6': '[BOOK]',     # 📖 book
            '\U0001f4bb': '[COMP]',     # 💻 computer
            '\U0001f5a5\ufe0f': '[DESKTOP]', # 🖥️ desktop
            '\U0001f5a5': '[DESKTOP]',  # 🖥 desktop
            '\U0001f4f1': '[MOBILE]',   # 📱 mobile
            '\U000023f1\ufe0f': '[TIMER]', # ⏱️ timer
            '\U000023f1': '[TIMER]',    # ⏱ timer
            '\U0001f552': '[TIME]',     # 🕒 clock
            '\U0001f195': '[NEW]',      # 🆕 new
            '\U0001f199': '[UP]',       # 🆙 up
            '\U0001f19a': '[VS]',       # 🆚 vs
            '\U0001f4a5': '[BOOM]',     # 💥 explosion
            '\U0001f525': '[HOT]',      # 🔥 fire
            '\U00002744\ufe0f': '[COLD]', # ❄️ snowflake
            '\U00002744': '[COLD]',     # ❄ snowflake
            '\U0001f522': '[NUMS]',     # 🔢 numbers
            '\U0001f523': '[SYMBOLS]',  # 🔣 symbols
            '\U0001f524': '[ABC]',      # 🔤 letters
            '\U00002699\ufe0f': '[GEAR]', # ⚙️ gear
            '\U00002699': '[GEAR]',     # ⚙ gear
            '\U00002696\ufe0f': '[BALANCE]', # ⚖️ balance
            '\U00002696': '[BALANCE]',  # ⚖ balance
            '\U0001f4e4': '[OUTBOX]',   # 📤 outbox
            '\U0001f4e5': '[INBOX]',    # 📥 inbox
            '\U0001f4ed': '[EMPTY]',    # 📭 mailbox
            '\U0001f4ec': '[MAIL]',     # 📬 mailbox
            '\U0001f4ea': '[MAILBOX]',  # 📪 closed mailbox
            '\U0001f4e8': '[ENVELOPE]', # 📨 envelope
            '\U0001f194': '[ID]',       # 🆔 ID
            '\U0001f50c': '[PLUG]',     # 🔌 plug
            '\U0001f4de': '[PHONE]',    # 📞 telephone
            '\U0001f4e0': '[FAX]',      # 📠 fax
            '\U0001f4fc': '[VHS]',      # 📼 videocassette
            '\U0001f4fd\ufe0f': '[FILM]', # 📽️ film projector
            '\U0001f4fd': '[FILM]',     # 📽 film projector
            '\U0001f3a5': '[CAMERA]',   # 🎥 movie camera
            '\U0001f4f7': '[PHOTO]',    # 📷 camera
            '\U0001f4f8': '[FLASH]',    # 📸 camera with flash
            '\U0001f50e': '[ZOOM]',     # 🔎 magnifying glass
            '\U0001f50f': '[LOCK]',     # 🔏 lock with pen
            '\U0001f510': '[UNLOCK]',   # 🔐 lock with key
            '\U0001f511': '[KEY]',      # 🔑 key
            '\U0001f513': '[OPEN]',     # 🔓 unlocked
            '\U0001f6aa': '[DOOR]',     # 🚪 door
            '\U0001f4ac': '[COMMENT]',  # 💬 speech balloon
            '\U0001f4ad': '[THOUGHT]',  # 💭 thought balloon
            '\U0001f5e8\ufe0f': '[SPEAK]', # 🗨️ left speech bubble
            '\U0001f5e8': '[SPEAK]',    # 🗨 left speech bubble
            '\U0001f5ef\ufe0f': '[ANGRY]', # 🗯️ right anger bubble
            '\U0001f5ef': '[ANGRY]',    # 🗯 right anger bubble
            '\U0001f4f0': '[NEWS]',     # 📰 newspaper
            '\U0001f4f3': '[VIBRATE]',  # 📳 vibration mode
            '\U0001f4f4': '[SILENT]',   # 📴 mobile phone off
            '\U0001f4f5': '[NO_MOBILE]', # 📵 no mobile phones
            '\U0001f4f6': '[SIGNAL]',   # 📶 antenna bars
            '\U0001f4f7': '[CAMERA2]',  # 📷 camera
            '\U0001f4f9': '[VIDEO]',    # 📹 video camera
            '\U0001f4fa': '[TV]',       # 📺 television
            '\U0001f4fb': '[RADIO]',    # 📻 radio
            '\U0001f4fc': '[TAPE]',     # 📼 videocassette
            '\U0001f50a': '[LOUD]',     # 🔊 speaker high volume
            '\U0001f50b': '[LOW]',      # 🔋 battery
            '\U0001f50c': '[ELECTRIC]', # 🔌 electric plug
            '\U0001f4af': '[100]',      # 💯 hundred points
            
            # Add checkmark and X emojis
            '\u2705': '[PASS]',         # ✅ check mark
            '\u274c': '[FAIL]',         # ❌ cross mark
            '\u26a0\ufe0f': '[WARN]',   # ⚠️ warning
            '\u26a0': '[WARN]',         # ⚠ warning
            '\u2139\ufe0f': '[INFO]',   # ℹ️ information
            '\u2139': '[INFO]',         # ℹ information
            '\u2753': '[QUESTION]',     # ❓ question mark
            '\u2754': '[QUESTION2]',    # ❔ white question mark
            '\u2755': '[EXCLAIM]',      # ❕ white exclamation mark
            '\u2757': '[EXCLAIM2]',     # ❗ exclamation mark
            '\u27a1\ufe0f': '[RIGHT]',  # ➡️ right arrow
            '\u27a1': '[RIGHT]',        # ➡ right arrow
            '\u2b05\ufe0f': '[LEFT]',   # ⬅️ left arrow
            '\u2b05': '[LEFT]',         # ⬅ left arrow
            '\u2b06\ufe0f': '[UP]',     # ⬆️ up arrow
            '\u2b06': '[UP]',           # ⬆ up arrow
            '\u2b07\ufe0f': '[DOWN]',   # ⬇️ down arrow
            '\u2b07': '[DOWN]',         # ⬇ down arrow
            
            # Missing emoji mappings from docs/missing_emoji_mappings.md
            # Brain/Intelligence Category
            '\U0001f9e0': '[MEMORY]',   # 🧠 brain
            '\U0001f9ee': '[COMPUTE]',  # 🧮 abacus
            '\U0001f916': '[BOT]',      # 🤖 robot
            '\U0001f52e': '[PREDICT]',  # 🔮 crystal ball
            
            # Connection/Process Category
            '\U0001f517': '[LINK]',     # 🔗 link
            '\U0001f504': '[CYCLE]',    # 🔄 counterclockwise arrows
            '\U0001f501': '[REPEAT]',   # 🔁 repeat button
            '\U0001f502': '[REPEAT_ONE]', # 🔂 repeat single
            '\U0001f503': '[VERTICAL]', # 🔃 clockwise vertical arrows
            
            # Places/Environment Category
            '\U0001f3e0': '[HOST]',     # 🏠 house
            '\U0001f3c6': '[AWARD]',    # 🏆 trophy
            '\U0001f3aa': '[STRATEGY]', # 🎪 circus tent
            '\U0001f3e2': '[OFFICE]',   # 🏢 office building
            '\U0001f3ed': '[FACTORY]',  # 🏭 factory
            
            # Tools/Objects Category
            '\U0001f9f9': '[CLEANUP]',  # 🧹 broom
            '\U0001f5d1\ufe0f': '[GARBAGE]', # 🗑️ wastebasket
            '\U0001f5d1': '[GARBAGE]',  # 🗑 wastebasket
            '\u270d\ufe0f': '[WRITE]',  # ✍️ writing hand
            '\u270d': '[WRITE]',        # ✍ writing hand
            '\U0001f58a\ufe0f': '[PEN]', # 🖊️ pen
            '\U0001f58a': '[PEN]',      # 🖊 pen
            '\U0001f528': '[BUILD]',    # 🔨 hammer
            
            # Animals Category (Context-Specific)
            '\U0001f43c': '[PANDAS]',   # 🐼 panda
            '\U0001f40d': '[PYTHON]',   # 🐍 snake
            '\U0001f427': '[LINUX]',    # 🐧 penguin
            '\U0001f980': '[RUST]',     # 🦀 crab
            
            # Symbols and Punctuation
            '\u2022': '-',              # • bullet point to dash
        }
        
        # Start with default mapping and merge/override with custom mapping if provided
        active_mapping = default_emoji_mapping.copy()
        
        if emoji_mapping is not None:
            if not isinstance(emoji_mapping, dict):
                raise ValueError("emoji_mapping must be a dictionary")
            # Update default mapping with custom mappings (overrides existing, adds new)
            active_mapping.update(emoji_mapping)
        
        # Track processing results
        successful_files = []
        failed_files = []
        total_replacements = 0
        processed_file_paths = []  # For Git commit tracking
        
        # Process each file
        for file_path in file_paths:
            try:
                # Validate file path and security checks
                abs_path = validate_operation(file_path, "replace_all_emojis_in_files", check_binary=True)
                
                # Check if file exists and is a text file
                if not os.path.exists(abs_path):
                    failed_files.append(f"{file_path} (file does not exist)")
                    continue
                
                if not os.path.isfile(abs_path):
                    failed_files.append(f"{file_path} (not a regular file)")
                    continue
                
                # Get original file info
                original_checksum = generate_checksum(abs_path)
                file_size = os.path.getsize(abs_path)
                
                # Read file content with proper error handling
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    failed_files.append(f"{file_path} (binary file - text files only)")
                    continue
                except Exception as e:
                    failed_files.append(f"{file_path} (read error: {str(e)})")
                    continue
                
                # Track changes for this file
                original_content = content
                file_replacements = 0
                
                # Apply emoji replacements
                for emoji_char, replacement in active_mapping.items():
                    if emoji_char in content:
                        count = content.count(emoji_char)
                        content = content.replace(emoji_char, replacement)
                        file_replacements += count
                
                # Only write file if changes were made
                if file_replacements > 0:
                    # Validate new content size
                    if len(content) > MAX_FILE_SIZE:
                        failed_files.append(f"{file_path} (resulting file too large: {len(content)} bytes)")
                        continue
                    
                    # Use atomic write operation with proper error handling
                    temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
                    try:
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        os.replace(temp_path, abs_path)
                    except Exception as e:
                        # Clean up temp file if write failed
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                        failed_files.append(f"{file_path} (write error: {str(e)})")
                        continue
                    
                    # Verify write was successful
                    new_checksum = generate_checksum(abs_path)
                    successful_files.append(f"{file_path} ({file_replacements} replacements)")
                    total_replacements += file_replacements
                    processed_file_paths.append(abs_path)
                else:
                    # No emojis found, but file was processed successfully
                    successful_files.append(f"{file_path} (no emojis found)")
                    
            except Exception as e:
                failed_files.append(f"{file_path} (error: {str(e)})")
        
        # Prepare result summary
        total_files = len(file_paths)
        success_count = len(successful_files)
        failure_count = len(failed_files)
        
        result_lines = [
            f"Emoji replacement completed: {success_count}/{total_files} files processed successfully",
            f"Total emoji replacements made: {total_replacements}"
        ]
        
        if successful_files:
            result_lines.append("\nSuccessfully processed files:")
            for file_info in successful_files:
                result_lines.append(f"  ✓ {file_info}")
        
        if failed_files:
            result_lines.append(f"\nFailed to process {failure_count} files:")
            for file_info in failed_files:
                result_lines.append(f"  ✗ {file_info}")
        
        # Auto-commit if enabled and there were successful replacements
        if processed_file_paths:
            commit_result = ""
            try:
                # Use the first processed file's directory for Git operations
                commit_path = os.path.dirname(processed_file_paths[0]) if processed_file_paths else "."
                commit = auto_commit_changes(commit_path, "replace_all_emojis_in_files", commit_message)
                if commit:
                    commit_result = f"\n{commit}"
            except GitError as e:
                commit_result = f"\nNote: {str(e)}"
            
            if commit_result:
                result_lines.append(commit_result)
        
        # Add information about the emoji mapping used
        if emoji_mapping is not None:
            overrides = len([k for k in emoji_mapping.keys() if k in default_emoji_mapping])
            additions = len([k for k in emoji_mapping.keys() if k not in default_emoji_mapping])
            mapping_info = f"\nUsed emoji mapping: Default mapping ({len(default_emoji_mapping)} patterns) + Custom overrides ({overrides} patterns) + Custom additions ({additions} patterns) = {len(active_mapping)} total patterns"
        else:
            mapping_info = f"\nUsed emoji mapping: Default mapping with {len(active_mapping)} emoji patterns"
        result_lines.append(mapping_info)
        
        return "\n".join(result_lines)

    @with_error_handling
    @mcp.tool()
    async def replace_all_in_file(path: str, new_string: Union[str, Dict[str, Any], list, int, float, bool] = None, old_string: Union[str, Dict[str, Any], list, int, float, bool] = None, commit_message: str = None, new_str: Union[str, Dict[str, Any], list, int, float, bool] = None, old_str: Union[str, Dict[str, Any], list, int, float, bool] = None) -> str:
        """
        Replace ALL occurrences of specific text within a file.
        
        This function replaces every instance of the old_string with new_string throughout the entire file.
        Unlike some text editors that only replace the first occurrence, this tool replaces all matches.
        
        Args:
            path: Path to the file to update
            new_string: Replacement text or object. If an object is provided, it will be serialized as JSON.
            old_string: Text or object to find and replace. If an object is provided, it will be serialized as JSON.
            commit_message: Custom Git commit message (optional)
            new_str: Alternative parameter name for new_string (backup for LLM compatibility)
            old_str: Alternative parameter name for old_string (backup for LLM compatibility)
            
        Returns:
            str: Success message with replacement count and checksum information
            
        Raises:
            ValueError: If file update fails or parameters are invalid
        """
        abs_path = validate_operation(path, "replace_all_in_file", check_binary=True)
        
        # Handle backup parameters for LLM compatibility
        # Use old_str as backup if old_string is not provided or is None
        if old_string is None and old_str is not None:
            old_string = old_str
        elif old_string is None and old_str is None:
            raise ValueError("Either old_string or old_str must be provided")
            
        # Use new_str as backup if new_string is not provided or is None
        if new_string is None and new_str is not None:
            new_string = new_str
        elif new_string is None and new_str is None:
            raise ValueError("Either new_string or new_str must be provided")
        
        # Validate content inputs
        if not old_string:
            raise ValueError("Old content cannot be empty")

        # Convert old_string to string appropriately
        old_string = sanitize_file_string(old_string)
        
        # Convert new_string to string appropriately
        new_string = sanitize_file_string(new_string)
            
        if '\0' in new_string:
            raise ValueError("Cannot replace with binary content")
            
        original_checksum = generate_checksum(abs_path)
        
        # Read file with proper error handling
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError(f"File {path} is not a valid text file")
        
        if old_string not in content:
            raise ValueError(f"The specified text to replace was not found in {path}")
        
        # Count occurrences before replacement for reporting
        occurrence_count = content.count(old_string)
        
        # Replace ALL occurrences of old_string with new_string
        updated_content = content.replace(old_string, new_string)
        
        # Validate new size
        if len(updated_content) > MAX_FILE_SIZE:
            raise ValueError(f"Updated content would be too large ({len(updated_content)} bytes). Maximum size is {MAX_FILE_SIZE} bytes.")
        
        # Use atomic write operation with proper error handling
        temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            os.replace(temp_path, abs_path)
        except Exception as e:
            # Clean up temp file if update failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise ValueError(f"Failed to update file: {str(e)}")
        
        new_checksum = generate_checksum(abs_path)
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "replace_all_in_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully replaced all occurrences in file: {path}\nReplacements made: {occurrence_count}\nOriginal checksum: {original_checksum}\nNew checksum: {new_checksum}{commit_result}"
    
    @with_error_handling
    @mcp.tool()
    async def read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """
        Read the contents of a text file.
        
        Args:
            path: Path to the file
            start_line: Optional starting line number (1-indexed, inclusive). If not specified, reads from beginning.
            end_line: Optional ending line number (1-indexed, inclusive). If not specified, reads to end.
            
        Returns:
            str: File info and contents
            
        Raises:
            ValueError: If file reading fails or line numbers are invalid
        """
        abs_path = validate_operation(path, "read_file", check_binary=True)
        
        # Get file info
        file_size = os.path.getsize(abs_path)
        checksum = generate_checksum(abs_path)
        
        # Read with timeout protection
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                if start_line is None and end_line is None:
                    # Read entire file if no line range specified
                    content = f.read()
                    line_info = ""
                else:
                    # Read line by line for range selection
                    all_lines = f.readlines()
                    total_lines = len(all_lines)
                    
                    # Validate line numbers
                    if start_line is not None:
                        if start_line < 1:
                            raise ValueError("start_line must be >= 1")
                        if start_line > total_lines:
                            raise ValueError(f"start_line ({start_line}) is beyond file length ({total_lines} lines)")
                    
                    if end_line is not None:
                        if end_line < 1:
                            raise ValueError("end_line must be >= 1")
                        if end_line > total_lines:
                            raise ValueError(f"end_line ({end_line}) is beyond file length ({total_lines} lines)")
                    
                    if start_line is not None and end_line is not None:
                        if start_line > end_line:
                            raise ValueError("start_line cannot be greater than end_line")
                    
                    # Determine actual line range (convert to 0-indexed)
                    start_idx = (start_line - 1) if start_line is not None else 0
                    end_idx = end_line if end_line is not None else total_lines
                    
                    # Extract the specified lines
                    selected_lines = all_lines[start_idx:end_idx]
                    content = ''.join(selected_lines)
                    
                    # Add line range info
                    actual_start = start_idx + 1
                    actual_end = min(end_idx, total_lines)
                    line_info = f"Lines: {actual_start}-{actual_end} (of {total_lines} total)\n"
                    
        except UnicodeDecodeError as e:
            raise ValueError(f"Cannot read binary file {path}. Only text files are supported.")
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")
            
        file_info = f"File: {path}\nSize: {file_size} bytes\nChecksum (SHA-256): {checksum}\n{line_info}\nContent:\n\n"
        return file_info + content

    @with_error_handling
    @mcp.tool()
    async def read_multiple_files(paths: list[str]) -> str:
        """
        Read the contents of multiple text files.
        
        Args:
            paths: List of paths to the files
            
        Returns:
            str: Formatted file contents for all files
            
        Raises:
            ValueError: If file reading fails for all files
        """
        if not paths:
            raise ValueError("No file paths provided")
            
        results = []
        failed_files = []
        
        for path in paths:
            try:
                abs_path = validate_operation(path, "read_file", check_binary=True)
                
                # Get file info
                file_size = os.path.getsize(abs_path)
                checksum = generate_checksum(abs_path)
                
                # Read with timeout protection
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    file_info = f"File: {path}\nSize: {file_size} bytes\nChecksum (SHA-256): {checksum}\n\nContent:\n\n"
                    results.append(file_info + content)
                except UnicodeDecodeError:
                    failed_files.append(f"{path} (binary file)")
                except Exception as e:
                    failed_files.append(f"{path} ({str(e)})")
            except ValueError as e:
                failed_files.append(f"{path} ({str(e)})")
        
        if not results and failed_files:
            raise ValueError(f"Failed to read any files: {', '.join(failed_files)}")
        
        result = "\n\n" + "="*80 + "\n\n".join(results)
        
        if failed_files:
            result += f"\n\nFailed to read {len(failed_files)} files: {', '.join(failed_files)}"
        
        return result

    @with_error_handling
    @mcp.tool()
    async def read_image(path: str) -> Image:
        """
        Read and return an image file as a Pillow Image object.
        
        Args:
            path: Path to the image file to read
            
        Returns:
            Image: Pillow Image object that can be displayed or processed by the MCP client
            
        Raises:
            ValueError: If image reading fails or file is not a valid image
        """
        # Validate path with strict security checks
        abs_path = validate_operation(path, "read_image", check_binary=False, check_exists=True)
        
        # Check if it's a file (not a directory)
        if not os.path.isfile(abs_path):
            raise ValueError(f"Path {path} is not a file")
        
        # Get file info for security validation
        file_size = os.path.getsize(abs_path)
        
        # Check file size limit (10MB)
        if file_size > MAX_FILE_SIZE:
            log_security_event("image_file_size_limit", {"path": path, "size": file_size})
            raise ValueError(f"Image file {path} is too large ({file_size} bytes). Maximum file size is {MAX_FILE_SIZE} bytes.")
        
        # Validate that it's actually an image file by checking common image extensions
        # This is a first-pass validation before attempting to open with PIL
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico'}
        file_ext = os.path.splitext(abs_path)[1].lower()
        
        if file_ext not in valid_extensions:
            log_security_event("invalid_image_extension", {"path": path, "extension": file_ext})
            raise ValueError(f"File {path} does not have a valid image extension. Supported formats: {', '.join(sorted(valid_extensions))}")
        
        try:
            # Use PIL to open and validate the image
            # This provides robust format validation and security
            with PILImage.open(abs_path) as pil_image:
                # Verify it's actually a valid image by trying to load it
                pil_image.verify()
            
            # Re-open the image since verify() closes it
            # and we need the actual image data
            with PILImage.open(abs_path) as pil_image:
                # Convert to RGB if necessary for broader compatibility
                # Some formats like RGBA or P (palette) might need conversion
                if pil_image.mode in ('RGBA', 'P', 'LA'):
                    # Preserve transparency for formats that support it
                    if pil_image.mode in ('RGBA', 'LA'):
                        format_type = "PNG"  # PNG supports transparency
                    else:
                        # For palette mode, convert to RGB
                        pil_image = pil_image.convert('RGB')
                        format_type = "JPEG"
                else:
                    # For RGB, L (grayscale), use JPEG for efficiency
                    format_type = "JPEG" if pil_image.mode in ('RGB', 'L') else "PNG"
                
                # Get image dimensions for validation
                width, height = pil_image.size
                
                # Reasonable size limits to prevent resource exhaustion
                max_dimension = 8192  # 8K resolution limit
                if width > max_dimension or height > max_dimension:
                    log_security_event("image_dimension_limit", {
                        "path": path, 
                        "width": width, 
                        "height": height,
                        "max_allowed": max_dimension
                    })
                    raise ValueError(f"Image {path} dimensions ({width}x{height}) exceed maximum allowed size ({max_dimension}x{max_dimension})")
                
                # Convert to bytes for the MCP Image object
                import io
                img_buffer = io.BytesIO()
                pil_image.save(img_buffer, format=format_type, quality=95 if format_type == "JPEG" else None)
                image_data = img_buffer.getvalue()
                
                # Create and return the MCP Image object
                return Image(
                    data=image_data,
                    format=format_type.lower()
                )
                
        except PILImage.UnidentifiedImageError:
            log_security_event("invalid_image_format", {"path": path})
            raise ValueError(f"File {path} is not a valid image file or format is not supported")
        except OSError as e:
            log_security_event("image_file_access_error", {"path": path, "error": str(e)})
            raise ValueError(f"Cannot access image file {path}: {str(e)}")
        except Exception as e:
            log_security_event("image_processing_error", {"path": path, "error": str(e)})
            raise ValueError(f"Error processing image file {path}: {str(e)}")

    @with_error_handling
    @mcp.tool()
    async def create_file(path: str, content: Union[str, Dict[str, Any], list, int, float, bool] = "", commit_message: str = None) -> str:
        """
        Create a new text file with the specified content.
        
        Args:
            path: Where to create the file
            content: Text content or object to write to the file. If an object is provided,
                    it will be serialized as JSON.
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If file creation fails
        """
        abs_path = validate_operation(path, "create_file")
        
        if os.path.exists(abs_path):
            raise ValueError(f"File already exists at {path}. Use rewrite_file operation to replace it.")
        
        # Handle different content types
        content = sanitize_file_string(content)
        
        # Validate content to prevent binary data
        if '\0' in content:
            raise ValueError("Cannot create file with binary content")
            
        # Check if content is too large
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"Content is too large ({len(content)} bytes). Maximum size is {MAX_FILE_SIZE} bytes.")
        
        # Create parent directories if needed
        directory = os.path.dirname(abs_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Use atomic write operation with proper error handling
        temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(temp_path, abs_path)
        except Exception as e:
            # Clean up temp file if creation failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise ValueError(f"Failed to write file: {str(e)}")
        
        # Get file details for verification
        file_size = os.path.getsize(abs_path)
        checksum = generate_checksum(abs_path)
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "create_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully created file: {path}\nSize: {file_size} bytes\nChecksum: {checksum}{commit_result}"

    @with_error_handling
    @mcp.tool()
    async def update_file(path: str, old_string: Union[str, Dict[str, Any], list, int, float, bool] = None, new_string: Union[str, Dict[str, Any], list, int, float, bool] = None, commit_message: str = None, old_str: Union[str, Dict[str, Any], list, int, float, bool] = None, new_str: Union[str, Dict[str, Any], list, int, float, bool] = None) -> str:
        """
        Update specific text within a file by replacing matching content.
        
        Args:
            path: Path to the file to update
            old_string: Text or object to find and replace. If an object is provided, it will be serialized as JSON.
            new_string: Replacement text or object. If an object is provided, it will be serialized as JSON.
            commit_message: Custom Git commit message (optional)
            old_str: Alternative parameter name for old_string (backup for LLM compatibility)
            new_str: Alternative parameter name for new_string (backup for LLM compatibility)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If file update fails
        """
        abs_path = validate_operation(path, "update_file", check_binary=True)
        
        # Handle backup parameters for LLM compatibility
        # Use old_str as backup if old_string is not provided or is None
        if old_string is None and old_str is not None:
            old_string = old_str
        elif old_string is None and old_str is None:
            raise ValueError("Either old_string or old_str must be provided")
            
        # Use new_str as backup if new_string is not provided or is None
        if new_string is None and new_str is not None:
            new_string = new_str
        elif new_string is None and new_str is None:
            raise ValueError("Either new_string or new_str must be provided")
        
        # Validate content inputs
        if not old_string:
            raise ValueError("Old content cannot be empty")

        # Convert old_string to string appropriately
        old_string = sanitize_file_string(old_string)
        
        # Convert new_string to string appropriately
        new_string = sanitize_file_string(new_string)
            
        if '\0' in new_string:
            raise ValueError("Cannot update with binary content")
            
        original_checksum = generate_checksum(abs_path)
        
        # Read file with proper error handling
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError(f"File {path} is not a valid text file")
        
        if old_string not in content:
            raise ValueError(f"The specified text to replace was not found in {path}")
        
        updated_content = content.replace(old_string, new_string)
        
        # Validate new size
        if len(updated_content) > MAX_FILE_SIZE:
            raise ValueError(f"Updated content would be too large ({len(updated_content)} bytes). Maximum size is {MAX_FILE_SIZE} bytes.")
        
        # Use atomic write operation with proper error handling
        temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            os.replace(temp_path, abs_path)
        except Exception as e:
            # Clean up temp file if update failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise ValueError(f"Failed to update file: {str(e)}")
        
        new_checksum = generate_checksum(abs_path)
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "update_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully updated file: {path}\nOriginal checksum: {original_checksum}\nNew checksum: {new_checksum}{commit_result}"

    @with_error_handling
    @mcp.tool()
    async def rewrite_file(path: str, content: Union[str, Dict[str, Any], list, int, float, bool], commit_message: str = None) -> str:
        """
        Completely rewrite a file with new content.
        
        Args:
            path: Path to the file
            content: New content for the file. If an object is provided,
                    it will be serialized as JSON.
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If file rewrite fails
        """
        abs_path = validate_operation(path, "rewrite_file", check_binary=True)
        
        # Handle different content types
        content = sanitize_file_string(content)
        
        # Validate content to prevent binary data
        if '\0' in content:
            raise ValueError("Cannot rewrite with binary content")
            
        # Check if content is too large
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"Content is too large ({len(content)} bytes). Maximum size is {MAX_FILE_SIZE} bytes.")
        
        # Get original checksum for verification
        original_checksum = None
        if os.path.exists(abs_path):
            original_checksum = generate_checksum(abs_path)
        
        # Create parent directories if needed
        directory = os.path.dirname(abs_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Use atomic write operation with proper error handling
        temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(temp_path, abs_path)
        except Exception as e:
            # Clean up temp file if rewrite failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise ValueError(f"Failed to rewrite file: {str(e)}")
        
        new_checksum = generate_checksum(abs_path)
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "rewrite_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        if original_checksum:
            return f"Successfully rewrote file: {path}\nOriginal checksum: {original_checksum}\nNew checksum: {new_checksum}{commit_result}"
        else:
            return f"Successfully created file: {path}\nChecksum: {new_checksum}{commit_result}"

    @with_error_handling
    @mcp.tool()
    async def delete_file(path: str, commit_message: str = None) -> str:
        """
        Delete a file.
        
        Args:
            path: Path to the file
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If file deletion fails
        """
        abs_path = validate_operation(path, "delete_file")
        
        if not os.path.exists(abs_path):
            raise ValueError(f"File does not exist at {path}")
        
        if os.path.isdir(abs_path):
            raise ValueError(f"{path} is a directory, not a file")
        
        try:
            os.remove(abs_path)
        except Exception as e:
            raise ValueError(f"Failed to delete file: {str(e)}")
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(os.path.dirname(abs_path), "delete_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully deleted file: {path}{commit_result}"

    @with_error_handling
    @mcp.tool()
    async def remove_from_file(path: str, old_string: Union[str, Dict[str, Any], list, int, float, bool], commit_message: str = None) -> str:
        """
        Remove specific text from a file.
        
        Args:
            path: Path to the file
            old_string: Text to find and remove
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If text removal fails
        """
        abs_path = validate_operation(path, "remove_from_file", check_binary=True)
        
        # Validate content inputs
        if not old_string:
            raise ValueError("Content to remove cannot be empty")
        
        old_string = sanitize_file_string(old_string)
            
        original_checksum = generate_checksum(abs_path)
        
        # Read file with proper error handling
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError(f"File {path} is not a valid text file")
        
        if old_string not in content:
            raise ValueError(f"The specified text to remove was not found in {path}")
        
        updated_content = content.replace(old_string, "")
        
        # Use atomic write operation with proper error handling
        temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            os.replace(temp_path, abs_path)
        except Exception as e:
            # Clean up temp file if update failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise ValueError(f"Failed to update file: {str(e)}")
        
        new_checksum = generate_checksum(abs_path)
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "remove_from_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully removed content from file: {path}\nOriginal checksum: {original_checksum}\nNew checksum: {new_checksum}{commit_result}"

    @with_error_handling
    @mcp.tool()
    async def append_to_file(path: str, content: Union[str, Dict[str, Any], list, int, float, bool], commit_message: str = None) -> str:
        """
        Append content to the end of a file.
        
        Args:
            path: Path to the file
            content: Text content or object to append. If an object is provided,
                    it will be serialized as JSON.
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message
            
        Raises:
            ValueError: If append fails
        """
        abs_path = validate_operation(path, "append_to_file", check_binary=True)
        
        # Handle different content types
        content = sanitize_file_string(content)
        
        # Validate content
        if not content:
            raise ValueError("Content to append cannot be empty")
            
        if '\0' in content:
            raise ValueError("Cannot append binary content")
        
        # Create file if it doesn't exist
        original_checksum = None
        if not os.path.exists(abs_path):
            directory = os.path.dirname(abs_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
        else:
            # Get original checksum for verification
            original_checksum = generate_checksum(abs_path)
            
            # Check if file is too large after append
            file_size = os.path.getsize(abs_path)
            if file_size + len(content) > MAX_FILE_SIZE:
                raise ValueError(f"Resulting file would be too large ({file_size + len(content)} bytes). Maximum size is {MAX_FILE_SIZE} bytes.")
        
        # Append content to file with proper error handling
        try:
            with open(abs_path, 'a', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise ValueError(f"Failed to append to file: {str(e)}")
        
        new_checksum = generate_checksum(abs_path)
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "append_to_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        if original_checksum:
            return f"Successfully appended content to file: {path}\nOriginal checksum: {original_checksum}\nNew checksum: {new_checksum}{commit_result}"
        else:
            return f"Successfully created and appended content to file: {path}\nChecksum: {new_checksum}{commit_result}"
            
    @with_error_handling
    @mcp.tool()
    async def insert_in_file(path: str, content: Union[str, Dict[str, Any], list, int, float, bool], after_line: int = None, before_line: int = None, after_pattern: str = None, commit_message: str = None) -> str:
        """
        Insert content at a specific position in a file.
        
        Args:
            path: Path to the file
            content: Text content or object to insert. If an object is provided,
                    it will be serialized as JSON.
            after_line: Line number to insert after (0-indexed)
            before_line: Line number to insert before (0-indexed)
            after_pattern: Pattern to search for and insert after the first occurrence
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success message with details of the insertion
            
        Raises:
            ValueError: If insertion fails or if multiple position specifiers are used
        """
        abs_path = validate_operation(path, "insert_in_file", check_binary=True)
        
        # Validate that the file exists
        if not os.path.exists(abs_path):
            raise ValueError(f"File does not exist at {path}. Use create_file operation to create it first.")
        
        # Validate position specification - only one method should be provided
        position_methods = sum(1 for p in [after_line is not None, before_line is not None, after_pattern is not None] if p)
        if position_methods == 0:
            raise ValueError("Must specify one of: after_line, before_line, or after_pattern")
        if position_methods > 1:
            raise ValueError("Only one position specifier can be used: after_line, before_line, or after_pattern")
        
        # Handle different content types
        content = sanitize_file_string(content)
        
        # Validate content
        if not content:
            raise ValueError("Content to insert cannot be empty")
            
        if '\0' in content:
            raise ValueError("Cannot insert binary content")
        
        # Get original file information for verification
        original_checksum = generate_checksum(abs_path)
        
        # Read the file content with proper error handling
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            raise ValueError(f"File {path} is not a valid text file")
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")
        
        # Determine insertion position
        insertion_index = None
        position_description = ""
        
        if after_line is not None:
            if not isinstance(after_line, int) or after_line < 0:
                raise ValueError("after_line must be a non-negative integer")
            if after_line >= len(lines):
                raise ValueError(f"after_line value {after_line} is out of range. File has {len(lines)} lines (0-indexed).")
            insertion_index = after_line + 1
            position_description = f"after line {after_line}"
        
        elif before_line is not None:
            if not isinstance(before_line, int) or before_line < 0:
                raise ValueError("before_line must be a non-negative integer")
            if before_line > len(lines):
                raise ValueError(f"before_line value {before_line} is out of range. File has {len(lines)} lines (0-indexed).")
            insertion_index = before_line
            position_description = f"before line {before_line}"
        
        elif after_pattern is not None:
            pattern_found = False
            for i, line in enumerate(lines):
                if after_pattern in line:
                    insertion_index = i + 1
                    position_description = f"after the pattern '{after_pattern}' (found at line {i})"
                    pattern_found = True
                    break
            if not pattern_found:
                raise ValueError(f"Pattern '{after_pattern}' not found in file {path}")
        
        # Check if resulting file would be too large
        current_size = os.path.getsize(abs_path)
        content_size = len(content)
        if current_size + content_size > MAX_FILE_SIZE:
            raise ValueError(f"Resulting file would be too large ({current_size + content_size} bytes). Maximum size is {MAX_FILE_SIZE} bytes.")
        
        # Ensure the content ends with a newline if inserting in the middle of the file
        if insertion_index < len(lines) and not content.endswith('\n'):
            content += '\n'
        
        # Insert the content at the appropriate position
        lines.insert(insertion_index, content)
        
        # Use atomic write operation with proper error handling
        temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            os.replace(temp_path, abs_path)
        except Exception as e:
            # Clean up temp file if update failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise ValueError(f"Failed to update file: {str(e)}")
        
        new_checksum = generate_checksum(abs_path)
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "insert_in_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully inserted content into file: {path} {position_description}\nOriginal checksum: {original_checksum}\nNew checksum: {new_checksum}{commit_result}"

    @with_error_handling
    @mcp.tool()
    async def file_exists(path: str) -> str:
        """
        Check if a file exists at the specified path.
        
        Args:
            path: Path to check for file existence
            
        Returns:
            str: Status message indicating whether the file exists
            
        Raises:
            ValueError: If path validation fails
        """
        try:
            # Validate path (but don't require the file to exist)
            abs_path = validate_operation(path, "file_exists", check_exists=False)
            
            # Check if path exists and is a file
            if os.path.exists(abs_path):
                if os.path.isfile(abs_path):
                    # Get file info for additional details
                    file_size = os.path.getsize(abs_path)
                    checksum = generate_checksum(abs_path)
                    return f"File exists: {path}\nSize: {file_size} bytes\nChecksum: {checksum}"
                elif os.path.isdir(abs_path):
                    return f"Path exists but is a directory, not a file: {path}"
                else:
                    return f"Path exists but is neither a file nor a directory: {path}"
            else:
                return f"File does not exist: {path}"
                
        except Exception as e:
            return f"Error checking file existence: {str(e)}"

    @with_error_handling
    @mcp.tool()
    async def delete_multiple_files(paths: list[str], commit_message: str = None) -> str:
        """
        Delete multiple files from the specified paths.
        
        Args:
            paths: List of paths to the files to delete
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Success and failure summary
            
        Raises:
            ValueError: If parameter validation fails
        """
        if not paths:
            raise ValueError("No file paths provided")
        
        # Track results
        successful_deletions = []
        failed_deletions = []
        deleted_files = []  # For Git commit tracking
        
        # Process each file deletion
        for path in paths:
            try:
                # Validate path
                abs_path = validate_operation(path, "delete_file")
                
                # Check if path exists
                if not os.path.exists(abs_path):
                    failed_deletions.append(f"{path} (file does not exist)")
                    continue
                
                # Check if it's a file (not a directory)
                if os.path.isdir(abs_path):
                    failed_deletions.append(f"{path} (is a directory, not a file)")
                    continue
                
                if not os.path.isfile(abs_path):
                    failed_deletions.append(f"{path} (is not a regular file)")
                    continue
                
                # Attempt to delete the file
                try:
                    os.remove(abs_path)
                    successful_deletions.append(path)
                    deleted_files.append(abs_path)
                except Exception as e:
                    failed_deletions.append(f"{path} (failed to delete: {str(e)})")
                    
            except Exception as e:
                failed_deletions.append(f"{path} (error: {str(e)})")
        
        # Prepare result summary
        total_files = len(paths)
        success_count = len(successful_deletions)
        failure_count = len(failed_deletions)
        
        result_lines = [f"Delete operation completed: {success_count}/{total_files} files deleted successfully"]
        
        if successful_deletions:
            result_lines.append("\nSuccessfully deleted files:")
            for path in successful_deletions:
                result_lines.append(f"  ✓ {path}")
        
        if failed_deletions:
            result_lines.append(f"\nFailed to delete {failure_count} files:")
            for failure in failed_deletions:
                result_lines.append(f"  ✗ {failure}")
        
        # Auto-commit if enabled and there were successful deletions
        if deleted_files:
            commit_result = ""
            try:
                # Use the first deleted file's directory for Git operations
                commit_path = os.path.dirname(deleted_files[0]) if deleted_files else "."
                commit = auto_commit_changes(commit_path, "delete_multiple_files", commit_message)
                if commit:
                    commit_result = f"\n{commit}"
            except GitError as e:
                commit_result = f"\nNote: {str(e)}"
            
            if commit_result:
                result_lines.append(commit_result)
        
        return "\n".join(result_lines)

    @with_error_handling
    @mcp.tool()
    async def replace_all_emojis_in_files(file_paths: list[str], emoji_mapping: Dict[str, str] = None, commit_message: str = None) -> str:
        """
        Replace all emoji occurrences in multiple text files with text representations.
        
        This tool processes multiple files to replace Unicode emoji characters with
        their text equivalents, helping to resolve encoding issues and improve
        text compatibility across different systems.
        
        Default Emoji Mapping (125+ patterns - expanded from docs/missing_emoji_mappings.md):
        
        Status & Actions: 🔧 -> [API], ⚡ -> [FAST], 🚀 -> [PERF], 📦 -> [PKG], 🎯 -> [TARGET], 
        🔒 -> [SEC], 💡 -> [TIP], 🔥 -> [FIRE], 💪 -> [STRONG], 🧪 -> [TEST]
        
        Files & Data: 📁 -> [DIR], 📂 -> [FOLDER], 📄 -> [FILE], 📝 -> [NOTE], 📋 -> [LIST], 
        📖 -> [BOOK], 📊 -> [CHART], 📈 -> [CHART], 📉 -> [CHART]
        
        Technology & Devices: 💻 -> [COMP], 🖥️ -> [DESKTOP], 📱 -> [MOBILE], 🐳 -> [DOCKER], 
        🌐 -> [NET], 📶 -> [NET], 🔌 -> [PLUG], ⚙️ -> [GEAR]
        
        Results & Status: ✅ -> [PASS], ❌ -> [FAIL], ⚠️ -> [WARN], ℹ️ -> [INFO], 
        ❓ -> [QUESTION], ❗ -> [EXCLAIM2], 🚨 -> [ERR], 🎉 -> [SUCCESS]
        
        Intelligence & Processing: 🧠 -> [MEMORY], 🧮 -> [COMPUTE], 🤖 -> [BOT], 🔮 -> [PREDICT]
        
        Connection & Flow: 🔗 -> [LINK], 🔄 -> [CYCLE], 🔁 -> [REPEAT], 🔂 -> [REPEAT_ONE], 
        🔃 -> [VERTICAL]
        
        Places & Environment: 🏠 -> [HOST], 🏆 -> [AWARD], 🎪 -> [STRATEGY], 🏢 -> [OFFICE], 
        🏭 -> [FACTORY]
        
        Tools & Objects: 🧹 -> [CLEANUP], 🗑️ -> [GARBAGE], ✍️ -> [WRITE], 🖊️ -> [PEN], 
        🔨 -> [BUILD]
        
        Programming Languages: 🐼 -> [PANDAS], 🐍 -> [PYTHON], 🐧 -> [LINUX], 🦀 -> [RUST]
        
        Navigation: ➡️ -> [RIGHT], ⬅️ -> [LEFT], ⬆️ -> [UP], ⬇️ -> [DOWN]
        
        Communication: 💬 -> [COMMENT], 💭 -> [THOUGHT], 🗨️ -> [SPEAK], 📞 -> [PHONE], 
        📧 -> [EMAIL]
        
        And 90+ more comprehensive patterns for complete emoji coverage!
        
        Args:
            file_paths: List of paths to the text files to process
            emoji_mapping: Optional custom emoji mapping dictionary that will be merged 
                          with the default mapping. Any emoji in this dictionary will 
                          override the default replacement for that emoji, and new 
                          emojis will be added to the mapping. The default mapping 
                          remains intact for all other emojis.
            commit_message: Custom Git commit message (optional)
            
        Returns:
            str: Summary of processing results including files processed, 
                 total replacements made, and any errors encountered
                 
        Raises:
            ValueError: If file paths are invalid, files are binary, or processing fails
            
        Security Notes:
            - Only processes text files (binary files are rejected for security)
            - Validates all file paths to prevent directory traversal attacks
            - Uses atomic file operations to prevent data corruption
            - Maintains file checksums for integrity verification
        """
        # Validate input parameters
        if not file_paths:
            raise ValueError("No file paths provided")
        
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list of strings")
        
        # Default comprehensive emoji mapping based on docs/fix_emojis.py
        default_emoji_mapping = {
            # Basic status indicators
            '\U0001f527': '[API]',      # 🔧 wrench
            '\U000026a1': '[FAST]',     # ⚡ lightning
            '\U0001f680': '[PERF]',     # 🚀 rocket
            '\U0001f4e6': '[PKG]',      # 📦 package
            '\U0001f4ca': '[CHART]',    # 📊 chart
            '\U0001f4c8': '[CHART]',    # 📈 chart increasing
            '\U0001f4c9': '[CHART]',    # 📉 chart decreasing
            '\U0001f3af': '[TARGET]',   # 🎯 target
            '\U0001f512': '[SEC]',      # 🔒 lock
            '\U0001f30d': '[GLOBAL]',   # 🌍 globe
            '\U0001f30e': '[WEB]',      # 🌎 globe
            '\U0001f4f6': '[NET]',      # 📶 network
            '\U0001f310': '[NET]',      # 🌐 network
            '\U0001f4a1': '[TIP]',      # 💡 bulb
            '\U0001f3c1': '[FINAL]',    # 🏁 checkered flag
            '\U0001f389': '[SUCCESS]',  # 🎉 party
            '\U0001f38a': '[DONE]',     # 🎊 confetti
            '\U0001f40c': '[SLOW]',     # 🐌 snail
            '\U0001f433': '[DOCKER]',   # 🐳 whale
            '\U0001f6e1\ufe0f': '[SHIELD]', # 🛡️ shield
            '\U0001f6e1': '[SHIELD]',   # 🛡 shield
            '\U0001f6a8': '[ERR]',      # 🚨 siren
            '\U0001f50d': '[SEARCH]',   # 🔍 magnifying glass
            '\U0001f514': '[CONN]',     # 🔔 bell
            '\U0001f525': '[FIRE]',     # 🔥 fire
            '\U0001f4aa': '[STRONG]',   # 💪 muscle
            '\U0001f9ea': '[TEST]',     # 🧪 test tube
            '\U0001f4dd': '[NOTE]',     # 📝 memo
            '\U0001f4cb': '[LIST]',     # 📋 clipboard
            '\U0001f4c4': '[FILE]',     # 📄 document
            '\U0001f4c1': '[DIR]',      # 📁 folder
            '\U0001f4c2': '[FOLDER]',   # 📂 open folder
            '\U0001f4d6': '[BOOK]',     # 📖 book
            '\U0001f4bb': '[COMP]',     # 💻 computer
            '\U0001f5a5\ufe0f': '[DESKTOP]', # 🖥️ desktop
            '\U0001f5a5': '[DESKTOP]',  # 🖥 desktop
            '\U0001f4f1': '[MOBILE]',   # 📱 mobile
            '\U000023f1\ufe0f': '[TIMER]', # ⏱️ timer
            '\U000023f1': '[TIMER]',    # ⏱ timer
            '\U0001f552': '[TIME]',     # 🕒 clock
            '\U0001f195': '[NEW]',      # 🆕 new
            '\U0001f199': '[UP]',       # 🆙 up
            '\U0001f19a': '[VS]',       # 🆚 vs
            '\U0001f4a5': '[BOOM]',     # 💥 explosion
            '\U0001f525': '[HOT]',      # 🔥 fire
            '\U00002744\ufe0f': '[COLD]', # ❄️ snowflake
            '\U00002744': '[COLD]',     # ❄ snowflake
            '\U0001f522': '[NUMS]',     # 🔢 numbers
            '\U0001f523': '[SYMBOLS]',  # 🔣 symbols
            '\U0001f524': '[ABC]',      # 🔤 letters
            '\U00002699\ufe0f': '[GEAR]', # ⚙️ gear
            '\U00002699': '[GEAR]',     # ⚙ gear
            '\U00002696\ufe0f': '[BALANCE]', # ⚖️ balance
            '\U00002696': '[BALANCE]',  # ⚖ balance
            '\U0001f4e4': '[OUTBOX]',   # 📤 outbox
            '\U0001f4e5': '[INBOX]',    # 📥 inbox
            '\U0001f4ed': '[EMPTY]',    # 📭 mailbox
            '\U0001f4ec': '[MAIL]',     # 📬 mailbox
            '\U0001f4ea': '[MAILBOX]',  # 📪 closed mailbox
            '\U0001f4e8': '[ENVELOPE]', # 📨 envelope
            '\U0001f194': '[ID]',       # 🆔 ID
            '\U0001f50c': '[PLUG]',     # 🔌 plug
            '\U0001f4de': '[PHONE]',    # 📞 telephone
            '\U0001f4e0': '[FAX]',      # 📠 fax
            '\U0001f4fc': '[VHS]',      # 📼 videocassette
            '\U0001f4fd\ufe0f': '[FILM]', # 📽️ film projector
            '\U0001f4fd': '[FILM]',     # 📽 film projector
            '\U0001f3a5': '[CAMERA]',   # 🎥 movie camera
            '\U0001f4f7': '[PHOTO]',    # 📷 camera
            '\U0001f4f8': '[FLASH]',    # 📸 camera with flash
            '\U0001f50e': '[ZOOM]',     # 🔎 magnifying glass
            '\U0001f50f': '[LOCK]',     # 🔏 lock with pen
            '\U0001f510': '[UNLOCK]',   # 🔐 lock with key
            '\U0001f511': '[KEY]',      # 🔑 key
            '\U0001f513': '[OPEN]',     # 🔓 unlocked
            '\U0001f6aa': '[DOOR]',     # 🚪 door
            '\U0001f4ac': '[COMMENT]',  # 💬 speech balloon
            '\U0001f4ad': '[THOUGHT]',  # 💭 thought balloon
            '\U0001f5e8\ufe0f': '[SPEAK]', # 🗨️ left speech bubble
            '\U0001f5e8': '[SPEAK]',    # 🗨 left speech bubble
            '\U0001f5ef\ufe0f': '[ANGRY]', # 🗯️ right anger bubble
            '\U0001f5ef': '[ANGRY]',    # 🗯 right anger bubble
            '\U0001f4f0': '[NEWS]',     # 📰 newspaper
            '\U0001f4f3': '[VIBRATE]',  # 📳 vibration mode
            '\U0001f4f4': '[SILENT]',   # 📴 mobile phone off
            '\U0001f4f5': '[NO_MOBILE]', # 📵 no mobile phones
            '\U0001f4f6': '[SIGNAL]',   # 📶 antenna bars
            '\U0001f4f7': '[CAMERA2]',  # 📷 camera
            '\U0001f4f9': '[VIDEO]',    # 📹 video camera
            '\U0001f4fa': '[TV]',       # 📺 television
            '\U0001f4fb': '[RADIO]',    # 📻 radio
            '\U0001f4fc': '[TAPE]',     # 📼 videocassette
            '\U0001f50a': '[LOUD]',     # 🔊 speaker high volume
            '\U0001f50b': '[LOW]',      # 🔋 battery
            '\U0001f50c': '[ELECTRIC]', # 🔌 electric plug
            '\U0001f4af': '[100]',      # 💯 hundred points
            
            # Add checkmark and X emojis
            '\u2705': '[PASS]',         # ✅ check mark
            '\u274c': '[FAIL]',         # ❌ cross mark
            '\u26a0\ufe0f': '[WARN]',   # ⚠️ warning
            '\u26a0': '[WARN]',         # ⚠ warning
            '\u2139\ufe0f': '[INFO]',   # ℹ️ information
            '\u2139': '[INFO]',         # ℹ information
            '\u2753': '[QUESTION]',     # ❓ question mark
            '\u2754': '[QUESTION2]',    # ❔ white question mark
            '\u2755': '[EXCLAIM]',      # ❕ white exclamation mark
            '\u2757': '[EXCLAIM2]',     # ❗ exclamation mark
            '\u27a1\ufe0f': '[RIGHT]',  # ➡️ right arrow
            '\u27a1': '[RIGHT]',        # ➡ right arrow
            '\u2b05\ufe0f': '[LEFT]',   # ⬅️ left arrow
            '\u2b05': '[LEFT]',         # ⬅ left arrow
            '\u2b06\ufe0f': '[UP]',     # ⬆️ up arrow
            '\u2b06': '[UP]',           # ⬆ up arrow
            '\u2b07\ufe0f': '[DOWN]',   # ⬇️ down arrow
            '\u2b07': '[DOWN]',         # ⬇ down arrow
            
            # Missing emoji mappings from docs/missing_emoji_mappings.md
            # Brain/Intelligence Category
            '\U0001f9e0': '[MEMORY]',   # 🧠 brain
            '\U0001f9ee': '[COMPUTE]',  # 🧮 abacus
            '\U0001f916': '[BOT]',      # 🤖 robot
            '\U0001f52e': '[PREDICT]',  # 🔮 crystal ball
            
            # Connection/Process Category
            '\U0001f517': '[LINK]',     # 🔗 link
            '\U0001f504': '[CYCLE]',    # 🔄 counterclockwise arrows
            '\U0001f501': '[REPEAT]',   # 🔁 repeat button
            '\U0001f502': '[REPEAT_ONE]', # 🔂 repeat single
            '\U0001f503': '[VERTICAL]', # 🔃 clockwise vertical arrows
            
            # Places/Environment Category
            '\U0001f3e0': '[HOST]',     # 🏠 house
            '\U0001f3c6': '[AWARD]',    # 🏆 trophy
            '\U0001f3aa': '[STRATEGY]', # 🎪 circus tent
            '\U0001f3e2': '[OFFICE]',   # 🏢 office building
            '\U0001f3ed': '[FACTORY]',  # 🏭 factory
            
            # Tools/Objects Category
            '\U0001f9f9': '[CLEANUP]',  # 🧹 broom
            '\U0001f5d1\ufe0f': '[GARBAGE]', # 🗑️ wastebasket
            '\U0001f5d1': '[GARBAGE]',  # 🗑 wastebasket
            '\u270d\ufe0f': '[WRITE]',  # ✍️ writing hand
            '\u270d': '[WRITE]',        # ✍ writing hand
            '\U0001f58a\ufe0f': '[PEN]', # 🖊️ pen
            '\U0001f58a': '[PEN]',      # 🖊 pen
            '\U0001f528': '[BUILD]',    # 🔨 hammer
            
            # Animals Category (Context-Specific)
            '\U0001f43c': '[PANDAS]',   # 🐼 panda
            '\U0001f40d': '[PYTHON]',   # 🐍 snake
            '\U0001f427': '[LINUX]',    # 🐧 penguin
            '\U0001f980': '[RUST]',     # 🦀 crab
            
            # Symbols and Punctuation
            '\u2022': '-',              # • bullet point to dash
        }
        
        # Start with default mapping and merge/override with custom mapping if provided
        active_mapping = default_emoji_mapping.copy()
        
        if emoji_mapping is not None:
            if not isinstance(emoji_mapping, dict):
                raise ValueError("emoji_mapping must be a dictionary")
            # Update default mapping with custom mappings (overrides existing, adds new)
            active_mapping.update(emoji_mapping)
        
        # Track processing results
        successful_files = []
        failed_files = []
        total_replacements = 0
        processed_file_paths = []  # For Git commit tracking
        
        # Process each file
        for file_path in file_paths:
            try:
                # Validate file path and security checks
                abs_path = validate_operation(file_path, "replace_all_emojis_in_files", check_binary=True)
                
                # Check if file exists and is a text file
                if not os.path.exists(abs_path):
                    failed_files.append(f"{file_path} (file does not exist)")
                    continue
                
                if not os.path.isfile(abs_path):
                    failed_files.append(f"{file_path} (not a regular file)")
                    continue
                
                # Get original file info
                original_checksum = generate_checksum(abs_path)
                file_size = os.path.getsize(abs_path)
                
                # Read file content with proper error handling
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    failed_files.append(f"{file_path} (binary file - text files only)")
                    continue
                except Exception as e:
                    failed_files.append(f"{file_path} (read error: {str(e)})")
                    continue
                
                # Track changes for this file
                original_content = content
                file_replacements = 0
                
                # Apply emoji replacements
                for emoji_char, replacement in active_mapping.items():
                    if emoji_char in content:
                        count = content.count(emoji_char)
                        content = content.replace(emoji_char, replacement)
                        file_replacements += count
                
                # Only write file if changes were made
                if file_replacements > 0:
                    # Validate new content size
                    if len(content) > MAX_FILE_SIZE:
                        failed_files.append(f"{file_path} (resulting file too large: {len(content)} bytes)")
                        continue
                    
                    # Use atomic write operation with proper error handling
                    temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
                    try:
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        os.replace(temp_path, abs_path)
                    except Exception as e:
                        # Clean up temp file if write failed
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                        failed_files.append(f"{file_path} (write error: {str(e)})")
                        continue
                    
                    # Verify write was successful
                    new_checksum = generate_checksum(abs_path)
                    successful_files.append(f"{file_path} ({file_replacements} replacements)")
                    total_replacements += file_replacements
                    processed_file_paths.append(abs_path)
                else:
                    # No emojis found, but file was processed successfully
                    successful_files.append(f"{file_path} (no emojis found)")
                    
            except Exception as e:
                failed_files.append(f"{file_path} (error: {str(e)})")
        
        # Prepare result summary
        total_files = len(file_paths)
        success_count = len(successful_files)
        failure_count = len(failed_files)
        
        result_lines = [
            f"Emoji replacement completed: {success_count}/{total_files} files processed successfully",
            f"Total emoji replacements made: {total_replacements}"
        ]
        
        if successful_files:
            result_lines.append("\nSuccessfully processed files:")
            for file_info in successful_files:
                result_lines.append(f"  ✓ {file_info}")
        
        if failed_files:
            result_lines.append(f"\nFailed to process {failure_count} files:")
            for file_info in failed_files:
                result_lines.append(f"  ✗ {file_info}")
        
        # Auto-commit if enabled and there were successful replacements
        if processed_file_paths:
            commit_result = ""
            try:
                # Use the first processed file's directory for Git operations
                commit_path = os.path.dirname(processed_file_paths[0]) if processed_file_paths else "."
                commit = auto_commit_changes(commit_path, "replace_all_emojis_in_files", commit_message)
                if commit:
                    commit_result = f"\n{commit}"
            except GitError as e:
                commit_result = f"\nNote: {str(e)}"
            
            if commit_result:
                result_lines.append(commit_result)
        
        # Add information about the emoji mapping used
        if emoji_mapping is not None:
            overrides = len([k for k in emoji_mapping.keys() if k in default_emoji_mapping])
            additions = len([k for k in emoji_mapping.keys() if k not in default_emoji_mapping])
            mapping_info = f"\nUsed emoji mapping: Default mapping ({len(default_emoji_mapping)} patterns) + Custom overrides ({overrides} patterns) + Custom additions ({additions} patterns) = {len(active_mapping)} total patterns"
        else:
            mapping_info = f"\nUsed emoji mapping: Default mapping with {len(active_mapping)} emoji patterns"
        result_lines.append(mapping_info)
        
        return "\n".join(result_lines)

    @with_error_handling
    @mcp.tool()
    async def replace_all_in_file(path: str, new_string: Union[str, Dict[str, Any], list, int, float, bool] = None, old_string: Union[str, Dict[str, Any], list, int, float, bool] = None, commit_message: str = None, new_str: Union[str, Dict[str, Any], list, int, float, bool] = None, old_str: Union[str, Dict[str, Any], list, int, float, bool] = None) -> str:
        """
        Replace ALL occurrences of specific text within a file.
        
        This function replaces every instance of the old_string with new_string throughout the entire file.
        Unlike some text editors that only replace the first occurrence, this tool replaces all matches.
        
        Args:
            path: Path to the file to update
            new_string: Replacement text or object. If an object is provided, it will be serialized as JSON.
            old_string: Text or object to find and replace. If an object is provided, it will be serialized as JSON.
            commit_message: Custom Git commit message (optional)
            new_str: Alternative parameter name for new_string (backup for LLM compatibility)
            old_str: Alternative parameter name for old_string (backup for LLM compatibility)
            
        Returns:
            str: Success message with replacement count and checksum information
            
        Raises:
            ValueError: If file update fails or parameters are invalid
        """
        abs_path = validate_operation(path, "replace_all_in_file", check_binary=True)
        
        # Handle backup parameters for LLM compatibility
        # Use old_str as backup if old_string is not provided or is None
        if old_string is None and old_str is not None:
            old_string = old_str
        elif old_string is None and old_str is None:
            raise ValueError("Either old_string or old_str must be provided")
            
        # Use new_str as backup if new_string is not provided or is None
        if new_string is None and new_str is not None:
            new_string = new_str
        elif new_string is None and new_str is None:
            raise ValueError("Either new_string or new_str must be provided")
        
        # Validate content inputs
        if not old_string:
            raise ValueError("Old content cannot be empty")

        # Convert old_string to string appropriately
        old_string = sanitize_file_string(old_string)
        
        # Convert new_string to string appropriately
        new_string = sanitize_file_string(new_string)
            
        if '\0' in new_string:
            raise ValueError("Cannot replace with binary content")
            
        original_checksum = generate_checksum(abs_path)
        
        # Read file with proper error handling
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError(f"File {path} is not a valid text file")
        
        if old_string not in content:
            raise ValueError(f"The specified text to replace was not found in {path}")
        
        # Count occurrences before replacement for reporting
        occurrence_count = content.count(old_string)
        
        # Replace ALL occurrences of old_string with new_string
        updated_content = content.replace(old_string, new_string)
        
        # Validate new size
        if len(updated_content) > MAX_FILE_SIZE:
            raise ValueError(f"Updated content would be too large ({len(updated_content)} bytes). Maximum size is {MAX_FILE_SIZE} bytes.")
        
        # Use atomic write operation with proper error handling
        temp_path = f"{abs_path}.tmp.{os.getpid()}.{int(time.time())}"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            os.replace(temp_path, abs_path)
        except Exception as e:
            # Clean up temp file if update failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise ValueError(f"Failed to update file: {str(e)}")
        
        new_checksum = generate_checksum(abs_path)
        
        # Auto-commit if enabled
        commit_result = ""
        try:
            commit = auto_commit_changes(abs_path, "replace_all_in_file", commit_message)
            if commit:
                commit_result = f"\n{commit}"
        except GitError as e:
            commit_result = f"\nNote: {str(e)}"
        
        return f"Successfully replaced all occurrences in file: {path}\nReplacements made: {occurrence_count}\nOriginal checksum: {original_checksum}\nNew checksum: {new_checksum}{commit_result}"
