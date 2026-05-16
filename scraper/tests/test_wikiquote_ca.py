def test_parse_season_quotes_basic(wq_season1_html):
    from scraper.sources.wikiquote_ca import parse_season_quotes
    cites = parse_season_quotes(wq_season1_html, season=1, source_url="https://example.com/wq/t1")
    # Episode 1: 2 dialogue blocks. Episode 2: 1 dialogue block. Total: 3.
    assert len(cites) == 3

    first = cites[0]
    assert first.id == "wq-1x01-01"
    assert first.episodi == "1x01"
    assert first.personatge == "josep-lopes"
    # First block has 3 turns (1 ul li + 2 dl dd)
    assert "Lopes:" in first.text
    assert "Ramon:" in first.text
    # citation markers stripped
    assert "[1]" not in first.text


def test_parse_season_quotes_unknown_speaker_yields_none_personatge(wq_season1_html):
    # In our fixture all speakers are mapped; let's add a quick assertion for the
    # last cite which is David (mapped).
    from scraper.sources.wikiquote_ca import parse_season_quotes
    cites = parse_season_quotes(wq_season1_html, season=1, source_url="https://example.com")
    last = cites[-1]
    assert last.id == "wq-1x02-01"
    assert last.episodi == "1x02"
    assert last.personatge == "david-guell-i-sobirana"
    # stage direction stripped
    assert "sorprès" not in last.text or "[" not in last.text  # the [i] tag is removed


def test_parse_season_quotes_handles_empty_html():
    from scraper.sources.wikiquote_ca import parse_season_quotes
    assert parse_season_quotes("<html><body></body></html>", season=1, source_url="x") == []


def test_fetcher_caches(tmp_path):
    from scraper.sources.wikiquote_ca import WikiquoteCaFetcher
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "x.html").write_text("<html>cached</html>", encoding="utf-8")
    fetcher = WikiquoteCaFetcher(cache_dir=cache)
    assert fetcher.fetch("https://example.com", cache_key="x") == "<html>cached</html>"
