from pathlib import Path

from scraper.emit import emit_api
from scraper.overrides import load_overrides
from scraper.sources.wikipedia_ca import (
    WikipediaCaFetcher,
    parse_episodis_i_temporades,
    parse_personatges,
)

WIKI_PERSONATGES_URL = "https://ca.wikipedia.org/wiki/Llista_de_personatges_de_Plats_bruts"
WIKI_EPISODIS_URL = "https://ca.wikipedia.org/wiki/Llista_d%27episodis_de_Plats_bruts"


def build(repo_root: Path) -> None:
    repo_root = Path(repo_root)
    cache_dir = repo_root / "scraper" / ".cache"

    fetcher = WikipediaCaFetcher(cache_dir=cache_dir)
    personatges_html = fetcher.fetch(WIKI_PERSONATGES_URL, cache_key="personatges")
    episodis_html = fetcher.fetch(WIKI_EPISODIS_URL, cache_key="episodis")

    personatges = parse_personatges(personatges_html, source_url=WIKI_PERSONATGES_URL)
    episodis, temporades = parse_episodis_i_temporades(
        episodis_html, source_url=WIKI_EPISODIS_URL
    )

    overrides = load_overrides(repo_root / "data" / "overrides.json")
    personatges = overrides.apply_to_personatges(personatges)

    emit_api(
        repo_root,
        personatges=personatges,
        episodis=episodis,
        temporades=temporades,
        cites=overrides.cites,
        localitzacions=overrides.localitzacions,
    )


if __name__ == "__main__":
    build(repo_root=Path(__file__).resolve().parent.parent)
