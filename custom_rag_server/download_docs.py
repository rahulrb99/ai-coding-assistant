"""
Download a sample of LangChain documentation (.mdx files) for RAG indexing.
Run once before starting the custom RAG server:

    python custom_rag_server/download_docs.py

This clones only the docs/ folder from the LangChain repo using a sparse checkout
so it doesn't download the entire monorepo (~2 GB).
"""
import subprocess
import sys
from pathlib import Path

DEST = Path("langchain_docs")
REPO = "https://github.com/langchain-ai/langchain.git"
SPARSE_PATH = "docs/docs"  # subfolder inside the repo that has .mdx files


def main() -> None:
    if DEST.exists() and any(DEST.rglob("*.mdx")):
        mdx_count = len(list(DEST.rglob("*.mdx")))
        print(f"langchain_docs/ already exists with {mdx_count} .mdx files. Nothing to do.")
        return

    print("Cloning LangChain docs (sparse checkout — docs folder only)...")
    DEST.mkdir(exist_ok=True)

    cmds = [
        ["git", "init"],
        ["git", "remote", "add", "origin", REPO],
        ["git", "sparse-checkout", "init", "--cone"],
        ["git", "sparse-checkout", "set", SPARSE_PATH],
        ["git", "pull", "origin", "master", "--depth=1"],
    ]

    for cmd in cmds:
        print(f"  $ {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(DEST), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)

    mdx_files = list(DEST.rglob("*.mdx"))
    print(f"\nDone. {len(mdx_files)} .mdx files downloaded to {DEST}/")
    print("Now run:  python -m custom_rag_server.main")


if __name__ == "__main__":
    main()
