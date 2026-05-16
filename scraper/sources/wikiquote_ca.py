import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from scraper.models import Cita
from scraper.slugify import slugify

USER_AGENT = "plats-bruts-api/0.1 (https://github.com/KaarloosT/plats_bruts_api; bastanerada77@gmail.com)"

# Map of "familiar name as it appears in Wikiquote dialogue" → personatge slug.
# Speakers not in this map will produce Cites with personatge=null.
SPEAKER_ALIASES = {
    "Lopes": "josep-lopes",
    "Lópes": "josep-lopes",
    "Josep": "josep-lopes",
    "Josep Lopes": "josep-lopes",
    "David": "david-guell-i-sobirana",
    "Emma": "emma-cruscat-de-palausabullabellobach-i-gonzalez",
    "Carbonell": "conxita-carbonell",
    "Conxita": "conxita-carbonell",
    "Pol": "pol-requena",
    "Mercedes": "maria-de-las-mercedes-de-simancas-i-murrieta",
    "Ramon": "ramon-zamora",
    "Iaia": "iaia-asunsion",
    "Asunsión": "iaia-asunsion",
    "Stasky": "stasky",
}


class WikiquoteCaFetcher:
    """Same caching+throttling behaviour as WikipediaCaFetcher; separate class for clarity."""

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
        # Force UTF-8 decoding — Wikiquote pages declare UTF-8 in meta but
        # requests may infer a different encoding from the Content-Type header.
        response.encoding = "utf-8"
        html = response.text
        cache_file.write_text(html, encoding="utf-8")
        return html

    def _throttle(self) -> None:
        if self._last_request_ts is None:
            return
        elapsed = time.monotonic() - self._last_request_ts
        remaining = self.throttle_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)


# Regex to identify episode section headings. Captures the episode number.
# Examples of id attribute we accept (BS4 decodes entities):
#   Cites_del_capítol_1_"Tinc_pis"
#   Cites_del_capítol_12_"Tinc_problemes_amb_els_papes"
_EPISODE_HEADING_RE = re.compile(r"Cites_del_cap[ií]tol_(\d+)", re.IGNORECASE)
_CITE_REF_RE = re.compile(r"\[\s*(?:\w+\s*)?\d+\s*\]")


def parse_season_quotes(html: str, season: int, source_url: str) -> list[Cita]:
    """Extract all dialogue cites from a Plats Bruts season Wikiquote page.

    Each Cita corresponds to one dialogue block (one <ul> + zero-or-more <dl>).
    Multi-turn dialogues are joined into a single text with newlines, prefixed
    by the speaker name: "Lopes: ...\\nRamon: ...".  The Cita.personatge field
    is the slug of the FIRST speaker (if matched in SPEAKER_ALIASES) or None.
    """
    soup = BeautifulSoup(html, "lxml")
    cites: list[Cita] = []
    # Find all h2 headings that look like episode quote sections
    for h2 in soup.find_all("h2"):
        h2_id = h2.get("id") or ""
        m = _EPISODE_HEADING_RE.search(h2_id)
        if not m:
            continue
        episodi_num = int(m.group(1))
        episodi_id = f"{season}x{episodi_num:02d}"

        # Walk siblings (or the wrapping div's siblings, per Wikiquote layout) until next h2
        walk_from = h2
        if h2.parent and h2.parent.name == "div" and "mw-parser-output" not in (h2.parent.get("class") or []):
            walk_from = h2.parent

        current_block: list[tuple[str, str]] = []  # list of (speaker, text) for the in-progress dialogue
        block_idx_in_episode = 0

        def flush_block():
            nonlocal block_idx_in_episode
            if not current_block:
                return
            block_idx_in_episode += 1
            speakers_text = "\n".join(f"{spk}: {txt}" for spk, txt in current_block)
            first_speaker_name = current_block[0][0].strip()
            personatge_slug = SPEAKER_ALIASES.get(first_speaker_name)
            cita_id = f"wq-{episodi_id}-{block_idx_in_episode:02d}"
            cites.append(Cita(
                id=cita_id,
                text=speakers_text,
                personatge=personatge_slug,
                episodi=episodi_id,
            ))
            current_block.clear()

        for sibling in walk_from.next_siblings:
            tag_name = getattr(sibling, "name", None)
            if tag_name == "h2":
                flush_block()
                break
            if tag_name == "ul":
                # New dialogue starts — flush previous block first
                flush_block()
                for li in sibling.find_all("li", recursive=False):
                    turn = _extract_turn(li)
                    if turn:
                        current_block.append(turn)
            elif tag_name == "dl":
                for dd in sibling.find_all("dd", recursive=False):
                    turn = _extract_turn(dd)
                    if turn:
                        current_block.append(turn)
            # Other tags (p, div with images, etc.) are skipped silently
        # End-of-section: flush any remaining open block
        flush_block()
    return cites


def _extract_turn(element) -> Optional[tuple[str, str]]:
    """Extract (speaker, text) from a <li> or <dd> turn. Returns None on failure."""
    # Find the speaker — first <b> inside the element
    b = element.find("b")
    if not b:
        return None
    speaker = b.get_text(strip=True)
    if not speaker:
        return None
    # Remove the speaker tag and stage-direction <i> tags from a copy, then extract text
    # Note: BeautifulSoup mutates in place — use extract() carefully
    # Strategy: clone via decode + re-parse is overkill; instead, use string traversal.
    parts = []
    found_b = False
    for child in element.children:
        if child is b:
            found_b = True
            continue
        if not found_b:
            continue
        if getattr(child, "name", None) == "sup":
            continue  # skip citation refs
        if getattr(child, "name", None) == "i":
            # stage directions — skip
            continue
        if hasattr(child, "get_text"):
            parts.append(child.get_text(separator=" ", strip=False))
        else:
            parts.append(str(child))
    text = "".join(parts)
    # Strip leading colon/whitespace and citation markers
    text = text.lstrip(": \t\n")
    text = _CITE_REF_RE.sub("", text)
    # Remove empty brackets left over after stage-direction <i> tags were dropped
    # (e.g. "[<i>somrient</i>] hola" became "[] hola").
    text = re.sub(r"\[\s*\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    return (speaker, text)
