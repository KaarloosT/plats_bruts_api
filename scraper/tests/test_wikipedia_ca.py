from pathlib import Path
from unittest.mock import patch, MagicMock

from scraper.sources.wikipedia_ca import WikipediaCaFetcher


def test_fetcher_uses_cache_when_available(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached_file = cache_dir / "plats-bruts.html"
    cached_file.write_text("<html>cached</html>", encoding="utf-8")

    fetcher = WikipediaCaFetcher(cache_dir=cache_dir)
    html = fetcher.fetch("https://ca.wikipedia.org/wiki/Plats_bruts", cache_key="plats-bruts")
    assert html == "<html>cached</html>"


def test_fetcher_downloads_and_caches_when_missing(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    mock_response = MagicMock()
    mock_response.text = "<html>fresh</html>"
    mock_response.raise_for_status = MagicMock()

    fetcher = WikipediaCaFetcher(cache_dir=cache_dir, throttle_seconds=0)
    with patch("scraper.sources.wikipedia_ca.requests.get", return_value=mock_response) as mock_get:
        html = fetcher.fetch("https://ca.wikipedia.org/wiki/Plats_bruts", cache_key="plats-bruts")

    assert html == "<html>fresh</html>"
    assert (cache_dir / "plats-bruts.html").read_text(encoding="utf-8") == "<html>fresh</html>"
    mock_get.assert_called_once()
    headers = mock_get.call_args.kwargs["headers"]
    assert "plats-bruts-api" in headers["User-Agent"]


def test_fetcher_throttles_between_live_requests(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    mock_response = MagicMock()
    mock_response.text = "<html>x</html>"
    mock_response.raise_for_status = MagicMock()

    fetcher = WikipediaCaFetcher(cache_dir=cache_dir, throttle_seconds=99)
    with patch("scraper.sources.wikipedia_ca.requests.get", return_value=mock_response), \
         patch("scraper.sources.wikipedia_ca.time.sleep") as mock_sleep:
        fetcher.fetch("https://example.com/a", cache_key="a")
        fetcher.fetch("https://example.com/b", cache_key="b")

    # First call: no prior request, no sleep. Second: must sleep ~throttle_seconds.
    assert mock_sleep.called
    slept = mock_sleep.call_args.args[0]
    assert slept > 0


from scraper.sources.wikipedia_ca import parse_personatges

PERSONATGES_URL = "https://ca.wikipedia.org/wiki/Llista_de_personatges_de_Plats_bruts"


def test_parse_personatges_extracts_rows(plats_bruts_html):
    personatges = parse_personatges(plats_bruts_html, source_url=PERSONATGES_URL)

    assert len(personatges) == 3
    lopes = personatges[0]
    assert lopes.slug == "josep-lopes"
    assert lopes.nom == "Josep Lopes"
    assert lopes.actor is None
    assert lopes.font_wikipedia == PERSONATGES_URL

    david = personatges[1]
    assert david.nom == "David Güell i Sobirana"
    assert david.font_wikipedia == PERSONATGES_URL

    pol = personatges[2]
    assert pol.nom == "Pol Requena"
    assert pol.font_wikipedia == PERSONATGES_URL


def test_parse_personatges_handles_accented_names(plats_bruts_html):
    personatges = parse_personatges(plats_bruts_html, source_url=PERSONATGES_URL)
    david = personatges[1]
    assert david.nom == "David Güell i Sobirana"
    assert david.slug == "david-guell-i-sobirana"  # accents stripped by slugify


from scraper.sources.wikipedia_ca import parse_episodis_i_temporades

EPISODIS_URL = "https://ca.wikipedia.org/wiki/Llista_d%27episodis_de_Plats_bruts"


def test_parse_episodis_extracts_per_season(llista_episodis_html):
    episodis, temporades = parse_episodis_i_temporades(
        llista_episodis_html,
        source_url=EPISODIS_URL,
    )

    assert len(episodis) == 3
    assert episodis[0].id == "1x01"
    assert episodis[0].titol == "Tinc pis"
    assert episodis[0].data_emissio == "1999-04-19"
    assert episodis[1].id == "1x02"
    assert episodis[1].titol == "Tinc por"
    assert episodis[2].id == "2x01"
    assert episodis[2].titol == "Tinc mama"


def test_parse_temporades_groups_episodis(llista_episodis_html):
    _, temporades = parse_episodis_i_temporades(
        llista_episodis_html,
        source_url=EPISODIS_URL,
    )
    assert len(temporades) == 2
    t1 = temporades[0]
    assert t1.numero == 1
    assert t1.num_episodis == 2
    assert t1.episodis == ["1x01", "1x02"]
    assert t1.any_inici == 1999
    assert t1.any_fi == 1999

    t2 = temporades[1]
    assert t2.numero == 2
    assert t2.episodis == ["2x01"]
    assert t2.any_inici == 1999
