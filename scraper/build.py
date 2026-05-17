from pathlib import Path

from scraper.emit import emit_api
from scraper.models import Cita
from scraper.overrides import load_overrides
from scraper.sources.wikipedia_ca import (
    WikipediaCaFetcher,
    parse_episodis_i_temporades,
    parse_personatges,
    parse_temporades_summary,
)
from scraper.sources.wikiquote_ca import WikiquoteCaFetcher, parse_season_quotes

WIKI_SERIE_URL = "https://ca.wikipedia.org/wiki/Plats_bruts"
WIKI_PERSONATGES_URL = "https://ca.wikipedia.org/wiki/Llista_de_personatges_de_Plats_bruts"
WIKI_EPISODIS_URL = "https://ca.wikipedia.org/wiki/Llista_d%27episodis_de_Plats_bruts"
WIKIQUOTE_SEASON_URL = "https://ca.wikiquote.org/wiki/Plats_Bruts_(Temporada_{n})"


def build(repo_root: Path) -> None:
    repo_root = Path(repo_root)
    cache_dir = repo_root / "scraper" / ".cache"

    fetcher = WikipediaCaFetcher(cache_dir=cache_dir)
    serie_html = fetcher.fetch(WIKI_SERIE_URL, cache_key="serie")
    personatges_html = fetcher.fetch(WIKI_PERSONATGES_URL, cache_key="personatges")
    episodis_html = fetcher.fetch(WIKI_EPISODIS_URL, cache_key="episodis")

    personatges = parse_personatges(personatges_html, source_url=WIKI_PERSONATGES_URL)
    episodis, temporades = parse_episodis_i_temporades(
        episodis_html, source_url=WIKI_EPISODIS_URL
    )

    # Enrich temporades with audience numbers from the main article's summary table
    audience_by_season = parse_temporades_summary(serie_html)
    for t in temporades:
        info = audience_by_season.get(t.numero)
        if info:
            t.audiencia_mitjana = info.get("audiencia_mitjana")
            t.quota_audiencia = info.get("quota_audiencia")

    overrides = load_overrides(repo_root / "data" / "overrides.json")
    personatges = overrides.apply_to_personatges(personatges)

    wikiquote_fetcher = WikiquoteCaFetcher(cache_dir=cache_dir)
    scraped_cites: list[Cita] = []
    for season_n in range(1, 7):  # 6 seasons
        url = WIKIQUOTE_SEASON_URL.format(n=season_n)
        wq_html = wikiquote_fetcher.fetch(url, cache_key=f"wikiquote-t{season_n}")
        scraped_cites.extend(parse_season_quotes(wq_html, season=season_n, source_url=url))

    # Combine: overrides cites + wikiquote cites (deduped by id, overrides win)
    seen_ids = {c.id for c in overrides.cites}
    all_cites = list(overrides.cites) + [c for c in scraped_cites if c.id not in seen_ids]

    # Cross-link: populate episodi.cites / episodi.personatges from cite data,
    # and personatge.cites from cite data.
    cites_by_episode: dict[str, list[str]] = {}
    speakers_by_episode: dict[str, set[str]] = {}
    cites_by_personatge: dict[str, list[str]] = {}
    for c in all_cites:
        if c.episodi:
            cites_by_episode.setdefault(c.episodi, []).append(c.id)
            if c.personatge:
                speakers_by_episode.setdefault(c.episodi, set()).add(c.personatge)
        if c.personatge:
            cites_by_personatge.setdefault(c.personatge, []).append(c.id)

    for e in episodis:
        e.cites = sorted(cites_by_episode.get(e.id, []))
        e.personatges = sorted(speakers_by_episode.get(e.id, set()))

    for p in personatges:
        p.cites = sorted(cites_by_personatge.get(p.slug, []))

    emit_api(
        repo_root,
        personatges=personatges,
        episodis=episodis,
        temporades=temporades,
        cites=all_cites,
        localitzacions=overrides.localitzacions,
    )


if __name__ == "__main__":
    build(repo_root=Path(__file__).resolve().parent.parent)
