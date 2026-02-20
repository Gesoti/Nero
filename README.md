# Cyprus Water Levels Dashboard

Real-time dashboard for monitoring Cyprus reservoir water levels. Displays fill percentages, storage volumes, and historical trends for all 17 major dams.

Data sourced from the [Water Development Department of Cyprus](https://cyprus-water.appspot.com) (CC BY 2.0), refreshed every 6 hours.

## Features

- Crisis hero banner with current system fill percentage
- Historical trend chart (2018–present, 599+ snapshots) with 1Y/3Y/All range filters
- Individual dam detail pages with photos, metadata, and charts
- Colour-coded severity: Critical (<20%), Warning (20–40%), Healthy (>40%)
- GDPR cookie consent banner with conditional AdSense loading
- Privacy Policy page
- HTTP security headers (CSP, X-Frame-Options, Referrer-Policy)
- SQLite-backed cache — fast page loads, works offline after first seed

## Tech Stack

FastAPI · Jinja2 · SQLite (WAL) · Tailwind CSS (built via standalone CLI) · Chart.js · APScheduler · httpx

## Running Locally

**Requirements:** Python 3.13+, [uv](https://docs.astral.sh/uv/)

```bash
uv sync                          # install dependencies
uv run python main.py            # start server (seeds DB on first run, ~7s)
WL_DEBUG=true uv run python main.py  # start with hot-reload
```

Open [http://localhost:8000](http://localhost:8000).

## Testing

```bash
uv sync --extra dev              # install test dependencies
uv run pytest tests/ -v          # run all tests (40 tests, <0.2s)
```

## Rebuilding CSS

After adding new Tailwind classes to templates, rebuild the purged CSS:

```bash
./tailwindcss -c tailwind.config.js -i app/static/css/input.css \
  -o app/static/css/tailwind.min.css --minify
```

(Download the CLI binary once: `curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64 && chmod +x tailwindcss`)

## Configuration

Override defaults via environment variables (prefix `WL_`):

| Variable | Default | Description |
|---|---|---|
| `WL_PORT` | `8000` | Server port |
| `WL_HOST` | `0.0.0.0` | Bind address |
| `WL_SYNC_INTERVAL_HOURS` | `6` | Background refresh interval |
| `WL_DB_PATH` | `data/water.db` | SQLite database path |
| `WL_DEBUG` | `false` | Enable hot-reload |

## Deployment

See [`deploy/DEPLOY.md`](deploy/DEPLOY.md) for the full VPS deployment checklist (systemd + Nginx + Let's Encrypt).

## License

Data: [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) (Water Development Department, Cyprus)
