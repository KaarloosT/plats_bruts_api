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
