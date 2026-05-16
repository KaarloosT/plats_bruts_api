# Plats Bruts API — Design Spec

**Fecha**: 2026-05-16
**Estado**: Aprobado para implementación

## Resumen

Una API REST **estática** con datos sobre la sitcom catalana **Plats Bruts** (TV3, 1999-2002), alojada en GitHub Pages. Inspirada en PokéAPI: cada recurso vive en su propio JSON con una URL predecible. Sin servidor, sin base de datos, sin auth, sin rate limits propios.

Pensada como servicio público para fans de la serie.

## Objetivos

- Exponer datos estructurados de personajes, episodios, temporadas, citas y localizaciones.
- Datos en **catalán únicamente** (idioma original).
- Consumible desde cualquier cliente (web, móvil, scripts) vía `fetch`/`curl`, sin auth.
- Pipeline reproducible: cualquiera puede regenerar los JSON desde la fuente.

## No-objetivos (alcance excluido del MVP)

- Búsqueda full-text en el servidor.
- Filtros dinámicos vía query params (la API es estática).
- Hospedaje propio de imágenes.
- Re-scraping automático programado.
- Endpoint de "personajes que aparecen en una localización" (derivable en cliente).
- Traducciones a otros idiomas.

## Arquitectura

```
Wikipedia (ca) ──► scraper (Python) ──► JSON files ──► GitHub Pages ──► clientes
                         │
                         └── overrides manuales (data/overrides.json)
```

- **Scraper**: Python + `requests` + `beautifulsoup4`. Se ejecuta offline (local o GitHub Actions). Lee páginas de Wikipedia en catalán, normaliza los datos, fusiona con `data/overrides.json` (correcciones y datos curados manualmente) y emite los JSON en `api/v1/`.
- **API**: directorio `api/v1/` con JSON estáticos. GitHub Pages los sirve con CORS abierto por defecto (`Access-Control-Allow-Origin: *`).
- **Documentación**: `docs/index.html` (página estática) + `README.md`.

## Endpoints

URL base provisional: `https://<usuario>.github.io/plats-bruts-api/api/v1/`

| Recurso | Índice (resumen) | Detalle (ficha) |
|---|---|---|
| Personatges | `/personatges/index.json` | `/personatges/{slug}.json` |
| Temporades | `/temporades/index.json` | `/temporades/{n}.json` |
| Episodis | `/episodis/index.json` | `/episodis/{T}x{NN}.json` |
| Cites | `/cites/index.json` | `/cites/{id}.json` |
| Localitzacions | `/localitzacions/index.json` | `/localitzacions/{slug}.json` |

**Versionado**: prefijo `/api/v1/`. Cambios incompatibles van en `/api/v2/`; `v1` queda inmutable.

**Convención de slugs**: ASCII en minúscula, sin acentos ni signos especiales (`emili` no `Em·li`, `mortimers` no `Mortimer's`). El nombre original se preserva en el campo `nom`.

## Esquema de datos

### Personatge — `/personatges/{slug}.json`
```json
{
  "slug": "lofi",
  "nom": "Lofi",
  "nom_complet": "Lluís Fernández",
  "descripcio": "Estudiant de filosofia que comparteix pis amb Em·li...",
  "actor": { "slug": "joel-joan", "nom": "Joel Joan" },
  "temporades": [1, 2, 3],
  "primera_aparicio": "1x01",
  "imatge": "https://upload.wikimedia.org/.../lofi.jpg",
  "font_wikipedia": "https://ca.wikipedia.org/wiki/Plats_bruts"
}
```

### Episodi — `/episodis/{T}x{NN}.json`
```json
{
  "id": "1x01",
  "temporada": 1,
  "numero": 1,
  "titol": "Pilot",
  "sinopsi": "Lofi i Em·li busquen un nou company de pis...",
  "data_emissio": "1999-04-12",
  "duracio_min": 30,
  "personatges": ["lofi", "emili", "ramon"],
  "localitzacions": ["pis", "mortimers"],
  "cites": ["c001", "c002"],
  "font_wikipedia": "https://ca.wikipedia.org/wiki/..."
}
```

### Temporada — `/temporades/{n}.json`
```json
{
  "numero": 1,
  "any_inici": 1999,
  "any_fi": 1999,
  "num_episodis": 13,
  "episodis": ["1x01", "1x02", "..."]
}
```

### Cita — `/cites/{id}.json`
```json
{
  "id": "c001",
  "text": "Que potes!",
  "personatge": "lofi",
  "episodi": "1x01"
}
```

### Localització — `/localitzacions/{slug}.json`
```json
{
  "slug": "mortimers",
  "nom": "Mortimer's",
  "descripcio": "El bar on els protagonistes passen les nits...",
  "episodis": ["1x01", "1x02"],
  "imatge": null
}
```

### Índices — `/{recurs}/index.json`
Lista compacta para iterar sin descargar todas las fichas:
```json
{
  "count": 12,
  "results": [
    { "slug": "lofi", "nom": "Lofi", "url": "/api/v1/personatges/lofi.json" },
    { "slug": "emili", "nom": "Em·li", "url": "/api/v1/personatges/emili.json" }
  ]
}
```

## Estructura del repositorio

```
plats-bruts-api/
├── api/v1/                    ← PUBLICADO por GitHub Pages
│   ├── personatges/
│   │   ├── index.json
│   │   └── {slug}.json
│   ├── episodis/
│   ├── temporades/
│   ├── cites/
│   └── localitzacions/
├── scraper/                   ← Código del scraper
│   ├── sources/
│   │   └── wikipedia_ca.py
│   ├── models.py              ← Dataclasses de los recursos
│   ├── build.py               ← Orquesta: scrape → merge overrides → emit JSON
│   └── tests/
├── data/
│   └── overrides.json         ← Correcciones y datos curados manualmente
├── docs/                      ← Documentación HTML estática (también GH Pages)
│   └── index.html
├── .github/workflows/
│   ├── build.yml              ← Ejecuta el scraper en push o manual
│   └── deploy.yml             ← Despliega a GitHub Pages
├── pyproject.toml
└── README.md
```

## Pipeline de construcción

1. **Scrape**: `scraper/sources/wikipedia_ca.py` baja las páginas relevantes de la Wikipedia en catalán (página principal de la serie, lista de episodios, fichas de personajes si existen).
2. **Parse**: BeautifulSoup extrae tablas y secciones a las dataclasses de `scraper/models.py`.
3. **Merge**: `scraper/build.py` aplica los overrides de `data/overrides.json` encima de los datos scrapeados (para correcciones, citas añadidas a mano, descripciones mejoradas).
4. **Emit**: serializa cada entidad a su JSON en `api/v1/{recurs}/{slug}.json` y regenera todos los `index.json`.
5. **Commit**: los JSON resultantes se versionan en git. Cualquier cambio de datos genera un diff revisable.

Comando local: `python -m scraper.build`.

## Scraping responsable

- `User-Agent` identificable que incluya el nombre del repo y un email de contacto.
- Throttling: mínimo 1 segundo entre requests al mismo host.
- Respeto a `robots.txt` de `ca.wikipedia.org`.
- Cache local de las páginas descargadas durante el desarrollo para no martillear Wikipedia en cada iteración.

## Despliegue

- Repositorio público en GitHub.
- GitHub Pages habilitado sirviendo desde la rama `main` (raíz).
- `.github/workflows/deploy.yml` ejecuta el deploy estándar de GitHub Pages cuando se hace push a `main`.
- `.github/workflows/build.yml` (manual o programado) ejecuta el scraper y commitea los JSON actualizados, lo que dispara el deploy.
- CORS: GitHub Pages devuelve `Access-Control-Allow-Origin: *` por defecto. Sin configuración adicional.

## Documentación

- `docs/index.html`: página estática con descripción del proyecto, listado de endpoints, ejemplos en `curl` y `fetch`, y la atribución requerida por la licencia.
- `README.md`: réplica condensada para visitantes de GitHub, instrucciones para regenerar los datos localmente.

## Consideraciones legales

- **Wikipedia** (CC BY-SA): atribución visible en `README.md` y `docs/index.html`; cada ficha de la API incluye `font_wikipedia` apuntando a la página original.
- **Imágenes**: solo URLs a Wikimedia Commons; no se rehospeda ningún binario.
- **TV3 / productora**: el README incluye un disclaimer indicando que el proyecto es un fan project no afiliado.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Wikipedia en catalán tiene poca información estructurada sobre la serie | Los huecos se rellenan vía `data/overrides.json` (curado manual incremental) |
| El HTML de Wikipedia cambia y rompe el parser | Tests en `scraper/tests/` con fixtures HTML; CI falla antes del deploy |
| Diferencias entre cómo se llama un personaje en distintas páginas | Tabla de aliases en `data/overrides.json` que normaliza nombres a un slug canónico |
| Citas son escasas en Wikipedia | Aceptado: el MVP arranca con pocas citas; se completarán manualmente con el tiempo |

## Criterios de éxito del MVP

- Los cinco recursos (personatges, episodis, temporades, cites, localitzacions) están publicados con sus índices.
- La API responde en `https://<usuario>.github.io/plats-bruts-api/api/v1/...` con JSON válido.
- `docs/index.html` documenta todos los endpoints con ejemplos funcionales.
- `python -m scraper.build` regenera todos los JSON desde cero sin intervención manual.
- Tests del scraper pasan en CI.
