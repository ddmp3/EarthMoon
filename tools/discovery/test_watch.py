"""Source watchers (T52 step 2, ADR-009 section 1), on recorded responses only: no network in tests."""
import json

import pytest

from discovery import watch
from discovery.watch import Response, check, make_fetch

NOW = "2026-11-23T20:00:00Z"


def fake(responses: dict):
    """A fetch that answers from recorded responses; a missing URL or a stored exception is a network failure."""
    def fetch(url, method="GET"):
        r = responses.get((method, url), responses.get(url))
        if r is None or isinstance(r, Exception):
            raise watch.FetchError(f"unreachable: {url}")
        return r
    return fetch


def s3_page(keys, token=None):
    items = "".join(f"<Contents><Key>{k}</Key><ETag>&quot;{e}&quot;</ETag><Size>{s}</Size></Contents>"
                    for k, e, s in keys)
    nxt = f"<IsTruncated>true</IsTruncated><NextContinuationToken>{token}</NextContinuationToken>" if token else \
        "<IsTruncated>false</IsTruncated>"
    return Response(200, {}, f"<ListBucketResult>{nxt}{items}</ListBucketResult>".encode())


S3 = {"family": "s3", "interval": "weekly", "watch": {"bucket": "https://b.example.org", "match": r"_DEM\.tif$"}}
LIST = "https://b.example.org/?list-type=2"


def s3_responses(second_etag="e2", drop=False):
    first = [("t1/t1_DEM.tif", "e1", 10), ("t1/aux.xml", "x", 1)]
    second = [] if drop else [("t2/t2_DEM.tif", second_etag, 20)]
    return {LIST: s3_page(first, token="abc"), LIST + "&continuation-token=abc": s3_page(second)}


def test_first_check_records_a_baseline_and_never_claims_unchanged():
    r = check("dem", S3, None, fake(s3_responses()), NOW)
    assert r["state"] == "baseline" and r["signal"] == {"t1/t1_DEM.tif": {"etag": "e1", "size": 10},
                                                        "t2/t2_DEM.tif": {"etag": "e2", "size": 20}}


def test_s3_listing_unchanged_changed_and_withdrawn():
    base = check("dem", S3, None, fake(s3_responses()), NOW)["signal"]
    assert check("dem", S3, base, fake(s3_responses()), NOW)["state"] == "unchanged"
    ch = check("dem", S3, base, fake(s3_responses(second_etag="e9")), NOW)
    assert ch["state"] == "changed" and ch["changed"] == ["t2/t2_DEM.tif"]
    wd = check("dem", S3, base, fake(s3_responses(drop=True)), NOW)
    assert wd["state"] == "withdrawn" and wd["withdrawn"] == ["t2/t2_DEM.tif"]


def test_an_unreachable_source_is_check_failed_never_unchanged():
    base = check("dem", S3, None, fake(s3_responses()), NOW)["signal"]
    r = check("dem", S3, base, fake({}), NOW)
    assert r["state"] == "check_failed" and "unreachable" in r["reason"] and r["signal"] is None


def test_a_server_error_or_refusal_is_check_failed():
    pds = {"family": "pds", "interval": "weekly", "watch": {"base": "https://p.example.org/img/",
                                                            "files": {"a.img": 100}}}
    for status in (403, 500, 503):
        r = check("lola", pds, None, fake({("HEAD", "https://p.example.org/img/a.img"): Response(status, {}, b"")}), NOW)
        assert r["state"] == "check_failed"


def test_pds_files_are_compared_with_the_size_recorded_at_ingest():
    """First check of a planetary file: the ingest size is the baseline, so a different size is a change."""
    pds = {"family": "pds", "interval": "weekly", "watch": {"base": "https://p.example.org/img/",
                                                            "files": {"a.img": 100, "b.img": 50}}}
    head = lambda n, size: Response(200, {"Content-Length": str(size), "ETag": '"x"',  # noqa: E731
                                          "Last-Modified": "Tue, 15 Sep 2026 00:00:00 GMT"}, b"")
    same = {("HEAD", "https://p.example.org/img/a.img"): head("a", 100),
            ("HEAD", "https://p.example.org/img/b.img"): head("b", 50)}
    assert check("lola", pds, None, fake(same), NOW)["state"] == "unchanged"
    other = dict(same)
    other[("HEAD", "https://p.example.org/img/b.img")] = head("b", 51)
    r = check("lola", pds, None, fake(other), NOW)
    assert r["state"] == "changed" and r["changed"] == ["b.img"]
    gone = dict(same)
    gone[("HEAD", "https://p.example.org/img/a.img")] = Response(404, {}, b"")
    assert check("lola", pds, None, fake(gone), NOW)["withdrawn"] == ["a.img"]


def test_page_pattern_reads_the_version_strings_of_a_page():
    page = {"family": "page", "interval": "monthly",
            "watch": {"url": "https://s.example.org/p", "pattern": r"Updated (\d{4}-\d{2}-\d{2} [\d:]+)"}}
    body = b"<p>Ci Updated 2019-05-08 08:37:36</p><p>Updated 2019-05-09 10:00:00</p>"
    base = check("swim", page, None, fake({"https://s.example.org/p": Response(200, {}, body)}), NOW)["signal"]
    assert check("swim", page, base, fake({"https://s.example.org/p": Response(200, {}, body)}), NOW)["state"] == "unchanged"
    r = check("swim", page, base, fake({"https://s.example.org/p": Response(200, {}, body.replace(b"05-09", b"06-01"))}),
              NOW)
    assert r["state"] == "changed"
    empty = check("swim", page, base, fake({"https://s.example.org/p": Response(200, {}, b"<p>redesigned</p>")}), NOW)
    assert empty["state"] == "check_failed" and "pattern" in empty["reason"]   # a lost pattern is not a withdrawal


def test_doi_reads_version_and_update_dates_from_datacite():
    doi = {"family": "doi", "interval": "monthly", "watch": {"doi": "10.1594/PANGAEA.888600"}}
    meta = lambda v, d: Response(200, {}, json.dumps({"data": {"attributes": {  # noqa: E731
        "version": v, "updated": "2026-01-01T00:00:00Z",
        "dates": [{"date": "2018-04-17", "dateType": "Issued"}, {"date": d, "dateType": "Updated"}]}}}).encode())
    url = "https://api.datacite.org/dois/10.1594/PANGAEA.888600"
    base = check("p", doi, None, fake({url: meta(None, "2019-04-01")}), NOW)["signal"]
    assert base == {"10.1594/PANGAEA.888600": {"version": None, "updated": "2019-04-01"}}
    assert check("p", doi, base, fake({url: meta(None, "2019-04-01")}), NOW)["state"] == "unchanged"
    assert check("p", doi, base, fake({url: meta("2", "2019-04-01")}), NOW)["state"] == "changed"
    assert check("p", doi, base, fake({url: Response(404, {}, b"")}), NOW)["state"] == "withdrawn"


def test_api_reads_one_value_at_a_json_path():
    api = {"family": "api", "interval": "monthly",
           "watch": {"endpoint": "https://api.example.org/commits", "path": "0.sha"}}
    r = lambda sha: {"https://api.example.org/commits": Response(200, {}, json.dumps([{"sha": sha}]).encode())}  # noqa: E731
    base = check("ne", api, None, fake(r("abc")), NOW)["signal"]
    assert check("ne", api, base, fake(r("abc")), NOW)["state"] == "unchanged"
    assert check("ne", api, base, fake(r("def")), NOW)["state"] == "changed"
    bad = check("ne", api, base, fake({"https://api.example.org/commits": Response(200, {}, b"[]")}), NOW)
    assert bad["state"] == "check_failed"


@pytest.mark.parametrize("refresh,why", [
    ({"family": "none", "interval": "none"}, "no machine signal"),
    ({"family": "pds", "interval": "weekly"}, "no target recorded"),
    ({"family": "cds", "interval": "weekly", "watch": {"dataset": "x"}}, "CDS"),
])
def test_sources_without_a_usable_signal_are_not_checkable(refresh, why):
    r = check("x", refresh, None, fake({}), NOW)
    assert r["state"] == "not_checkable" and why in r["reason"]


def test_fetch_refuses_hosts_outside_the_catalogue():
    fetch = make_fetch({"copernicus-dem-90m.s3.amazonaws.com"})
    with pytest.raises(watch.FetchError, match="not a catalogue host"):
        fetch("https://evil.example.org/x")


def test_catalogue_hosts_are_read_from_the_watch_targets():
    hosts = watch.catalogue_hosts([{"refresh": S3}, {"refresh": {"family": "doi", "watch": {"doi": "10.1/x"}}},
                                   {"refresh": {"family": "pds", "watch": {"base": "https://p.example.org/img/"}}}])
    assert hosts == {"b.example.org", "api.datacite.org", "p.example.org"}


def test_a_check_returns_the_base_it_compared_with():
    pds = {"family": "pds", "interval": "weekly", "watch": {"base": "https://p.example.org/img/", "files": {"a.img": 100}}}
    ok = {("HEAD", "https://p.example.org/img/a.img"): Response(200, {"Content-Length": "100"}, b"")}
    assert check("lola", pds, None, fake(ok), NOW)["base"] == {"a.img": {"size": 100}}
    assert check("lola", pds, {"a.img": {"size": 100, "etag": "e"}}, fake(ok), NOW)["base"] == {"a.img": {"size": 100, "etag": "e"}}
