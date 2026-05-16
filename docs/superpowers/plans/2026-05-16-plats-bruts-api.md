# Plats Bruts API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static REST API of Plats Bruts (TV3) data, served from GitHub Pages, with data scraped from Catalan Wikipedia.

**Architecture:** A Python scraper reads Catalan Wikipedia pages, parses them with BeautifulSoup, merges in manual overrides, and emits a tree of static JSON files under `api/v1/`. GitHub Pages serves the JSON tree and a documentation page. No backend, no database. Tests use offline HTML fixtures so the scraper logic is verifiable without hitting the network.

**Tech Stack:** Python 3.11+, `requests`, `beautifulsoup4`, `pytest`. GitHub Pages + GitHub Actions for hosting and CI.

---

## File Structure

**To create:**

| Path | Purpose |
|---|---|
| `pyproject.toml` | Project metadata, dependencies, pytest config |
| `.gitignore` | Ignore venv, cache, build artifacts |
| `README.md` | Public-facing repo description + how to regenerate |
| `scraper/__init__.py` | Package marker |
| `scraper/slugify.py` | `slugify(text)` helper — ASCII, no accents, lowercase |
| `scraper/models.py` | Dataclasses for each resource + `to_dict()` |
| `scraper/sources/__init__.py` | Package marker |
| `scraper/sources/wikipedia_ca.py` | Wikipedia fetcher (cache + throttle) and parsers |
| `scraper/overrides.py` | Load and deep-merge `data/overrides.json` |
| `scraper/emit.py` | Write JSON tree under `api/v1/` |
| `scraper/build.py` | Orchestrator: scrape → merge → emit |
| `scraper/tests/__init__.py` | Package marker |
| `scraper/tests/conftest.py` | Shared pytest fixtures |
| `scraper/tests/fixtures/wiki_plats_bruts.html` | Saved Wikipedia HTML for tests |
| `scraper/tests/fixtures/wiki_llista_episodis.html` | Saved episode list HTML for tests |
| `scraper/tests/test_slugify.py` | Tests for slugify |
| `scraper/tests/test_models.py` | Tests for dataclass serialization |
| `scraper/tests/test_wikipedia_ca.py` | Tests for parsers using fixtures |
| `scraper/tests/test_overrides.py` | Tests for override merging |
| `scraper/tests/test_emit.py` | Tests for JSON tree emission |
| `scraper/tests/test_build.py` | End-to-end integration test |
| `data/overrides.json` | Seed manual overrides (starts mostly empty) |
| `docs/index.html` | Public documentation page |
| `.github/workflows/build.yml` | Manual workflow that runs scraper and commits JSON |
| `.github/workflows/deploy.yml` | Deploys to GitHub Pages on push to main |

**Design rationale:**
- One file per source (`sources/wikipedia_ca.py`) so adding sources later (e.g. 3cat.cat) is additive.
- `models.py`, `overrides.py`, `emit.py`, `build.py` are split by responsibility so each stays small and testable in isolation.
- Tests use HTML fixtures saved to disk, never live Wikipedia, so CI is deterministic.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "plats-bruts-api"
version = "0.1.0"
description = "Static REST API of Plats Bruts (TV3) data"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "lxml>=4.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
]

[tool.pytest.ini_options]
testpaths = ["scraper/tests"]
pythonpath = ["."]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/
scraper/.cache/
*.egg-info/
build/
dist/
```

- [ ] **Step 3: Create initial `README.md`**

```markdown
# Plats Bruts API

A static REST API of data about the Catalan sitcom **Plats Bruts** (TV3, 1999-2002), inspired by PokéAPI. Hosted on GitHub Pages, with no auth and no rate limits.

> Fan project, not affiliated with TV3 or the production company. Data sourced from Wikipedia (CC BY-SA).

## Endpoints

Base URL: `https://<user>.github.io/plats-bruts-api/api/v1/`

Documentation: see `docs/index.html` (also served from GitHub Pages root).

## Regenerating the data

```bash
pip install -e ".[dev]"
python -m scraper.build
```

## Tests

```bash
pytest
```
```

- [ ] **Step 4: Install dependencies and verify**

Run: `pip install -e ".[dev]"`
Expected: installs `requests`, `beautifulsoup4`, `lxml`, `pytest`, `pytest-cov`. No errors.

Run: `pytest --collect-only`
Expected: "no tests ran" or "collected 0 items" (no tests exist yet).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore README.md
git commit -m "chore: project scaffolding"
```

---

## Task 2: Slug helper

**Files:**
- Create: `scraper/__init__.py` (empty)
- Create: `scraper/slugify.py`
- Create: `scraper/tests/__init__.py` (empty)
- Test: `scraper/tests/test_slugify.py`

- [ ] **Step 1: Create empty package markers**

Create `scraper/__init__.py` with content: `` (empty file)
Create `scraper/tests/__init__.py` with content: `` (empty file)

- [ ] **Step 2: Write the failing tests**

Create `scraper/tests/test_slugify.py`:

```python
from scraper.slugify import slugify


def test_lowercase():
    assert slugify("Lofi") == "lofi"


def test_removes_accents():
    assert slugify("Em·li") == "emili"


def test_removes_apostrophes():
    assert slugify("Mortimer's") == "mortimers"


def test_collapses_spaces_to_hyphens():
    assert slugify("Joel Joan") == "joel-joan"


def test_preserves_existing_hyphens():
    assert slugify("Pere-Lluís") == "pere-lluis"


def test_strips_leading_trailing_punctuation():
    assert slugify(" -hello- ") == "hello"


def test_collapses_repeated_hyphens():
    assert slugify("a  b") == "a-b"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest scraper/tests/test_slugify.py -v`
Expected: ImportError or ModuleNotFoundError for `scraper.slugify`.

- [ ] **Step 4: Implement `scraper/slugify.py`**

```python
import re
import unicodedata


def slugify(text: str) -> str:
    """Normalize a string to an ASCII, lowercase, hyphen-separated slug."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    return cleaned.strip("-")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest scraper/tests/test_slugify.py -v`
Expected: all 7 tests pass.

- [ ] **Step 6: Commit**

```bash
git add scraper/__init__.py scraper/slugify.py scraper/tests/__init__.py scraper/tests/test_slugify.py
git commit -m "feat(scraper): add slugify helper"
```

---

## Task 3: Resource dataclasses

**Files:**
- Create: `scraper/models.py`
- Test: `scraper/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Create `scraper/tests/test_models.py`:

```python
from scraper.models import Actor, Personatge, Episodi, Temporada, Cita, Localitzacio


def test_personatge_to_dict():
    p = Personatge(
        slug="lofi",
        nom="Lofi",
        nom_complet="Lluís Fernández",
        descripcio="Estudiant de filosofia.",
        actor=Actor(slug="joel-joan", nom="Joel Joan"),
        temporades=[1, 2, 3],
        primera_aparicio="1x01",
        imatge="https://example.com/lofi.jpg",
        font_wikipedia="https://ca.wikipedia.org/wiki/Plats_bruts",
    )
    assert p.to_dict() == {
        "slug": "lofi",
        "nom": "Lofi",
        "nom_complet": "Lluís Fernández",
        "descripcio": "Estudiant de filosofia.",
        "actor": {"slug": "joel-joan", "nom": "Joel Joan"},
        "temporades": [1, 2, 3],
        "primera_aparicio": "1x01",
        "imatge": "https://example.com/lofi.jpg",
        "font_wikipedia": "https://ca.wikipedia.org/wiki/Plats_bruts",
    }


def test_personatge_index_entry():
    p = Personatge(slug="lofi", nom="Lofi")
    assert p.index_entry() == {
        "slug": "lofi",
        "nom": "Lofi",
        "url": "/api/v1/personatges/lofi.json",
    }


def test_episodi_id_format():
    e = Episodi(temporada=1, numero=3, titol="...")
    assert e.id == "1x03"


def test_episodi_id_double_digit():
    e = Episodi(temporada=2, numero=12, titol="...")
    assert e.id == "2x12"


def test_temporada_to_dict():
    t = Temporada(numero=1, any_inici=1999, any_fi=1999, num_episodis=2, episodis=["1x01", "1x02"])
    assert t.to_dict() == {
        "numero": 1,
        "any_inici": 1999,
        "any_fi": 1999,
        "num_episodis": 2,
        "episodis": ["1x01", "1x02"],
    }


def test_cita_to_dict():
    c = Cita(id="c001", text="Que potes!", personatge="lofi", episodi="1x01")
    assert c.to_dict() == {
        "id": "c001",
        "text": "Que potes!",
        "personatge": "lofi",
        "episodi": "1x01",
    }


def test_localitzacio_to_dict():
    l = Localitzacio(slug="mortimers", nom="Mortimer's", descripcio="El bar.", episodis=["1x01"], imatge=None)
    assert l.to_dict() == {
        "slug": "mortimers",
        "nom": "Mortimer's",
        "descripcio": "El bar.",
        "episodis": ["1x01"],
        "imatge": None,
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest scraper/tests/test_models.py -v`
Expected: ImportError for `scraper.models`.

- [ ] **Step 3: Implement `scraper/models.py`**

```python
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Actor:
    slug: str
    nom: str

    def to_dict(self) -> dict:
        return {"slug": self.slug, "nom": self.nom}


@dataclass
class Personatge:
    slug: str
    nom: str
    nom_complet: Optional[str] = None
    descripcio: Optional[str] = None
    actor: Optional[Actor] = None
    temporades: list[int] = field(default_factory=list)
    primera_aparicio: Optional[str] = None
    imatge: Optional[str] = None
    font_wikipedia: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "nom": self.nom,
            "nom_complet": self.nom_complet,
            "descripcio": self.descripcio,
            "actor": self.actor.to_dict() if self.actor else None,
            "temporades": list(self.temporades),
            "primera_aparicio": self.primera_aparicio,
            "imatge": self.imatge,
            "font_wikipedia": self.font_wikipedia,
        }

    def index_entry(self) -> dict:
        return {
            "slug": self.slug,
            "nom": self.nom,
            "url": f"/api/v1/personatges/{self.slug}.json",
        }


@dataclass
class Episodi:
    temporada: int
    numero: int
    titol: str
    sinopsi: Optional[str] = None
    data_emissio: Optional[str] = None
    duracio_min: Optional[int] = None
    personatges: list[str] = field(default_factory=list)
    localitzacions: list[str] = field(default_factory=list)
    cites: list[str] = field(default_factory=list)
    font_wikipedia: Optional[str] = None

    @property
    def id(self) -> str:
        return f"{self.temporada}x{self.numero:02d}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "temporada": self.temporada,
            "numero": self.numero,
            "titol": self.titol,
            "sinopsi": self.sinopsi,
            "data_emissio": self.data_emissio,
            "duracio_min": self.duracio_min,
            "personatges": list(self.personatges),
            "localitzacions": list(self.localitzacions),
            "cites": list(self.cites),
            "font_wikipedia": self.font_wikipedia,
        }

    def index_entry(self) -> dict:
        return {
            "id": self.id,
            "titol": self.titol,
            "url": f"/api/v1/episodis/{self.id}.json",
        }


@dataclass
class Temporada:
    numero: int
    any_inici: Optional[int] = None
    any_fi: Optional[int] = None
    num_episodis: int = 0
    episodis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "numero": self.numero,
            "any_inici": self.any_inici,
            "any_fi": self.any_fi,
            "num_episodis": self.num_episodis,
            "episodis": list(self.episodis),
        }

    def index_entry(self) -> dict:
        return {
            "numero": self.numero,
            "url": f"/api/v1/temporades/{self.numero}.json",
        }


@dataclass
class Cita:
    id: str
    text: str
    personatge: Optional[str] = None
    episodi: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "personatge": self.personatge,
            "episodi": self.episodi,
        }

    def index_entry(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "url": f"/api/v1/cites/{self.id}.json",
        }


@dataclass
class Localitzacio:
    slug: str
    nom: str
    descripcio: Optional[str] = None
    episodis: list[str] = field(default_factory=list)
    imatge: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "nom": self.nom,
            "descripcio": self.descripcio,
            "episodis": list(self.episodis),
            "imatge": self.imatge,
        }

    def index_entry(self) -> dict:
        return {
            "slug": self.slug,
            "nom": self.nom,
            "url": f"/api/v1/localitzacions/{self.slug}.json",
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest scraper/tests/test_models.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scraper/models.py scraper/tests/test_models.py
git commit -m "feat(scraper): add resource dataclasses"
```

---

## Task 4: Wikipedia fetcher (HTTP layer with cache and throttle)

**Files:**
- Create: `scraper/sources/__init__.py` (empty)
- Create: `scraper/sources/wikipedia_ca.py` (fetcher only — parsers come later)
- Test: `scraper/tests/test_wikipedia_ca.py`

- [ ] **Step 1: Create package marker**

Create `scraper/sources/__init__.py` with content: `` (empty file).

- [ ] **Step 2: Write the failing tests for the fetcher**

Create `scraper/tests/test_wikipedia_ca.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest scraper/tests/test_wikipedia_ca.py -v`
Expected: ImportError for `scraper.sources.wikipedia_ca`.

- [ ] **Step 4: Implement the fetcher**

Create `scraper/sources/wikipedia_ca.py`:

```python
import time
from pathlib import Path
from typing import Optional

import requests

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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest scraper/tests/test_wikipedia_ca.py -v`
Expected: all 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add scraper/sources/__init__.py scraper/sources/wikipedia_ca.py scraper/tests/test_wikipedia_ca.py
git commit -m "feat(scraper): add cached, throttled Wikipedia fetcher"
```

---

## Task 5: HTML fixtures for parser tests

**Files:**
- Create: `scraper/tests/fixtures/wiki_plats_bruts.html`
- Create: `scraper/tests/fixtures/wiki_llista_episodis.html`
- Create: `scraper/tests/conftest.py`

These fixtures are minimal — just enough HTML to exercise the parser. We do not save real Wikipedia pages (too noisy). The parsers are designed against this fixture shape and validated end-to-end in Task 11.

- [ ] **Step 1: Create `scraper/tests/fixtures/wiki_plats_bruts.html`**

```html
<!DOCTYPE html>
<html>
<body>
<h2><span id="Personatges">Personatges</span></h2>
<table class="wikitable">
  <tbody>
    <tr><th>Personatge</th><th>Actor</th><th>Temporades</th></tr>
    <tr>
      <td>Lofi</td>
      <td><a href="/wiki/Joel_Joan">Joel Joan</a></td>
      <td>1-3</td>
    </tr>
    <tr>
      <td>Em·li</td>
      <td><a href="/wiki/Jordi_S%C3%A0nchez">Jordi Sànchez</a></td>
      <td>1-3</td>
    </tr>
  </tbody>
</table>
</body>
</html>
```

- [ ] **Step 2: Create `scraper/tests/fixtures/wiki_llista_episodis.html`**

```html
<!DOCTYPE html>
<html>
<body>
<h2><span id="Temporada_1">Temporada 1</span></h2>
<table class="wikitable">
  <tbody>
    <tr><th>Núm.</th><th>Títol</th><th>Data d'emissió</th></tr>
    <tr><td>1</td><td>Pilot</td><td>12 d'abril de 1999</td></tr>
    <tr><td>2</td><td>El nou company</td><td>19 d'abril de 1999</td></tr>
  </tbody>
</table>
<h2><span id="Temporada_2">Temporada 2</span></h2>
<table class="wikitable">
  <tbody>
    <tr><th>Núm.</th><th>Títol</th><th>Data d'emissió</th></tr>
    <tr><td>1</td><td>Tornada</td><td>15 de gener de 2000</td></tr>
  </tbody>
</table>
</body>
</html>
```

- [ ] **Step 3: Create `scraper/tests/conftest.py`**

```python
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def plats_bruts_html() -> str:
    return (FIXTURES / "wiki_plats_bruts.html").read_text(encoding="utf-8")


@pytest.fixture
def llista_episodis_html() -> str:
    return (FIXTURES / "wiki_llista_episodis.html").read_text(encoding="utf-8")
```

- [ ] **Step 4: Verify fixtures load**

Run: `pytest scraper/tests/ -v`
Expected: existing tests still pass. The new fixtures are not yet used.

- [ ] **Step 5: Commit**

```bash
git add scraper/tests/fixtures/ scraper/tests/conftest.py
git commit -m "test(scraper): add Wikipedia HTML fixtures"
```

---

## Task 6: Wikipedia parser — characters

**Files:**
- Modify: `scraper/sources/wikipedia_ca.py` (add parser function)
- Modify: `scraper/tests/test_wikipedia_ca.py` (add parser tests)

- [ ] **Step 1: Append failing tests to `scraper/tests/test_wikipedia_ca.py`**

Add at the end of the file:

```python
from scraper.sources.wikipedia_ca import parse_personatges


def test_parse_personatges_extracts_rows(plats_bruts_html):
    personatges = parse_personatges(plats_bruts_html, source_url="https://ca.wikipedia.org/wiki/Plats_bruts")

    assert len(personatges) == 2
    lofi = personatges[0]
    assert lofi.slug == "lofi"
    assert lofi.nom == "Lofi"
    assert lofi.actor.slug == "joel-joan"
    assert lofi.actor.nom == "Joel Joan"
    assert lofi.temporades == [1, 2, 3]
    assert lofi.font_wikipedia == "https://ca.wikipedia.org/wiki/Plats_bruts"


def test_parse_personatges_handles_accented_names(plats_bruts_html):
    personatges = parse_personatges(plats_bruts_html, source_url="https://ca.wikipedia.org/wiki/Plats_bruts")
    emili = personatges[1]
    assert emili.nom == "Em·li"
    assert emili.slug == "emili"
    assert emili.actor.nom == "Jordi Sànchez"
    assert emili.actor.slug == "jordi-sanchez"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest scraper/tests/test_wikipedia_ca.py::test_parse_personatges_extracts_rows -v`
Expected: ImportError for `parse_personatges`.

- [ ] **Step 3: Implement parser in `scraper/sources/wikipedia_ca.py`**

Append to the file:

```python
import re
from bs4 import BeautifulSoup

from scraper.models import Actor, Personatge
from scraper.slugify import slugify


def parse_personatges(html: str, source_url: str) -> list[Personatge]:
    soup = BeautifulSoup(html, "lxml")
    heading_span = soup.find("span", id="Personatges")
    if heading_span is None:
        return []
    table = heading_span.find_parent().find_next("table", class_="wikitable")
    if table is None:
        return []

    personatges: list[Personatge] = []
    rows = table.find("tbody").find_all("tr")
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
    """Parses '1-3' → [1,2,3], '1, 3' → [1,3], '2' → [2]."""
    text = text.strip()
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        return list(range(start, end + 1))
    return [int(n.strip()) for n in text.split(",") if n.strip().isdigit()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest scraper/tests/test_wikipedia_ca.py -v`
Expected: all 5 tests pass (3 fetcher + 2 parser).

- [ ] **Step 5: Commit**

```bash
git add scraper/sources/wikipedia_ca.py scraper/tests/test_wikipedia_ca.py
git commit -m "feat(scraper): parse personatges from Wikipedia"
```

---

## Task 7: Wikipedia parser — episodes and seasons

**Files:**
- Modify: `scraper/sources/wikipedia_ca.py` (add `parse_episodis_i_temporades`)
- Modify: `scraper/tests/test_wikipedia_ca.py` (add tests)

- [ ] **Step 1: Append failing tests to `scraper/tests/test_wikipedia_ca.py`**

Add at the end of the file:

```python
from scraper.sources.wikipedia_ca import parse_episodis_i_temporades


def test_parse_episodis_extracts_per_season(llista_episodis_html):
    episodis, temporades = parse_episodis_i_temporades(
        llista_episodis_html,
        source_url="https://ca.wikipedia.org/wiki/Llista_d%27episodis_de_Plats_bruts",
    )

    assert len(episodis) == 3
    assert episodis[0].id == "1x01"
    assert episodis[0].titol == "Pilot"
    assert episodis[0].data_emissio == "1999-04-12"
    assert episodis[1].id == "1x02"
    assert episodis[2].id == "2x01"
    assert episodis[2].titol == "Tornada"


def test_parse_temporades_groups_episodis(llista_episodis_html):
    _, temporades = parse_episodis_i_temporades(
        llista_episodis_html,
        source_url="https://ca.wikipedia.org/wiki/Llista_d%27episodis_de_Plats_bruts",
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
    assert t2.any_inici == 2000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest scraper/tests/test_wikipedia_ca.py::test_parse_episodis_extracts_per_season -v`
Expected: ImportError for `parse_episodis_i_temporades`.

- [ ] **Step 3: Implement parsers in `scraper/sources/wikipedia_ca.py`**

Append to the file:

```python
from scraper.models import Episodi, Temporada

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

        season_episodis: list[Episodi] = []
        rows = table.find("tbody").find_all("tr")
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
    """Parses '12 d'abril de 1999' → '1999-04-12'. Returns None on failure."""
    match = re.search(r"(\d{1,2})\s+d[e']\s*(\w+)\s+de\s+(\d{4})", text, re.IGNORECASE)
    if not match:
        return None
    day, month_name, year = match.groups()
    month = CATALAN_MONTHS.get(month_name.lower())
    if not month:
        return None
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest scraper/tests/test_wikipedia_ca.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scraper/sources/wikipedia_ca.py scraper/tests/test_wikipedia_ca.py
git commit -m "feat(scraper): parse episodis and temporades from Wikipedia"
```

---

## Task 8: Overrides merger

**Files:**
- Create: `scraper/overrides.py`
- Create: `data/overrides.json` (initial seed)
- Test: `scraper/tests/test_overrides.py`

- [ ] **Step 1: Write the failing tests**

Create `scraper/tests/test_overrides.py`:

```python
import json
from pathlib import Path

from scraper.models import Actor, Cita, Localitzacio, Personatge
from scraper.overrides import Overrides, load_overrides


def test_load_overrides_from_file(tmp_path):
    overrides_file = tmp_path / "overrides.json"
    overrides_file.write_text(json.dumps({
        "personatges": {"lofi": {"descripcio": "Estudiant de filosofia."}},
        "cites": [{"id": "c001", "text": "Que potes!", "personatge": "lofi", "episodi": "1x01"}],
        "localitzacions": [{"slug": "pis", "nom": "El pis", "descripcio": "L'apartament."}],
    }), encoding="utf-8")

    overrides = load_overrides(overrides_file)
    assert overrides.personatge_patches["lofi"] == {"descripcio": "Estudiant de filosofia."}
    assert len(overrides.cites) == 1
    assert overrides.cites[0].id == "c001"
    assert len(overrides.localitzacions) == 1
    assert overrides.localitzacions[0].slug == "pis"


def test_load_overrides_missing_file_returns_empty(tmp_path):
    overrides = load_overrides(tmp_path / "missing.json")
    assert overrides.personatge_patches == {}
    assert overrides.cites == []
    assert overrides.localitzacions == []


def test_apply_personatge_patch_overrides_fields():
    p = Personatge(slug="lofi", nom="Lofi", actor=Actor(slug="joel-joan", nom="Joel Joan"))
    overrides = Overrides(
        personatge_patches={"lofi": {"descripcio": "Estudiant.", "nom_complet": "Lluís Fernández"}},
        cites=[],
        localitzacions=[],
    )
    patched = overrides.apply_to_personatges([p])
    assert patched[0].descripcio == "Estudiant."
    assert patched[0].nom_complet == "Lluís Fernández"
    assert patched[0].actor.nom == "Joel Joan"  # not overridden


def test_apply_personatge_patch_ignores_unknown_slugs():
    p = Personatge(slug="lofi", nom="Lofi")
    overrides = Overrides(
        personatge_patches={"unknown": {"descripcio": "..."}},
        cites=[],
        localitzacions=[],
    )
    patched = overrides.apply_to_personatges([p])
    assert patched[0].descripcio is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest scraper/tests/test_overrides.py -v`
Expected: ImportError for `scraper.overrides`.

- [ ] **Step 3: Implement `scraper/overrides.py`**

```python
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from scraper.models import Cita, Localitzacio, Personatge


@dataclass
class Overrides:
    personatge_patches: dict[str, dict] = field(default_factory=dict)
    cites: list[Cita] = field(default_factory=list)
    localitzacions: list[Localitzacio] = field(default_factory=list)

    def apply_to_personatges(self, personatges: list[Personatge]) -> list[Personatge]:
        out = []
        for p in personatges:
            patch = self.personatge_patches.get(p.slug)
            if not patch:
                out.append(p)
                continue
            valid_fields = {k: v for k, v in patch.items() if k in p.__dataclass_fields__}
            out.append(replace(p, **valid_fields))
        return out


def load_overrides(path: Path) -> Overrides:
    path = Path(path)
    if not path.exists():
        return Overrides()
    data = json.loads(path.read_text(encoding="utf-8"))
    return Overrides(
        personatge_patches=data.get("personatges", {}),
        cites=[Cita(**c) for c in data.get("cites", [])],
        localitzacions=[Localitzacio(**l) for l in data.get("localitzacions", [])],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest scraper/tests/test_overrides.py -v`
Expected: all 4 tests pass.

- [ ] **Step 5: Create initial `data/overrides.json`**

```json
{
  "personatges": {},
  "cites": [],
  "localitzacions": []
}
```

- [ ] **Step 6: Commit**

```bash
git add scraper/overrides.py scraper/tests/test_overrides.py data/overrides.json
git commit -m "feat(scraper): load and apply manual overrides"
```

---

## Task 9: JSON emitter

**Files:**
- Create: `scraper/emit.py`
- Test: `scraper/tests/test_emit.py`

- [ ] **Step 1: Write the failing tests**

Create `scraper/tests/test_emit.py`:

```python
import json
from pathlib import Path

from scraper.models import Cita, Episodi, Localitzacio, Personatge, Temporada
from scraper.emit import emit_api


def test_emit_writes_personatge_detail_and_index(tmp_path):
    lofi = Personatge(slug="lofi", nom="Lofi")
    emit_api(
        tmp_path,
        personatges=[lofi],
        episodis=[],
        temporades=[],
        cites=[],
        localitzacions=[],
    )

    detail_file = tmp_path / "api" / "v1" / "personatges" / "lofi.json"
    assert detail_file.exists()
    assert json.loads(detail_file.read_text(encoding="utf-8"))["slug"] == "lofi"

    index_file = tmp_path / "api" / "v1" / "personatges" / "index.json"
    index = json.loads(index_file.read_text(encoding="utf-8"))
    assert index["count"] == 1
    assert index["results"][0]["slug"] == "lofi"
    assert index["results"][0]["url"] == "/api/v1/personatges/lofi.json"


def test_emit_writes_all_resource_types(tmp_path):
    emit_api(
        tmp_path,
        personatges=[Personatge(slug="lofi", nom="Lofi")],
        episodis=[Episodi(temporada=1, numero=1, titol="Pilot")],
        temporades=[Temporada(numero=1)],
        cites=[Cita(id="c001", text="Que potes!")],
        localitzacions=[Localitzacio(slug="pis", nom="El pis")],
    )

    base = tmp_path / "api" / "v1"
    assert (base / "personatges" / "index.json").exists()
    assert (base / "episodis" / "index.json").exists()
    assert (base / "episodis" / "1x01.json").exists()
    assert (base / "temporades" / "index.json").exists()
    assert (base / "temporades" / "1.json").exists()
    assert (base / "cites" / "index.json").exists()
    assert (base / "cites" / "c001.json").exists()
    assert (base / "localitzacions" / "index.json").exists()
    assert (base / "localitzacions" / "pis.json").exists()


def test_emit_overwrites_stale_files(tmp_path):
    stale = tmp_path / "api" / "v1" / "personatges" / "stale.json"
    stale.parent.mkdir(parents=True)
    stale.write_text("{}", encoding="utf-8")

    emit_api(
        tmp_path,
        personatges=[Personatge(slug="lofi", nom="Lofi")],
        episodis=[], temporades=[], cites=[], localitzacions=[],
    )

    # Stale file from a previous run should be cleaned up.
    assert not stale.exists()
    assert (tmp_path / "api" / "v1" / "personatges" / "lofi.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest scraper/tests/test_emit.py -v`
Expected: ImportError for `scraper.emit`.

- [ ] **Step 3: Implement `scraper/emit.py`**

```python
import json
import shutil
from pathlib import Path

from scraper.models import Cita, Episodi, Localitzacio, Personatge, Temporada


def emit_api(
    root: Path,
    *,
    personatges: list[Personatge],
    episodis: list[Episodi],
    temporades: list[Temporada],
    cites: list[Cita],
    localitzacions: list[Localitzacio],
) -> None:
    base = Path(root) / "api" / "v1"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    _emit_collection(base / "personatges", personatges, key_attr="slug")
    _emit_collection(base / "episodis", episodis, key_attr="id")
    _emit_collection(base / "temporades", temporades, key_attr="numero")
    _emit_collection(base / "cites", cites, key_attr="id")
    _emit_collection(base / "localitzacions", localitzacions, key_attr="slug")


def _emit_collection(directory: Path, items: list, *, key_attr: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for item in items:
        key = getattr(item, key_attr)
        (directory / f"{key}.json").write_text(
            json.dumps(item.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    index = {"count": len(items), "results": [item.index_entry() for item in items]}
    (directory / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest scraper/tests/test_emit.py -v`
Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scraper/emit.py scraper/tests/test_emit.py
git commit -m "feat(scraper): emit static JSON tree"
```

---

## Task 10: Build orchestrator

**Files:**
- Create: `scraper/build.py`
- Test: `scraper/tests/test_build.py`

- [ ] **Step 1: Write the failing test**

Create `scraper/tests/test_build.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch

from scraper.build import build


def test_build_end_to_end(tmp_path, plats_bruts_html, llista_episodis_html):
    repo_root = tmp_path
    (repo_root / "data").mkdir()
    (repo_root / "data" / "overrides.json").write_text(json.dumps({
        "personatges": {"lofi": {"descripcio": "Estudiant de filosofia."}},
        "cites": [{"id": "c001", "text": "Que potes!", "personatge": "lofi", "episodi": "1x01"}],
        "localitzacions": [{"slug": "pis", "nom": "El pis", "descripcio": "L'apartament."}]
    }), encoding="utf-8")

    def fake_fetch(url, cache_key):
        if "Llista" in url:
            return llista_episodis_html
        return plats_bruts_html

    with patch("scraper.build.WikipediaCaFetcher") as MockFetcher:
        MockFetcher.return_value.fetch.side_effect = fake_fetch
        build(repo_root=repo_root)

    base = repo_root / "api" / "v1"
    lofi = json.loads((base / "personatges" / "lofi.json").read_text(encoding="utf-8"))
    assert lofi["descripcio"] == "Estudiant de filosofia."

    ep = json.loads((base / "episodis" / "1x01.json").read_text(encoding="utf-8"))
    assert ep["titol"] == "Pilot"

    cita = json.loads((base / "cites" / "c001.json").read_text(encoding="utf-8"))
    assert cita["text"] == "Que potes!"

    pis = json.loads((base / "localitzacions" / "pis.json").read_text(encoding="utf-8"))
    assert pis["nom"] == "El pis"

    indexes = ["personatges", "episodis", "temporades", "cites", "localitzacions"]
    for name in indexes:
        idx = json.loads((base / name / "index.json").read_text(encoding="utf-8"))
        assert idx["count"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest scraper/tests/test_build.py -v`
Expected: ImportError for `scraper.build`.

- [ ] **Step 3: Implement `scraper/build.py`**

```python
from pathlib import Path

from scraper.emit import emit_api
from scraper.overrides import load_overrides
from scraper.sources.wikipedia_ca import (
    WikipediaCaFetcher,
    parse_episodis_i_temporades,
    parse_personatges,
)

WIKI_SERIE_URL = "https://ca.wikipedia.org/wiki/Plats_bruts"
WIKI_EPISODIS_URL = "https://ca.wikipedia.org/wiki/Llista_d%27episodis_de_Plats_bruts"


def build(repo_root: Path) -> None:
    repo_root = Path(repo_root)
    cache_dir = repo_root / "scraper" / ".cache"

    fetcher = WikipediaCaFetcher(cache_dir=cache_dir)
    serie_html = fetcher.fetch(WIKI_SERIE_URL, cache_key="serie")
    episodis_html = fetcher.fetch(WIKI_EPISODIS_URL, cache_key="episodis")

    personatges = parse_personatges(serie_html, source_url=WIKI_SERIE_URL)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest scraper/tests/test_build.py -v`
Expected: PASS.

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: all tests (slugify + models + wikipedia_ca + overrides + emit + build) pass. ~20 tests total.

- [ ] **Step 6: Commit**

```bash
git add scraper/build.py scraper/tests/test_build.py
git commit -m "feat(scraper): orchestrate end-to-end build"
```

---

## Task 11: First real run

**Files:**
- Modify: `api/v1/**` (generated)

- [ ] **Step 1: Run the build against real Wikipedia**

Run: `python -m scraper.build`
Expected: completes without error. Creates `scraper/.cache/serie.html` and `scraper/.cache/episodis.html`. Creates the full `api/v1/` tree.

- [ ] **Step 2: Spot-check the output**

Run: `ls api/v1/personatges/`
Expected: at least `index.json` and one `*.json` per character row found in Wikipedia's character table. Number depends on what's there at scrape time.

Run: `python -c "import json; print(json.dumps(json.load(open('api/v1/personatges/index.json', encoding='utf-8')), indent=2, ensure_ascii=False))"`
Expected: a `count` and `results` array with character entries.

Note: if Wikipedia's HTML structure differs from our fixture (different table layout, missing section header, etc.), some entries may be empty or the parser may return no results. If that happens, inspect `scraper/.cache/serie.html`, adjust the parser to match the real structure, re-run tests with an updated fixture, and re-run the build.

- [ ] **Step 3: Commit the generated data**

```bash
git add api/v1/
git commit -m "data: initial scrape of Plats Bruts"
```

---

## Task 12: Documentation page

**Files:**
- Create: `docs/index.html`

- [ ] **Step 1: Create `docs/index.html`**

```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <title>Plats Bruts API</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #222; }
    code, pre { background: #f4f4f4; padding: 0.1rem 0.3rem; border-radius: 3px; font-family: "SF Mono", Menlo, monospace; }
    pre { padding: 1rem; overflow-x: auto; }
    h1, h2 { border-bottom: 1px solid #eee; padding-bottom: 0.3rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }
    th { background: #fafafa; }
    .disclaimer { font-size: 0.85rem; color: #666; border-left: 3px solid #ddd; padding: 0.5rem 1rem; }
  </style>
</head>
<body>
  <h1>Plats Bruts API</h1>
  <p>API REST estàtica amb dades sobre la sitcom catalana <strong>Plats Bruts</strong> (TV3, 1999-2002). Sense autenticació, sense límits.</p>

  <p class="disclaimer">
    Projecte de fans, sense afiliació amb TV3 ni la productora. Dades extretes de Viquipèdia
    (<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA</a>).
  </p>

  <h2>URL base</h2>
  <pre><code>https://&lt;usuari&gt;.github.io/plats-bruts-api/api/v1/</code></pre>

  <h2>Endpoints</h2>
  <table>
    <tr><th>Recurs</th><th>Índex</th><th>Detall</th></tr>
    <tr><td>Personatges</td><td><code>/personatges/index.json</code></td><td><code>/personatges/{slug}.json</code></td></tr>
    <tr><td>Temporades</td><td><code>/temporades/index.json</code></td><td><code>/temporades/{n}.json</code></td></tr>
    <tr><td>Episodis</td><td><code>/episodis/index.json</code></td><td><code>/episodis/{T}x{NN}.json</code></td></tr>
    <tr><td>Cites</td><td><code>/cites/index.json</code></td><td><code>/cites/{id}.json</code></td></tr>
    <tr><td>Localitzacions</td><td><code>/localitzacions/index.json</code></td><td><code>/localitzacions/{slug}.json</code></td></tr>
  </table>

  <h2>Exemple amb fetch</h2>
  <pre><code>const res = await fetch("https://&lt;usuari&gt;.github.io/plats-bruts-api/api/v1/personatges/lofi.json");
const lofi = await res.json();
console.log(lofi.nom);</code></pre>

  <h2>Exemple amb curl</h2>
  <pre><code>curl https://&lt;usuari&gt;.github.io/plats-bruts-api/api/v1/episodis/1x01.json</code></pre>

  <h2>Codi font</h2>
  <p>Tot el codi del scraper i les dades estan a <a href="https://github.com/&lt;usuari&gt;/plats-bruts-api">GitHub</a>.</p>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add docs/index.html
git commit -m "docs: add documentation page"
```

---

## Task 13: GitHub Actions — Pages deploy

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Create `.github/workflows/deploy.yml`**

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: .
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: deploy to GitHub Pages on push to main"
```

---

## Task 14: GitHub Actions — scheduled rebuild

**Files:**
- Create: `.github/workflows/build.yml`

- [ ] **Step 1: Create `.github/workflows/build.yml`**

```yaml
name: Rebuild API data

on:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest -v
      - run: python -m scraper.build
      - name: Commit updated data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add api/v1/
          if git diff --cached --quiet; then
            echo "No data changes."
          else
            git commit -m "data: refresh from Wikipedia"
            git push
          fi
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: manual workflow to rebuild API data"
```

---

## Task 15: Final verification

- [ ] **Step 1: Run full test suite one last time**

Run: `pytest -v`
Expected: all tests pass.

- [ ] **Step 2: Verify the API tree is committed and complete**

Run: `ls api/v1/`
Expected: directories `personatges/`, `episodis/`, `temporades/`, `cites/`, `localitzacions/`, each with an `index.json` and at least one detail file.

- [ ] **Step 3: Verify CORS-friendliness (manual check after first deploy)**

After the first GitHub Pages deploy, open the docs page in a browser and run in the console:

```javascript
fetch("/api/v1/personatges/index.json").then(r => r.json()).then(console.log)
```

Expected: prints the personatges index. No CORS errors.

If accessing from a different origin, same `fetch` URL with absolute base should also succeed because GitHub Pages serves `Access-Control-Allow-Origin: *`.

- [ ] **Step 4: Final commit (if anything pending)**

```bash
git status
```

Expected: clean tree.

---

## Done

The MVP from the spec is complete:
- All five resources (personatges, episodis, temporades, cites, localitzacions) published with indexes.
- Data scraped from Catalan Wikipedia with manual overrides.
- Documentation page live.
- Reproducible build via `python -m scraper.build`.
- CI pipeline (deploy + manual rebuild).
