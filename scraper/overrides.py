import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from scraper.models import Actor, Cita, Localitzacio, Personatge


@dataclass
class Overrides:
    personatge_patches: dict[str, dict] = field(default_factory=dict)
    cites: list[Cita] = field(default_factory=list)
    localitzacions: list[Localitzacio] = field(default_factory=list)
    extra_personatges: list[Personatge] = field(default_factory=list)

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
        # Append extras, deduped by slug — existing scraped entries win
        existing_slugs = {p.slug for p in out}
        out.extend(p for p in self.extra_personatges if p.slug not in existing_slugs)
        return out


def _personatge_from_dict(d: dict) -> Personatge:
    actor_data = d.get("actor")
    actor = Actor(**actor_data) if isinstance(actor_data, dict) else None
    return Personatge(
        slug=d["slug"],
        nom=d["nom"],
        nom_complet=d.get("nom_complet"),
        descripcio=d.get("descripcio"),
        actor=actor,
        temporades=d.get("temporades", []),
        primera_aparicio=d.get("primera_aparicio"),
        imatge=d.get("imatge"),
        font_wikipedia=d.get("font_wikipedia"),
    )


def load_overrides(path: Path) -> Overrides:
    path = Path(path)
    if not path.exists():
        return Overrides()
    data = json.loads(path.read_text(encoding="utf-8"))
    return Overrides(
        personatge_patches=data.get("personatges", {}),
        cites=[Cita(**c) for c in data.get("cites", [])],
        localitzacions=[Localitzacio(**l) for l in data.get("localitzacions", [])],
        extra_personatges=[
            _personatge_from_dict(e) for e in data.get("personatges_extra", [])
        ],
    )
