"""Convert docs/comparison_report.md to docs/comparison_report.docx (tables and figures included).

    python scripts/build_word_report.py

Requires pandoc (https://pandoc.org; on macOS: brew install pandoc). Image paths in the Markdown
are relative to docs/, so pandoc is run with docs/ as its resource path.
"""

import shutil
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def main():
    if shutil.which("pandoc") is None:
        sys.exit("pandoc not found: install it from https://pandoc.org (macOS: brew install pandoc)")
    src, out = DOCS / "comparison_report.md", DOCS / "comparison_report.docx"
    subprocess.run(["pandoc", str(src), "-o", str(out), "--resource-path", str(DOCS),
                    "--from", "gfm", "--toc", "--toc-depth=2",
                    "--metadata", "title=Computational Study 1: All-Pairs Shortest Paths"],
                   check=True)
    print(f"Wrote {out.relative_to(DOCS.parent)}")


if __name__ == "__main__":
    main()
