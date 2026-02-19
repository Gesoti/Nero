# Cyprus Water Levels Dashboard

A real-time dashboard for monitoring Cyprus reservoir water levels. Displays fill percentages, storage volumes, and historical trends for all 17 major dams.

Data is sourced from the [Water Development Department of Cyprus](https://cyprus-water.appspot.com) (CC BY 2.0) and refreshed every 6 hours.

## Features

- Crisis hero banner showing current system fill percentage
- Historical trend chart (2018–present, 599+ snapshots)
- Individual dam detail pages with photos, metadata, and charts
- Color-coded severity: Critical (<20%), Warning (20–40%), Healthy (>40%)
- SQLite-backed cache — fast page loads, works offline after first seed

## Tech Stack

FastAPI · Jinja2 · SQLite · Tailwind CSS CDN · Chart.js · APScheduler · httpx

## Running Locally

**Requirements:** Python 3.13+, [uv](https://docs.astral.sh/uv/)

```bash
# Install dependencies
uv sync

# Start the server (seeds database on first run, ~7s)
uv run python main.py
```

Open [http://localhost:8000](http://localhost:8000).

On first startup the app fetches all historical data from the upstream API (~7 seconds). Subsequent restarts use the cached SQLite database and only sync today's data.

## Configuration

Override defaults via environment variables (prefix `WL_`):

| Variable | Default | Description |
|---|---|---|
| `WL_PORT` | `8000` | Server port |
| `WL_HOST` | `0.0.0.0` | Bind address |
| `WL_SYNC_INTERVAL_HOURS` | `6` | Background refresh interval |
| `WL_DB_PATH` | `data/water.db` | SQLite database path |
| `WL_DEBUG` | `false` | Enable hot-reload |

```bash
WL_PORT=9000 WL_DEBUG=true uv run python main.py
```
