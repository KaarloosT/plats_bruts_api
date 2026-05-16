import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from scraper.models import Actor, Cita, Localitzacio, Personatge


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
            if isinstance(valid_fields.get("actor"), dict):
                valid_fields["actor"] = Actor(**valid_fields["actor"])
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
