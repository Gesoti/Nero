# Nero — Water Reservoir Monitoring Dashboard

Open-source, multi-country water reservoir dashboard tracking storage levels across 13 European countries. Built with FastAPI, Jinja2, and SQLite. Data sourced from official government APIs and open data portals.

Live instance: [nero.cy](https://nero.cy)

## Supported Countries

| Country | Data Source | Reservoirs |
|---------|-----------|------------|
| Cyprus | Water Development Department REST API | 17 |
| Greece | EYDAP OpenData API (Athens) | 4 |
| Spain | embalses.net (HTML scraping) | 20 |
| Portugal | infoagua.apambiente.pt (embedded JSON) | 20 |
| Czech Republic | 5 Povodi basin authority portals | 15 |
| Austria | Stub (ENTSO-E pending) | 15 |
| Italy | OpenData Sicilia GitHub CSV | 13 |
| Finland | SYKE OData API | 15 |
| Norway | NVE Magasinstatistikk JSON API | 5 zones |
| Switzerland | BFE/SFOE CSV | 4 regions |
| Bulgaria | Stub (MOEW .doc pending) | 20 |
| Germany | Stub (Ruhr/Saxony HTML pending) | 15 |
| Poland | Stub (IMGW PDF pending) | 15 |

## Features

- Per-dam detail pages with historical charts and year-on-year comparison
- Severity indicators (critical < 20%, warning 20-40%, healthy > 40%)
- Interactive map with Leaflet.js
- Multi-language support (12 locales)
- Blog with water-related articles
- SEO-optimized with JSON-LD structured data
- Auto-syncing from upstream sources via APScheduler
- No user tracking, no cookies (except optional language preference)
- HTTP security headers (nonce-based CSP, X-Frame-Options, Referrer-Policy)

## Quick Start

**Requirements:** Python 3.13+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/Gesoti/Nero.git
cd Nero
uv sync
uv run python main.py    # seeds DB on first run (~7-10s)
```

Visit [http://localhost:8000](http://localhost:8000). Use `WL_DEBUG=true` for hot-reload.

## Configuration

Override defaults via environment variables (prefix `WL_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `WL_PORT` | `8000` | Server port |
| `WL_HOST` | `0.0.0.0` | Bind address |
| `WL_DEBUG` | `false` | Enable hot-reload |
| `WL_DB_PATH` | `data/{country}/water.db` | SQLite database path |
| `WL_BASE_URL` | `https://nero.cy` | Public base URL |
| `WL_SYNC_INTERVAL_HOURS` | `6` | Background refresh interval |
| `WL_ENABLED_COUNTRIES` | `cy,gr,...,pl` | Comma-separated country codes |
| `WL_ADSENSE_PUB_ID` | *(empty)* | Google AdSense publisher ID (optional) |

See [`deploy/env.example`](deploy/env.example) for a complete template.

## Testing

```bash
uv sync --extra dev
uv run pytest tests/ -v    # 850+ tests, <10s
```

## Architecture

```
Upstream APIs (13 countries)
  ↓  httpx (app/providers/*.py)
  ↓  sync.py (initial_seed / incremental_sync, tenacity retries)
SQLite (data/{cc}/water.db per country, WAL mode)
  ↓  db.py (typed dataclass returns)
  ↓  routes/pages.py (severity labelling)
Jinja2 templates → HTML response
```

Each country has its own provider in `app/providers/`, its own SQLite database, and its own template layout. Cyprus is the default (no URL prefix); others use path prefixes (`/gr/`, `/es/`, etc.).

## Translations

12 locales supported. To add a new language:

```bash
uv run pybabel extract -F babel.cfg -o app/translations/messages.pot .
uv run pybabel init -i app/translations/messages.pot -d app/translations -l <locale>
# Translate app/translations/<locale>/LC_MESSAGES/messages.po
uv run pybabel compile -d app/translations
```

Then add the locale to `SUPPORTED_LOCALES` and `LANGUAGE_LABELS` in `app/i18n.py`.

## Adding a New Country

1. Create `app/providers/{cc}.py` implementing the `DataProvider` protocol
2. Add entries to `app/country_config.py` (all 4 dicts)
3. Register the provider in `app/main.py` `_build_provider_registry()`
4. Create `app/{cc}_dam_descriptions.py` and `app/templates/{cc}/layout.html`
5. Add routes, sitemap entries, and tests

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Rebuilding CSS

After adding new Tailwind classes to templates:

```bash
./tailwindcss -c tailwind.config.js -i app/static/css/input.css \
  -o app/static/css/tailwind.min.css --minify
```

## Deployment

See [`deploy/AWS_DEPLOY.md`](deploy/AWS_DEPLOY.md) for the full AWS deployment guide (Terraform + ECR + Docker).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

Data sourced under various open data licenses from national water agencies.
