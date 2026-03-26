"""
Download LangChain documentation for RAG indexing.
Run once before starting the custom RAG server:

    python custom_rag_server/download_docs.py

Uses a sparse git checkout to fetch only the docs/ folder (~50 MB vs 2 GB full clone).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEST = Path("langchain_docs")
REPO = "https://github.com/langchain-ai/langchain.git"
BRANCH = "master"
SPARSE_PATH = "docs"


def _run(cmd: list, cwd: str) -> bool:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR running {' '.join(cmd)}: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def main() -> None:
    if DEST.exists():
        mdx = list(DEST.rglob("*.mdx"))
        md = list(DEST.rglob("*.md"))
        total = len(mdx) + len(md)
        if total > 0:
            print(f"langchain_docs/ already has {total} docs ({len(mdx)} .mdx + {len(md)} .md). Nothing to do.")
            return
        print("langchain_docs/ exists but is empty — re-downloading...")
        shutil.rmtree(DEST)

    print("Downloading LangChain docs (sparse checkout)...")
    DEST.mkdir(parents=True)
    cwd = str(DEST)

    steps = [
        (["git", "init"], "initialising repo"),
        (["git", "remote", "add", "origin", REPO], "adding remote"),
        (["git", "sparse-checkout", "init", "--no-cone"], "enabling sparse checkout"),
        (["git", "sparse-checkout", "set", f"{SPARSE_PATH}/"], "setting sparse path"),
        (["git", "fetch", "--depth=1", "origin", BRANCH], "fetching (this may take a minute)..."),
        (["git", "checkout", f"origin/{BRANCH}", "--", f"{SPARSE_PATH}/"], "checking out docs/"),
    ]

    for cmd, label in steps:
        print(f"  {label}...")
        if not _run(cmd, cwd):
            print(f"\nFailed. Try manually:\n  cd {DEST} && git pull", file=sys.stderr)
            sys.exit(1)

    mdx = list(DEST.rglob("*.mdx"))
    md = list(DEST.rglob("*.md"))
    total = len(mdx) + len(md)

    if total == 0:
        print("\nWarning: no .md/.mdx files found. The docs/ path may have changed.")
        print("Check https://github.com/langchain-ai/langchain/tree/master/docs")
    else:
        print(f"\nDone. {total} docs downloaded ({len(mdx)} .mdx + {len(md)} .md) to {DEST}/")
        print("Now run:  python -m custom_rag_server.main")


if __name__ == "__main__":
    main()
