"""Checks every DOI of docs/REFERENCES.md against Crossref (task T13).

    python -I tools/research/verify_refs.py                    # writes docs/wiki/references-check.md

For each reference row (| Rn | citation | ...), every DOI is resolved through the Crossref API and the record
is compared with the citation: first author's family name, year, and title words. Requests are sequential
with a pause (Crossref answered 429 to parallel calls in v2) and use a generic User-Agent, no personal data.
A DOI that resolves to another paper is reported as a mismatch: it is worse than no DOI.
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

ROW = re.compile(r"^\|\s*(R\d+)\s*\|\s*(.+?)\s*\|\s*([^|]*?)\s*\|", re.M)
DOI = re.compile(r"doi:\s*(10\.\d{4,9}/[^\s;,|]+?)(?=[\s;,|]|\.?\s*$|\.\s)", re.I)
USER_AGENT = "EarthMoon-reference-check/1.0 (+https://github.com/ddmp3/EarthMoon)"


def parse_references(markdown: str) -> list[dict]:
    refs = []
    for ident, citation, status in ROW.findall(markdown):
        dois = [d.rstrip(".") for d in DOI.findall(citation + " ")]
        refs.append({"id": ident, "citation": citation, "status": status, "dois": dois})
    return refs


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", text)


def compare(citation: str, record: dict) -> dict:
    """Match a Crossref record with a citation. Notes (online-first year, corporate author) do not fail it."""
    problems, notes = [], []
    cit = _norm(citation)
    family = _norm((record.get("author") or [{}])[0].get("family", ""))
    if not family:
        notes.append("no personal author in Crossref")
    elif family.split()[0] not in cit:
        problems.append("author")
    year = ((record.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    if year is None or str(year) not in citation:
        if year is not None and (str(year + 1) in citation or str(year - 1) in citation):
            notes.append(f"Crossref year {year} differs by one (online-first or print date)")
        else:
            problems.append("year")
    words = [w for w in _norm((record.get("title") or [""])[0]).split() if len(w) > 3]
    if not words or sum(w in cit for w in words) / len(words) < 0.6:
        problems.append("title")
    return {"match": not problems, "problems": problems, "notes": notes,
            "crossref": {"title": (record.get("title") or [""])[0], "first_author": family, "year": str(year),
                         "journal": (record.get("container-title") or [""])[0]}}


def check_reference(ref: dict, fetch: Callable[[str], dict | None]) -> dict:
    if not ref["dois"]:
        return {"id": ref["id"], "verdict": "no DOI: manual check", "results": []}
    results = []
    for doi in ref["dois"]:
        record = fetch(doi)
        if record is None:
            results.append({"doi": doi, "match": False, "problems": ["DOI not found"]})
        else:
            results.append({"doi": doi, **compare(ref["citation"], record)})
    verdict = "verified" if all(r["match"] for r in results) else "mismatch"
    return {"id": ref["id"], "verdict": verdict, "results": results}


def crossref_fetch(doi: str, pause: float = 1.2) -> dict | None:
    time.sleep(pause)
    req = urllib.request.Request(f"https://api.crossref.org/works/{doi}", headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read())["message"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            raise
    return None


def datacite_record(payload: dict) -> dict:
    """A DataCite record (data DOIs such as PANGAEA) in the shape of a Crossref one, for compare()."""
    a = payload.get("data", {}).get("attributes", {})
    creators = [{"family": c.get("familyName") or (c.get("name") or "").split(",")[0]} for c in a.get("creators") or []]
    return {"title": [t.get("title", "") for t in a.get("titles") or []][:1] or [""], "author": creators,
            "issued": {"date-parts": [[a.get("publicationYear")]]}, "container-title": [a.get("publisher") or ""]}


def datacite_fetch(doi: str, pause: float = 1.2) -> dict | None:
    time.sleep(pause)
    req = urllib.request.Request(f"https://api.datacite.org/dois/{doi}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return datacite_record(json.loads(res.read()))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def first_found(*fetchers: Callable[[str], dict | None]) -> Callable[[str], dict | None]:
    """Crossref first, then DataCite: a DOI unknown to both is reported as not found."""
    def fetch(doi: str) -> dict | None:
        for f in fetchers:
            rec = f(doi)
            if rec is not None:
                return rec
        return None
    return fetch


def report(checks: list[dict], today: str) -> str:
    lines = [f"# Reference check ({today})", "",
             "Generated by `tools/research/verify_refs.py`: each DOI of [REFERENCES.md](../REFERENCES.md) resolved on Crossref (DataCite for data DOIs) "
             "and compared with the citation (first author, year, title words). Do not edit by hand.", "",
             "| ID | Verdict | DOI | Problems or notes | Crossref title |", "|---|---|---|---|---|"]
    for c in checks:
        if not c["results"]:
            lines.append(f"| {c['id']} | {c['verdict']} | | | |")
        for r in c["results"]:
            title = r.get("crossref", {}).get("title", "").replace("|", "/")[:110]
            issues = ", ".join(r["problems"] + r.get("notes", [])) or "none"
            lines.append(f"| {c['id']} | {c['verdict']} | {r['doi']} | {issues} | {title} |")
    counts = {v: sum(c["verdict"] == v for c in checks) for v in ("verified", "mismatch", "no DOI: manual check")}
    lines += ["", f"Totals: {counts['verified']} verified, {counts['mismatch']} mismatch, {counts['no DOI: manual check']} without DOI."]
    return "\n".join(lines) + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    refs = parse_references((root / "docs" / "REFERENCES.md").read_text(encoding="utf-8"))
    checks = [check_reference(r, first_found(crossref_fetch, datacite_fetch)) for r in refs]
    (root / "docs" / "wiki" / "references-check.md").write_text(report(checks, time.strftime("%Y-%m-%d")), encoding="utf-8")
    bad = [c["id"] for c in checks if c["verdict"] == "mismatch"]
    print(f"{len(checks)} references, mismatches: {bad or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
