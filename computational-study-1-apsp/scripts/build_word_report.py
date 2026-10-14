"""Convert docs/comparison_report.md to docs/comparison_report.docx (tables and figures included).

    python scripts/build_word_report.py

Requires pandoc (https://pandoc.org; on macOS: brew install pandoc). Image paths in the Markdown
are relative to docs/, so pandoc is run with docs/ as its resource path.

Title block convention in the Markdown: the single "# Title" line, then (until the first blank
line) the author in **bold**, a subtitle line, and a date line. In the Word file these become the
document's title, author, subtitle and date, placed on the first page ABOVE the table of contents.
"""

import shutil
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def split_title_block(markdown):
    """Return (title, author, subtitle, date, body) from the report's first lines."""
    lines = markdown.splitlines()
    assert lines[0].startswith("# "), "report must start with a single '# Title' line"
    title = lines[0][2:].strip()
    block = []
    i = 2  # line 1 is blank
    while i < len(lines) and lines[i].strip():
        block.append(lines[i].strip().strip("*").rstrip())
        i += 1
    author, subtitle, date = (block + ["", "", ""])[:3]
    return title, author, subtitle, date, "\n".join(lines[i:])


def main():
    if shutil.which("pandoc") is None:
        sys.exit("pandoc not found: install it from https://pandoc.org (macOS: brew install pandoc)")
    src, out = DOCS / "comparison_report.md", DOCS / "comparison_report.docx"
    title, author, subtitle, date, body = split_title_block(src.read_text())
    subprocess.run(["pandoc", "-", "-o", str(out), "--resource-path", str(DOCS),
                    "--from", "gfm", "--toc", "--toc-depth=2",
                    "--shift-heading-level-by=-1",  # "## 1. Summary" becomes a level-1 heading
                    "--metadata", f"title={title}", "--metadata", f"author={author}",
                    "--metadata", f"subtitle={subtitle}", "--metadata", f"date={date}"],
                   input=body, text=True, check=True)
    print(f"Wrote {out.relative_to(DOCS.parent)}")


if __name__ == "__main__":
    main()
