import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from scraper.models import Actor, Personatge
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
