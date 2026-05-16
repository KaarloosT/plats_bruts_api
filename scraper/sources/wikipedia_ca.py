import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from scraper.models import Actor, Episodi, Personatge, Temporada
from scraper.slugify import slugify

USER_AGENT = "plats-bruts-api/0.1 (https://github.com/plats-bruts-api; bastanerada77@gmail.com)"


class WikipediaCaFetcher:
    """Fetches Wikipedia pages with on-disk caching and request throttling."""

    def __init__(self, cache_dir: Path, throttle_seconds: float = 1.5):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.throttle_seconds = throttle_seconds
        self._last_request_ts: Optional[float] = None

    def fetch(self, url: str, cache_key: str) -> str:
        cache_file = self.cache_dir / f"{cache_key}.html"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

        self._throttle()
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        self._last_request_ts = time.monotonic()

        cache_file.write_text(response.text, encoding="utf-8")
        return response.text

    def _throttle(self) -> None:
        if self._last_request_ts is None:
            return
        elapsed = time.monotonic() - self._last_request_ts
        remaining = self.throttle_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)


PERSONATGE_SKIP = {"Principals", "Secundaris", "Altres", "Artistes_convidats"}


def parse_personatges(html: str, source_url: str) -> list[Personatge]:
    """Extract characters from the 'Llista de personatges' article.

    Characters are identified by <h3> elements whose id is NOT in the skip-list.
    The heading text (with any '[modifica]' edit links stripped) is used as the nom.
    Actor information is not extracted (too embedded in prose); callers can supply
    it via data/overrides.json.
    """
    soup = BeautifulSoup(html, "lxml")
    personatges: list[Personatge] = []

    for h3 in soup.find_all("h3"):
        # The id may be on the h3 itself or on a child <span class="mw-headline">
        h3_id = h3.get("id") or ""
        if not h3_id:
            span = h3.find("span", id=True)
            h3_id = span["id"] if span else ""

        if not h3_id or h3_id in PERSONATGE_SKIP:
            continue

        # Extract the display text; prefer the mw-headline span if present
        headline_span = h3.find("span", class_="mw-headline")
        if headline_span:
            nom = headline_span.get_text(strip=True)
        else:
            # Fall back to full h3 text, stripping edit-section links
            for edit_link in h3.find_all(class_="mw-editsection"):
                edit_link.decompose()
            nom = h3.get_text(strip=True)

        if not nom:
            continue

        personatges.append(Personatge(
            slug=slugify(nom),
            nom=nom,
            font_wikipedia=source_url,
        ))

    return personatges


CATALAN_MONTHS = {
    "gener": 1, "febrer": 2, "març": 3, "abril": 4, "maig": 5, "juny": 6,
    "juliol": 7, "agost": 8, "setembre": 9, "octubre": 10, "novembre": 11, "desembre": 12,
}


ORDINAL_TO_SEASON = {
    "primera": 1, "segona": 2, "tercera": 3, "quarta": 4,
    "cinquena": 5, "sisena": 6, "setena": 7, "vuitena": 8,
}


def parse_episodis_i_temporades(html: str, source_url: str) -> tuple[list[Episodi], list[Temporada]]:
    """Parse episodes and seasons from the 'Llista d'episodis' article.

    Seasons are identified by <h3 id="<ordinal>_temporada"> headings, where
    <ordinal> is a Catalan ordinal word (primera, segona, …).  The FIRST wikitable
    that follows each such heading is the episode list for that season.

    Episode rows have 6 cells:
        [0] episode number within season
        [1] episode code (e.g. "1-01")
        [2] title (possibly wrapped in <span><b>…</b></span>)
        [3] director
        [4] script author
        [5] air date
    """
    soup = BeautifulSoup(html, "lxml")
    episodis: list[Episodi] = []
    temporades: list[Temporada] = []

    for h3 in soup.find_all("h3"):
        # The id may be directly on h3 or on a child element
        h3_id = h3.get("id") or ""
        if not h3_id:
            id_el = h3.find(id=True)
            h3_id = id_el["id"] if id_el else ""

        if not h3_id:
            continue

        # Match "<ordinal>_temporada" (case-insensitive)
        m = re.match(r"^([A-Za-z]+)_temporada$", h3_id, re.IGNORECASE)
        if not m:
            continue
        ordinal = m.group(1).lower()
        numero = ORDINAL_TO_SEASON.get(ordinal)
        if numero is None:
            continue

        # Find the first wikitable after this heading
        table = h3.find_next("table", class_="wikitable")
        if table is None:
            continue

        tbody = table.find("tbody") or table
        rows = tbody.find_all("tr")
        season_episodis: list[Episodi] = []
        for row in rows[1:]:  # skip header row
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            num_text = cells[0].get_text(strip=True)
            if not num_text.isdigit():
                continue  # skip colspan separator rows
            # Wikipedia's "Episodi" column is a cumulative global counter.
            # We want per-season numbering, so derive it from position.
            num = len(season_episodis) + 1
            titol = cells[2].get_text(separator=" ", strip=True)
            data_str = cells[5].get_text(strip=True) if len(cells) > 5 else ""
            iso_date = _parse_catalan_date(data_str)

            season_episodis.append(Episodi(
                temporada=numero,
                numero=num,
                titol=titol,
                data_emissio=iso_date,
                font_wikipedia=source_url,
            ))

        episodis.extend(season_episodis)
        anys = sorted({int(e.data_emissio[:4]) for e in season_episodis if e.data_emissio})
        temporades.append(Temporada(
            numero=numero,
            any_inici=anys[0] if anys else None,
            any_fi=anys[-1] if anys else None,
            num_episodis=len(season_episodis),
            episodis=[e.id for e in season_episodis],
        ))

    return episodis, temporades


def _parse_catalan_date(text: str) -> str | None:
    """Parses '12 d'abril de 1999' or '10 de gener del 2000' -> '1999-04-12'. Returns None on failure."""
    match = re.search(r"(\d{1,2})\s+d[e']\s*(\w+)\s+del?\s+(\d{4})", text, re.IGNORECASE)
    if not match:
        return None
    day, month_name, year = match.groups()
    month = CATALAN_MONTHS.get(month_name.lower())
    if not month:
        return None
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"
