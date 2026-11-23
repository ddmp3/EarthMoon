"""Isolation of the local stack (ADR-005, ADR-009 section 5), read from docker-compose.yml."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
S = COMPOSE["services"]


def _data_mounts(svc: dict) -> list[str]:
    return [v for v in svc.get("volumes", []) if ":/data" in v]


def test_api_and_discovery_read_the_data_only():
    for name in ("api", "discovery"):
        mounts = _data_mounts(S[name])
        assert mounts and all(m.endswith(":ro") for m in mounts), name
    assert S["discovery"]["read_only"] is True and S["discovery"]["networks"] == ["backend"]
    assert COMPOSE["networks"]["backend"]["internal"] is True


def test_the_refresher_is_the_only_writer_and_publishes_no_port():
    r = S["refresher"]
    assert "ports" not in r and "expose" not in r
    assert any(not m.endswith(":ro") for m in _data_mounts(r))
    assert [n for n, s in S.items() if any(not m.endswith(":ro") for m in _data_mounts(s))] == ["refresher"]


def test_the_refresher_starts_only_on_request_and_never_on_the_fixture():
    r = S["refresher"]
    assert r["profiles"] == ["refresh"]                       # `docker compose up` (and the e2e test) leave it off
    assert all("releases-fixture" not in m for m in _data_mounts(r))
    assert all("EARTHMOON_DATA" in m for m in _data_mounts(r))      # the real data folder, named by the user


def test_refresher_credentials_come_from_an_uncommitted_file():
    r = S["refresher"]
    files = [f["path"] if isinstance(f, dict) else f for f in r.get("env_file", [])]
    assert files == [".env.refresher"]
    assert not (ROOT / ".env.refresher").exists() or ".env.*" in (ROOT / ".gitignore").read_text()
    assert "environment" not in r or not any(k.lower().endswith(("key", "password", "token")) for k in r["environment"])
