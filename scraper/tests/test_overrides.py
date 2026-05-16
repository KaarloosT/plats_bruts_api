import json
from pathlib import Path

from scraper.models import Actor, Cita, Localitzacio, Personatge
from scraper.overrides import Overrides, load_overrides


def test_load_overrides_from_file(tmp_path):
    overrides_file = tmp_path / "overrides.json"
    overrides_file.write_text(json.dumps({
        "personatges": {"lofi": {"descripcio": "Estudiant de filosofia."}},
        "cites": [{"id": "c001", "text": "Que pots!", "personatge": "lofi", "episodi": "1x01"}],
        "localitzacions": [{"slug": "pis", "nom": "El pis", "descripcio": "L'apartament."}],
    }), encoding="utf-8")

    overrides = load_overrides(overrides_file)
    assert overrides.personatge_patches["lofi"] == {"descripcio": "Estudiant de filosofia."}
    assert len(overrides.cites) == 1
    assert overrides.cites[0].id == "c001"
    assert len(overrides.localitzacions) == 1
    assert overrides.localitzacions[0].slug == "pis"


def test_load_overrides_missing_file_returns_empty(tmp_path):
    overrides = load_overrides(tmp_path / "missing.json")
    assert overrides.personatge_patches == {}
    assert overrides.cites == []
    assert overrides.localitzacions == []


def test_apply_personatge_patch_overrides_fields():
    p = Personatge(slug="lofi", nom="Lofi", actor=Actor(slug="joel-joan", nom="Joel Joan"))
    overrides = Overrides(
        personatge_patches={"lofi": {"descripcio": "Estudiant.", "nom_complet": "Lluís Fernández"}},
        cites=[],
        localitzacions=[],
    )
    patched = overrides.apply_to_personatges([p])
    assert patched[0].descripcio == "Estudiant."
    assert patched[0].nom_complet == "Lluís Fernández"
    assert patched[0].actor.nom == "Joel Joan"  # not overridden


def test_apply_personatge_patch_ignores_unknown_slugs():
    p = Personatge(slug="lofi", nom="Lofi")
    overrides = Overrides(
        personatge_patches={"unknown": {"descripcio": "..."}},
        cites=[],
        localitzacions=[],
    )
    patched = overrides.apply_to_personatges([p])
    assert patched[0].descripcio is None
