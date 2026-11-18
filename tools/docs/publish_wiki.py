"""Mirrors docs/wiki/ (source of truth, reviewed in pull requests) to the GitHub wiki of ddmp3/EarthMoon.

    python tools/docs/publish_wiki.py            # build, commit and push the wiki
    python tools/docs/publish_wiki.py --dry-run  # build into a temporary folder and list the pages

GitHub wiki pages are flat: docs/wiki/data/moon.md becomes the page "data-moon", docs/wiki/README.md
becomes "Home". Links between wiki pages are rewritten to page names; links to other repository files
become GitHub URLs on main. Never edit the GitHub wiki by hand: the next publication overwrites it.
The wiki repository exists only after a first page was created once in the GitHub web interface.
"""
from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/ddmp3/EarthMoon/blob/main"
WIKI_GIT = "https://github.com/ddmp3/EarthMoon.wiki.git"
LINK = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")
CODE = re.compile(r"`[^`]*`")


def page_name(rel: str) -> str:
    """Flat wiki page name of a path relative to docs/wiki."""
    if rel == "README.md":
        return "Home"
    return rel[:-3].replace("/", "-") if rel.endswith(".md") else rel.replace("/", "-")


def _rewrite_target(target: str, source_rel: str, pages: set[str] | None) -> str:
    if re.match(r"^[a-z]+:", target) or target.startswith("#"):
        return target
    path, _, anchor = target.partition("#")
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source_rel), path))
    suffix = f"#{anchor}" if anchor else ""
    inside_wiki = not resolved.startswith("..")
    is_page = inside_wiki and resolved.endswith(".md") and (pages is None or resolved in pages)
    if is_page:
        return page_name(resolved) + suffix
    repo_path = posixpath.normpath(posixpath.join("docs/wiki", resolved))
    return f"{REPO_URL}/{repo_path}{suffix}"


def rewrite_links(text: str, source_rel: str, pages: set[str] | None = None) -> str:
    """Rewrite the relative links of a page located at docs/wiki/<source_rel>; inline code is left alone."""
    parts, last = [], 0
    for code in CODE.finditer(text):
        parts.append(_rewrite_outside_code(text[last:code.start()], source_rel, pages))
        parts.append(code.group(0))
        last = code.end()
    parts.append(_rewrite_outside_code(text[last:], source_rel, pages))
    return "".join(parts)


def _rewrite_outside_code(text: str, source_rel: str, pages: set[str] | None) -> str:
    return LINK.sub(lambda m: m.group(1) + _rewrite_target(m.group(2), source_rel, pages) + m.group(3), text)


def _title(md: str, fallback: str) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build(src: Path, out: Path, source_commit: str) -> list[str]:
    """Write the flat wiki into `out` (existing .md pages are replaced). Returns the page names."""
    for old in out.glob("*.md"):
        old.unlink()
    rels = sorted(p.relative_to(src).as_posix() for p in src.rglob("*.md"))
    pages = set(rels)
    sidebar = ["**EarthMoon wiki**", ""]
    for rel in rels:
        text = (src / rel).read_text(encoding="utf-8")
        name = page_name(rel)
        (out / f"{name}.md").write_text(rewrite_links(text, rel, pages), encoding="utf-8")
        sidebar.append(f"- [{_title(text, name)}]({name})")
    (out / "_Sidebar.md").write_text("\n".join(sidebar) + "\n", encoding="utf-8")
    (out / "_Footer.md").write_text(
        f"Mirror of [docs/wiki]({REPO_URL}/docs/wiki) at commit `{source_commit}`. Edit the repository, not this wiki.\n",
        encoding="utf-8",
    )
    return [page_name(r) for r in rels]


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    commit = _git("rev-parse", "--short", "HEAD", cwd=root)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "wiki"
        if args.dry_run:
            out.mkdir()
            print("\n".join(build(root / "docs" / "wiki", out, commit)))
            return 0
        try:
            _git("clone", "--depth", "1", WIKI_GIT, str(out))
        except subprocess.CalledProcessError:
            print("The wiki repository does not exist yet: create a 'Home' page once on GitHub, then rerun.", file=sys.stderr)
            return 1
        names = build(root / "docs" / "wiki", out, commit)
        _git("add", "-A", cwd=out)
        if not _git("status", "--porcelain", cwd=out):
            print("wiki already up to date")
            return 0
        # The temporary clone has no identity: reuse the source repository's author.
        name, email = _git("config", "user.name", cwd=root), _git("config", "user.email", cwd=root)
        try:
            _git("-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "-m", f"Mirror of docs/wiki at {commit}", cwd=out)
            _git("push", cwd=out)
        except subprocess.CalledProcessError as e:
            print(f"git failed: {e.stderr}", file=sys.stderr)
            return 1
        print(f"published {len(names)} pages from {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
