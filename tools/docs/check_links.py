"""Checks that every relative link in the repository's Markdown files points to an existing file.

    python tools/docs/check_links.py          # exit code 1 and the list of broken links if any

Part of tools/check.sh (stage "python"). URLs and in-page anchors are not checked.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

SKIP = {"node_modules", ".git", ".check", "dist", "__pycache__", ".pytest_cache"}
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE = re.compile(r"`[^`]*`")


def links_in(text: str) -> list[str]:
    """Relative link targets of a Markdown text, without anchors; inline code is ignored."""
    out = []
    for target in LINK.findall(CODE.sub("", text)):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue
        out.append(target.split("#", 1)[0])
    return [t for t in out if t]


def broken_links(root: Path) -> list[tuple[str, str]]:
    broken = []
    for md in sorted(root.rglob("*.md")):
        if any(part in SKIP for part in md.relative_to(root).parts):
            continue
        for target in links_in(md.read_text(encoding="utf-8")):
            if not (md.parent / unquote(target)).exists():
                broken.append((md.relative_to(root).as_posix(), target))
    return broken


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    broken = broken_links(root)
    for source, target in broken:
        print(f"broken link in {source}: {target}")
    print(f"{len(broken)} broken link(s)")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
