"""
Download LangChain documentation for RAG indexing.
Run once before starting the custom RAG server:

    python custom_rag_server/download_docs.py

Shallow-clones (~150 MB) the LangChain repo into a temp folder,
copies only the docs/ subfolder to langchain_docs/, then deletes the clone.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEST = Path("langchain_docs")
REPO = "https://github.com/langchain-ai/langchain.git"


def _run(cmd: list, cwd: str, label: str) -> None:
    print(f"  {label}...")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if DEST.exists():
        total = len(list(DEST.rglob("*.mdx"))) + len(list(DEST.rglob("*.md")))
        if total > 0:
            print(f"langchain_docs/ already has {total} docs. Nothing to do.")
            return
        print("langchain_docs/ exists but is empty — removing and re-downloading.")
        shutil.rmtree(DEST)

    print("Shallow-cloning LangChain repo (depth=1, ~150 MB)...")
    with tempfile.TemporaryDirectory() as tmp:
        _run(
            ["git", "clone", "--depth=1", "--no-tags", REPO, tmp],
            cwd=".",
            label="cloning (this takes ~1-2 min on a slow connection)",
        )

        # Find the docs folder (could be docs/ or docs/docs/)
        for candidate in ["docs/docs", "docs"]:
            src = Path(tmp) / candidate
            if src.exists() and any(src.rglob("*.md")):
                print(f"  Found docs at {candidate}/ — copying to langchain_docs/")
                shutil.copytree(src, DEST)
                break
        else:
            print("ERROR: Could not find docs folder in repo.", file=sys.stderr)
            sys.exit(1)

    mdx = len(list(DEST.rglob("*.mdx")))
    md = len(list(DEST.rglob("*.md")))
    print(f"\nDone. {mdx + md} files copied ({mdx} .mdx + {md} .md) to langchain_docs/")
    print("Now run:  python -m custom_rag_server.main")


if __name__ == "__main__":
    main()
