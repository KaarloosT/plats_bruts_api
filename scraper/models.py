from dataclasses import dataclass, field
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
    cites: list[str] = field(default_factory=list)

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
            "cites": list(self.cites),
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
    audiencia_mitjana: Optional[int] = None
    quota_audiencia: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "numero": self.numero,
            "any_inici": self.any_inici,
            "any_fi": self.any_fi,
            "num_episodis": self.num_episodis,
            "episodis": list(self.episodis),
            "audiencia_mitjana": self.audiencia_mitjana,
            "quota_audiencia": self.quota_audiencia,
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
