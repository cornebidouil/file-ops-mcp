# FileOps Essential Rules

## Before Any File Operation
1. **Explore first**: Use `get_tree`, `list_dir`, `search_files` to understand project structure
2. **Read before modify**: Use `read_file` or `read_multiple_files` to check existing content
3. **Verify paths**: Check if directories exist before creating files; use `create_dir` if needed

## File Operations
4. **Complete code only**: Never use placeholders - write full, working code
5. **Use appropriate method**:
   - New files: `create_file` 
   - Line edits: `update_file` or `insert_in_file`
   - Large files: `create_file` + `append_to_file`
   - Documentation: `update_file`
6. **Batch reads**: Use `read_multiple_files` for related files, not individual `read_file` calls

## Quality & Organization  
7. **Always commit**: Provide explicit commit messages
8. **Proper structure**: Place tests/examples in correct folders
9. **Handle emoji**: Avoid emoji in code (encoding issues); use `replace_all_emojis_in_files` if cleanup needed
10. **No analysis tool**: Don't use data analysis when using FileOps

## Communication
11. **Discuss architecture**: Get approval for major design decisions
12. **Provide commands**: Give full paths and exact terminal commands when needed