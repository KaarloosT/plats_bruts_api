from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def plats_bruts_html() -> str:
    return (FIXTURES / "wiki_plats_bruts.html").read_text(encoding="utf-8")


@pytest.fixture
def llista_episodis_html() -> str:
    return (FIXTURES / "wiki_llista_episodis.html").read_text(encoding="utf-8")


@pytest.fixture
def wq_season1_html() -> str:
    return (FIXTURES / "wq_season1.html").read_text(encoding="utf-8")
