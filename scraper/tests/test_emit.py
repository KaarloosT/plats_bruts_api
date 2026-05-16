import json
from pathlib import Path

from scraper.models import Cita, Episodi, Localitzacio, Personatge, Temporada
from scraper.emit import emit_api


def test_emit_writes_personatge_detail_and_index(tmp_path):
    lofi = Personatge(slug="lofi", nom="Lofi")
    emit_api(
        tmp_path,
        personatges=[lofi],
        episodis=[],
        temporades=[],
        cites=[],
        localitzacions=[],
    )

    detail_file = tmp_path / "api" / "v1" / "personatges" / "lofi.json"
    assert detail_file.exists()
    assert json.loads(detail_file.read_text(encoding="utf-8"))["slug"] == "lofi"

    index_file = tmp_path / "api" / "v1" / "personatges" / "index.json"
    index = json.loads(index_file.read_text(encoding="utf-8"))
    assert index["count"] == 1
    assert index["results"][0]["slug"] == "lofi"
    assert index["results"][0]["url"] == "/api/v1/personatges/lofi.json"


def test_emit_writes_all_resource_types(tmp_path):
    emit_api(
        tmp_path,
        personatges=[Personatge(slug="lofi", nom="Lofi")],
        episodis=[Episodi(temporada=1, numero=1, titol="Pilot")],
        temporades=[Temporada(numero=1)],
        cites=[Cita(id="c001", text="Que potes!")],
        localitzacions=[Localitzacio(slug="pis", nom="El pis")],
    )

    base = tmp_path / "api" / "v1"
    assert (base / "personatges" / "index.json").exists()
    assert (base / "episodis" / "index.json").exists()
    assert (base / "episodis" / "1x01.json").exists()
    assert (base / "temporades" / "index.json").exists()
    assert (base / "temporades" / "1.json").exists()
    assert (base / "cites" / "index.json").exists()
    assert (base / "cites" / "c001.json").exists()
    assert (base / "localitzacions" / "index.json").exists()
    assert (base / "localitzacions" / "pis.json").exists()


def test_emit_overwrites_stale_files(tmp_path):
    stale = tmp_path / "api" / "v1" / "personatges" / "stale.json"
    stale.parent.mkdir(parents=True)
    stale.write_text("{}", encoding="utf-8")

    emit_api(
        tmp_path,
        personatges=[Personatge(slug="lofi", nom="Lofi")],
        episodis=[], temporades=[], cites=[], localitzacions=[],
    )

    # Stale file from a previous run should be cleaned up.
    assert not stale.exists()
    assert (tmp_path / "api" / "v1" / "personatges" / "lofi.json").exists()
