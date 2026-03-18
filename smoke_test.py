"""
smoke_test.py
Quick manual verification that all tools work end to end.
Run with: python3 smoke_test.py
"""

import tempfile
from tools import ToolRegistry, ToolExecutor
from tools import ReadFileTool, WriteFileTool, EditFileTool, RunShellTool

# Setup 
ws = tempfile.mkdtemp()
print(f"\n📁 Workspace: {ws}\n")
print("=" * 55)

registry = ToolRegistry()
registry.register(ReadFileTool(workspace_root=ws))
registry.register(WriteFileTool(workspace_root=ws))
registry.register(EditFileTool(workspace_root=ws))
registry.register(RunShellTool(workspace_root=ws))

executor = ToolExecutor(registry=registry, workspace_root=ws, safe_mode=False)


def show(label, result):
    status = "✅" if result["status"] == "success" else "❌"
    print(f"\n{status}  {label}")
    key = "output" if result["status"] == "success" else "message"
    print(f"   {result[key][:200]}")
    print("-" * 55)


# 1. Write a file
show("write_file — create hello.py", executor.execute("write_file", {
    "path": "hello.py",
    "content": "def greet():\n    print('hello world!')\n\ngreet()\n"
}))

# 2. Read it back 
show("read_file — read hello.py", executor.execute("read_file", {
    "path": "hello.py"
}))

# 3. Edit it    
show("edit_file — exact match", executor.execute("edit_file", {
    "path":          "hello.py",
    "search_block":  "    print('hello world!')",
    "replace_block": "    print('hello from edit_file!')"
}))

# 4. Run it     
show("run_shell — python3 hello.py", executor.execute("run_shell", {
    "command": "python3 hello.py"
}))

# 5. Write a subdir file 
show("write_file — create subdirectory", executor.execute("write_file", {
    "path":    "src/utils.py",
    "content": "def add(a, b):\n    return a + b\n"
}))

# 6. Run shell — list files 
show("run_shell — ls", executor.execute("run_shell", {
    "command": "ls"
}))

# 7. Edit with whitespace-normalized match 
executor.execute("write_file", {
    "path":    "messy.py",
    "content": "def   compute( x ):\n    return  x  +  1\n"
})
show("edit_file — whitespace normalized match", executor.execute("edit_file", {
    "path":          "messy.py",
    "search_block":  "def compute(x):\n    return x + 1",
    "replace_block": "def compute(x):\n    return x * 2"
}))

# 8. Read nonexistent file 
show("read_file — missing file (expect error)", executor.execute("read_file", {
    "path": "does_not_exist.py"
}))

# 9. Path traversal blocked 
show("read_file — path traversal (expect error)", executor.execute("read_file", {
    "path": "../../etc/passwd"
}))

# 10. Dangerous command blocked 
show("run_shell — rm -rf / (expect error)", executor.execute("run_shell", {
    "command": "rm -rf /"
}))

# 11. Edit no match 
show("edit_file — no match (expect error + tip)", executor.execute("edit_file", {
    "path":          "hello.py",
    "search_block":  "THIS DOES NOT EXIST IN THE FILE",
    "replace_block": "anything"
}))

print("\n✅ Smoke test complete.\n")