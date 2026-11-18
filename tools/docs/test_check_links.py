"""Tests of the Markdown link checker."""
from pathlib import Path

from check_links import broken_links, links_in


def test_finds_relative_links_and_ignores_urls_and_anchors():
    text = "[a](x.md) [b](https://nasa.gov) [c](#top) [d](../y/z.md#part) ![img](pic.png) `[e](code.md)`"
    assert links_in(text) == ["x.md", "../y/z.md", "pic.png"]


def test_reports_missing_targets_only(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ok.md").write_text("[back](../readme.md) [gone](missing.md)", encoding="utf-8")
    (tmp_path / "readme.md").write_text("[docs](docs/ok.md)", encoding="utf-8")
    assert broken_links(tmp_path) == [("docs/ok.md", "missing.md")]


def test_skips_dependency_folders(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.md").write_text("[gone](nope.md)", encoding="utf-8")
    assert broken_links(tmp_path) == []


def test_link_with_spaces_encoded(tmp_path: Path):
    (tmp_path / "a b.md").write_text("", encoding="utf-8")
    (tmp_path / "i.md").write_text("[x](a%20b.md)", encoding="utf-8")
    assert broken_links(tmp_path) == []
