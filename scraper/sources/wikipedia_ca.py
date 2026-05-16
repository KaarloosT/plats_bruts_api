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

# Regex to extract the actor name from "Interpretat per..." / "Interpretada per..."
# Matches patterns like:
#   "Interpretat per Jordi Sànchez"
#   "Interpretada per la Lloll Bertran"
#   "Interpretat per en Joel Joan,"
# Note: "Interpretat" (masc.) vs "Interpretada" (fem.) — the suffix varies.
_ACTOR_RE = re.compile(
    r"Interpretat(?:da|a)?\s+per\s+(?:la\s+|el\s+|en\s+)?([A-ZÀ-Ÿ][^,.;\n]+?)(?:\s*[,.;]|\s*$)",
    re.IGNORECASE,
)

# Regex to strip Wikipedia citation markers like [1], [2], [nb 1], etc.
_CITE_RE = re.compile(r"\[\s*(?:\w+\s*)?\d+\s*\]")

# Regex to strip "[modifica]" / "[ modifica ]" / "[editar]" edit links
_EDIT_LINK_RE = re.compile(r"\[\s*(?:modifica|editar)\s*\]", re.IGNORECASE)


def _clean_prose(text: str, max_chars: int = 1500) -> str:
    """Strip citation markers and edit-link artefacts from Wikipedia prose, then trim."""
    text = _CITE_RE.sub("", text)
    text = _EDIT_LINK_RE.sub("", text)
    # Collapse internal whitespace and newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def parse_personatges(html: str, source_url: str) -> list[Personatge]:
    """Extract characters from the 'Llista de personatges' article.

    Characters are identified by <h3> elements whose id is NOT in the skip-list.
    For each character the parser walks forward through the DOM siblings until it
    hits the next <h2> or <h3>, accumulating <p> text as the description.

    From that accumulated prose:
    - ``descripcio``: cleaned prose (citation markers and edit links stripped,
      whitespace collapsed, capped at 1500 chars).  The leading "Interpretat
      per X" sentence is kept inside descripcio — it duplicates the actor field
      slightly but preserves the natural opening of each character's biography.
    - ``actor``: extracted via a regex on the prose.  Both ``nom`` and ``slug``
      are derived from the captured name string.

    ``nom_complet`` is left as None because the h3 text is already used as
    ``nom``; the field exists for overrides to fill in when needed.
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

        # Walk siblings after this h3 (or its parent wrapper div if Wikipedia
        # rendered the h3 inside a <div>) collecting <p> text until the next
        # block-level heading.
        # Modern Wikipedia wraps <h3> + its edit-section span inside a <div>;
        # the following <p> paragraphs are siblings of that wrapping <div>, not
        # of the <h3> itself.  We detect this by checking whether the h3's
        # parent is a <div> that is not the mw-parser-output container itself.
        walk_from = h3
        if h3.parent and h3.parent.name == "div" and "mw-parser-output" not in (h3.parent.get("class") or []):
            walk_from = h3.parent

        prose_parts: list[str] = []
        for sibling in walk_from.next_siblings:
            tag_name = getattr(sibling, "name", None)
            if tag_name in ("h2", "h3", "div"):
                # Stop at the next heading or heading-wrapper div.
                # We peek inside divs to see if they contain an h2/h3.
                if tag_name == "div":
                    inner = sibling.find(["h2", "h3"])
                    if inner:
                        break
                    # Otherwise it might be a content div — fall through to collect p inside
                    for p in sibling.find_all("p", recursive=False):
                        prose_parts.append(p.get_text(separator=" ", strip=True))
                else:
                    break
            elif tag_name == "p":
                prose_parts.append(sibling.get_text(separator=" ", strip=True))

        raw_prose = " ".join(prose_parts)
        descripcio = _clean_prose(raw_prose) if raw_prose.strip() else None

        # Extract actor from prose
        actor: Optional[Actor] = None
        if raw_prose:
            m = _ACTOR_RE.search(raw_prose)
            if m:
                actor_nom = m.group(1).strip()
                actor = Actor(slug=slugify(actor_nom), nom=actor_nom)

        personatges.append(Personatge(
            slug=slugify(nom),
            nom=nom,
            descripcio=descripcio,
            actor=actor,
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
        rows = list(tbody.find_all("tr"))
        season_episodis: list[Episodi] = []
        for idx in range(1, len(rows)):  # skip header row at index 0
            row = rows[idx]
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

            # Check if the NEXT row is a synopsis row:
            # a synopsis row has exactly one <td> with a colspan attribute.
            sinopsi: Optional[str] = None
            next_idx = idx + 1
            if next_idx < len(rows):
                next_cells = rows[next_idx].find_all(["td", "th"])
                if len(next_cells) == 1 and next_cells[0].get("colspan"):
                    raw_sinopsi = next_cells[0].get_text(separator=" ", strip=True)
                    sinopsi = _clean_prose(raw_sinopsi) if raw_sinopsi.strip() else None

            season_episodis.append(Episodi(
                temporada=numero,
                numero=num,
                titol=titol,
                sinopsi=sinopsi,
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
