from scraper.models import Actor, Personatge, Episodi, Temporada, Cita, Localitzacio


def test_personatge_to_dict():
    p = Personatge(
        slug="lofi",
        nom="Lofi",
        nom_complet="Lluís Fernández",
        descripcio="Estudiant de filosofia.",
        actor=Actor(slug="joel-joan", nom="Joel Joan"),
        temporades=[1, 2, 3],
        primera_aparicio="1x01",
        imatge="https://example.com/lofi.jpg",
        font_wikipedia="https://ca.wikipedia.org/wiki/Plats_bruts",
    )
    assert p.to_dict() == {
        "slug": "lofi",
        "nom": "Lofi",
        "nom_complet": "Lluís Fernández",
        "descripcio": "Estudiant de filosofia.",
        "actor": {"slug": "joel-joan", "nom": "Joel Joan"},
        "temporades": [1, 2, 3],
        "primera_aparicio": "1x01",
        "imatge": "https://example.com/lofi.jpg",
        "font_wikipedia": "https://ca.wikipedia.org/wiki/Plats_bruts",
    }


def test_personatge_index_entry():
    p = Personatge(slug="lofi", nom="Lofi")
    assert p.index_entry() == {
        "slug": "lofi",
        "nom": "Lofi",
        "url": "/api/v1/personatges/lofi.json",
    }


def test_episodi_id_format():
    e = Episodi(temporada=1, numero=3, titol="...")
    assert e.id == "1x03"


def test_episodi_id_double_digit():
    e = Episodi(temporada=2, numero=12, titol="...")
    assert e.id == "2x12"


def test_temporada_to_dict():
    t = Temporada(numero=1, any_inici=1999, any_fi=1999, num_episodis=2, episodis=["1x01", "1x02"])
    assert t.to_dict() == {
        "numero": 1,
        "any_inici": 1999,
        "any_fi": 1999,
        "num_episodis": 2,
        "episodis": ["1x01", "1x02"],
    }


def test_cita_to_dict():
    c = Cita(id="c001", text="Que potes!", personatge="lofi", episodi="1x01")
    assert c.to_dict() == {
        "id": "c001",
        "text": "Que potes!",
        "personatge": "lofi",
        "episodi": "1x01",
    }


def test_localitzacio_to_dict():
    l = Localitzacio(slug="mortimers", nom="Mortimer's", descripcio="El bar.", episodis=["1x01"], imatge=None)
    assert l.to_dict() == {
        "slug": "mortimers",
        "nom": "Mortimer's",
        "descripcio": "El bar.",
        "episodis": ["1x01"],
        "imatge": None,
    }
