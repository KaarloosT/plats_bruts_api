from scraper.slugify import slugify


def test_lowercase():
    assert slugify("Lofi") == "lofi"


def test_removes_accents():
    assert slugify("Emíli") == "emili"


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
