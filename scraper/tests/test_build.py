import json
from pathlib import Path
from unittest.mock import patch

from scraper.build import build


def test_build_end_to_end(tmp_path, plats_bruts_html, llista_episodis_html):
    repo_root = tmp_path
    (repo_root / "data").mkdir()
    (repo_root / "data" / "overrides.json").write_text(json.dumps({
        "personatges": {"josep-lopes": {"descripcio": "El Lopes és un personatge principal."}},
        "cites": [{"id": "c001", "text": "Que potes!", "personatge": "josep-lopes", "episodi": "1x01"}],
        "localitzacions": [{"slug": "pis", "nom": "El pis", "descripcio": "L'apartament."}]
    }), encoding="utf-8")

    def fake_fetch(url, cache_key):
        if "Llista_d" in url and "episodis" in url:
            return llista_episodis_html
        if "Llista_de_personatges" in url:
            return plats_bruts_html
        return ""

    with patch("scraper.build.WikipediaCaFetcher") as MockFetcher, \
         patch("scraper.build.WikiquoteCaFetcher") as MockWQ:
        MockFetcher.return_value.fetch.side_effect = fake_fetch
        # Make the WQ fetcher return empty HTML so no quotes are scraped in the test
        MockWQ.return_value.fetch.return_value = "<html><body></body></html>"
        build(repo_root=repo_root)

    base = repo_root / "api" / "v1"
    lopes = json.loads((base / "personatges" / "josep-lopes.json").read_text(encoding="utf-8"))
    assert lopes["descripcio"] == "El Lopes és un personatge principal."

    ep = json.loads((base / "episodis" / "1x01.json").read_text(encoding="utf-8"))
    assert ep["titol"] == "Tinc pis"

    cita = json.loads((base / "cites" / "c001.json").read_text(encoding="utf-8"))
    assert cita["text"] == "Que potes!"

    pis = json.loads((base / "localitzacions" / "pis.json").read_text(encoding="utf-8"))
    assert pis["nom"] == "El pis"

    indexes = ["personatges", "episodis", "temporades", "cites", "localitzacions"]
    for name in indexes:
        idx = json.loads((base / name / "index.json").read_text(encoding="utf-8"))
        assert idx["count"] >= 1
