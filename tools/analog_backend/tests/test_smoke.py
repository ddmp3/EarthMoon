import json, os
from analog_finder.export_results import SITE_KEYS, validate
from run_pipeline import load_config, run
from tests.make_fixtures import make_fixtures


def test_pipeline_end_to_end(tmp_path):
    cfg = load_config(make_fixtures(str(tmp_path / "data")))
    res = run(cfg, str(tmp_path / "out"))
    payload = json.load(open(res["paths"]["json"]))
    validate(payload)
    sites = payload["sites"]
    assert len(sites) > 20
    src = {s["datasetSource"] for s in sites}
    assert src == {"NLDAS", "RCM_Arctic", "RCM_Antarctic"}, src
    assert all(list(s) == SITE_KEYS for s in sites)
    nl = [s for s in sites if s["datasetSource"] == "NLDAS"]
    rc = [s for s in sites if s["datasetSource"] != "NLDAS"]
    assert all(s["comparison"]["thermalQuantileMatch"] is not None for s in nl)
    assert all(s["comparison"]["thermalQuantileMatch"] is None and s["variables"]["windSpeed"] is None for s in rc)
    assert all(0 <= s["comparison"]["similarityIndex"] <= 1 for s in sites)
    assert os.path.exists(res["paths"]["geojson"]) and os.path.exists(tmp_path / "out" / "audit.json")
