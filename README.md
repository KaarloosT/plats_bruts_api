# Plats Bruts API

A static REST API of data about the Catalan sitcom **Plats Bruts** (TV3, 1999-2002), inspired by PokéAPI. Hosted on GitHub Pages, with no auth and no rate limits.

> Fan project, not affiliated with TV3 or the production company. Data sourced from Wikipedia (CC BY-SA).

## Endpoints

Base URL: `https://kaarloost.github.io/plats_bruts_api/api/v1/`

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
