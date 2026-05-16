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


def parse_personatges(html: str, source_url: str) -> list[Personatge]:
    soup = BeautifulSoup(html, "lxml")
    heading_span = soup.find("span", id="Personatges")
    if heading_span is None:
        return []
    table = heading_span.find_parent().find_next("table", class_="wikitable")
    if table is None:
        return []

    personatges: list[Personatge] = []
    tbody = table.find("tbody") or table
    rows = tbody.find_all("tr")
    for row in rows[1:]:  # skip header row
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        nom = cells[0].get_text(strip=True)
        actor_text = cells[1].get_text(strip=True)
        temporades_text = cells[2].get_text(strip=True)

        personatges.append(Personatge(
            slug=slugify(nom),
            nom=nom,
            actor=Actor(slug=slugify(actor_text), nom=actor_text),
            temporades=_parse_temporades_range(temporades_text),
            font_wikipedia=source_url,
        ))
    return personatges


def _parse_temporades_range(text: str) -> list[int]:
    """Parses '1-3' -> [1,2,3], '1, 3' -> [1,3], '2' -> [2]."""
    text = text.strip()
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        return list(range(start, end + 1))
    return [int(n.strip()) for n in text.split(",") if n.strip().isdigit()]


CATALAN_MONTHS = {
    "gener": 1, "febrer": 2, "març": 3, "abril": 4, "maig": 5, "juny": 6,
    "juliol": 7, "agost": 8, "setembre": 9, "octubre": 10, "novembre": 11, "desembre": 12,
}


def parse_episodis_i_temporades(html: str, source_url: str) -> tuple[list[Episodi], list[Temporada]]:
    soup = BeautifulSoup(html, "lxml")
    episodis: list[Episodi] = []
    temporades: list[Temporada] = []

    season_spans = soup.find_all("span", id=re.compile(r"^Temporada_\d+$"))
    for span in season_spans:
        numero = int(span["id"].split("_")[1])
        table = span.find_parent().find_next("table", class_="wikitable")
        if table is None:
            continue

        tbody = table.find("tbody") or table
        rows = tbody.find_all("tr")
        season_episodis: list[Episodi] = []
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            num = int(cells[0].get_text(strip=True))
            titol = cells[1].get_text(strip=True)
            data_str = cells[2].get_text(strip=True)
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
    """Parses '12 d'abril de 1999' -> '1999-04-12'. Returns None on failure."""
    match = re.search(r"(\d{1,2})\s+d[e']\s*(\w+)\s+de\s+(\d{4})", text, re.IGNORECASE)
    if not match:
        return None
    day, month_name, year = match.groups()
    month = CATALAN_MONTHS.get(month_name.lower())
    if not month:
        return None
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"
