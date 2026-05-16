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


def test_apply_appends_extra_personatges():
    base = [Personatge(slug="existing", nom="Existing")]
    overrides = Overrides(
        extra_personatges=[
            Personatge(slug="oriol-lopes", nom="Oriol Lopes",
                       actor=Actor(slug="jordi-banacolocha", nom="Jordi Banacolocha"))
        ],
    )
    result = overrides.apply_to_personatges(base)
    assert len(result) == 2
    assert result[1].slug == "oriol-lopes"
    assert result[1].actor.nom == "Jordi Banacolocha"


def test_apply_extras_does_not_duplicate_existing_slugs():
    base = [Personatge(slug="lofi", nom="Lofi")]
    overrides = Overrides(
        extra_personatges=[Personatge(slug="lofi", nom="Lofi DIFFERENT")]
    )
    result = overrides.apply_to_personatges(base)
    assert len(result) == 1
    assert result[0].nom == "Lofi"  # scraped wins


def test_load_overrides_reads_extra_personatges(tmp_path):
    p = tmp_path / "overrides.json"
    p.write_text(json.dumps({
        "personatges_extra": [
            {"slug": "test", "nom": "Test",
             "actor": {"slug": "actor-1", "nom": "Actor 1"}}
        ]
    }), encoding="utf-8")
    overrides = load_overrides(p)
    assert len(overrides.extra_personatges) == 1
    extra = overrides.extra_personatges[0]
    assert extra.slug == "test"
    assert extra.actor.nom == "Actor 1"
