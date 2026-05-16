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
