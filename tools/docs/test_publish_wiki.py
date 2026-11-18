"""Tests of the GitHub wiki mirror (docs/wiki -> ddmp3/EarthMoon.wiki)."""
from pathlib import Path

from publish_wiki import REPO_URL, build, page_name, rewrite_links


def test_page_names_are_flat():
    assert page_name("README.md") == "Home"
    assert page_name("baseline.md") == "baseline"
    assert page_name("data/moon.md") == "data-moon"
    assert page_name("v2/SCIENTIFIC_AUDIT.md") == "v2-SCIENTIFIC_AUDIT"


def test_links_between_wiki_pages_become_page_names():
    # Resolved relative to the source page (methods/), anchors kept.
    text = "[moon](data/moon.md) and [audit](../v2/SCIENTIFIC_AUDIT.md#5-findings)"
    out = rewrite_links(text, "methods/profiles.md")
    assert out == "[moon](methods-data-moon) and [audit](v2-SCIENTIFIC_AUDIT#5-findings)"


def test_with_a_page_list_unknown_wiki_files_link_to_github():
    out = rewrite_links("[m](../data/moon.md) [x](notes.txt)", "methods/profiles.md", pages={"data/moon.md"})
    assert out == f"[m](data-moon) [x]({REPO_URL}/docs/wiki/methods/notes.txt)"


def test_links_to_repository_files_become_github_urls():
    out = rewrite_links("[method](../METHOD.md) [code](../../tools/check.sh)", "baseline.md")
    assert out == f"[method]({REPO_URL}/docs/METHOD.md) [code]({REPO_URL}/tools/check.sh)"


def test_external_links_and_anchors_are_untouched():
    text = "[nasa](https://nasa.gov) [top](#top) `[code](x.md)`"
    assert rewrite_links(text, "baseline.md") == text


def test_build_writes_pages_home_and_sidebar(tmp_path: Path):
    src = tmp_path / "wiki"
    (src / "data").mkdir(parents=True)
    (src / "README.md").write_text("# Wiki\n[moon](data/moon.md)\n", encoding="utf-8")
    (src / "data" / "moon.md").write_text("# Moon data\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.md").write_text("old", encoding="utf-8")
    build(src, out, source_commit="abc1234")
    assert sorted(p.name for p in out.glob("*.md")) == ["Home.md", "_Footer.md", "_Sidebar.md", "data-moon.md"]
    assert "[moon](data-moon)" in (out / "Home.md").read_text(encoding="utf-8")
    assert "[Moon data](data-moon)" in (out / "_Sidebar.md").read_text(encoding="utf-8")
    assert "abc1234" in (out / "_Footer.md").read_text(encoding="utf-8")
