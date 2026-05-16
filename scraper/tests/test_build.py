import json
from pathlib import Path
from unittest.mock import patch

from scraper.build import build


def test_build_end_to_end(tmp_path, plats_bruts_html, llista_episodis_html):
    repo_root = tmp_path
    (repo_root / "data").mkdir()
    (repo_root / "data" / "overrides.json").write_text(json.dumps({
        "personatges": {"lofi": {"descripcio": "Estudiant de filosofia."}},
        "cites": [{"id": "c001", "text": "Que potes!", "personatge": "lofi", "episodi": "1x01"}],
        "localitzacions": [{"slug": "pis", "nom": "El pis", "descripcio": "L'apartament."}]
    }), encoding="utf-8")

    def fake_fetch(url, cache_key):
        if "Llista" in url:
            return llista_episodis_html
        return plats_bruts_html

    with patch("scraper.build.WikipediaCaFetcher") as MockFetcher:
        MockFetcher.return_value.fetch.side_effect = fake_fetch
        build(repo_root=repo_root)

    base = repo_root / "api" / "v1"
    lofi = json.loads((base / "personatges" / "lofi.json").read_text(encoding="utf-8"))
    assert lofi["descripcio"] == "Estudiant de filosofia."

    ep = json.loads((base / "episodis" / "1x01.json").read_text(encoding="utf-8"))
    assert ep["titol"] == "Pilot"

    cita = json.loads((base / "cites" / "c001.json").read_text(encoding="utf-8"))
    assert cita["text"] == "Que potes!"

    pis = json.loads((base / "localitzacions" / "pis.json").read_text(encoding="utf-8"))
    assert pis["nom"] == "El pis"

    indexes = ["personatges", "episodis", "temporades", "cites", "localitzacions"]
    for name in indexes:
        idx = json.loads((base / name / "index.json").read_text(encoding="utf-8"))
        assert idx["count"] >= 1
