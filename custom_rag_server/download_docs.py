"""
Download LangChain documentation for RAG indexing.
Run once before starting the custom RAG server:

    python custom_rag_server/download_docs.py

Shallow-clones the LangChain monorepo (depth=1) and collects all .md/.mdx
files from the libs/ subdirectory into langchain_docs/.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEST = Path("langchain_docs")
REPO = "https://github.com/langchain-ai/langchain.git"
# Subfolder(s) to harvest — checked in order; first one that has .md files wins
_CANDIDATES = ["docs", "libs", "."]


def _run(cmd: list, label: str) -> None:
    print(f"  {label}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
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

    print("Shallow-cloning LangChain repo (depth=1)...")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _run(
            ["git", "clone", "--depth=1", "--no-tags", REPO, tmp],
            label="cloning (this may take 1-2 min)",
        )

        # Find whichever subfolder has the most .md files
        best_src = None
        best_count = 0
        for candidate in _CANDIDATES:
            src = tmp_path / candidate if candidate != "." else tmp_path
            if not src.exists():
                continue
            count = len(list(src.rglob("*.md"))) + len(list(src.rglob("*.mdx")))
            print(f"  Found {count} docs in {candidate}/")
            if count > best_count:
                best_count = count
                best_src = src

        if not best_src or best_count == 0:
            print("ERROR: No markdown files found in repo at all.", file=sys.stderr)
            sys.exit(1)

        print(f"  Copying {best_count} files to langchain_docs/...")
        DEST.mkdir(parents=True)
        for md_file in list(best_src.rglob("*.md")) + list(best_src.rglob("*.mdx")):
            rel = md_file.relative_to(best_src)
            dest_file = DEST / rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md_file, dest_file)

    mdx = len(list(DEST.rglob("*.mdx")))
    md = len(list(DEST.rglob("*.md")))
    print(f"\nDone. {mdx + md} files in langchain_docs/ ({mdx} .mdx + {md} .md)")
    print("Now run:  python -m custom_rag_server.main")


if __name__ == "__main__":
    main()
