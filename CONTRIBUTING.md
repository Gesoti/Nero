# Contributing to Nero

Thank you for your interest in contributing. This guide covers the process for reporting bugs, proposing features, and submitting code.

## Reporting Bugs

Open a [GitHub issue](https://github.com/Gesoti/Nero/issues) with:
- Steps to reproduce
- Expected vs actual behaviour
- Country/page affected (if applicable)
- Browser and OS (for frontend issues)

## Proposing Features

Open a GitHub issue with the "enhancement" label. Describe the use case and why it would benefit the project.

## Development Setup

**Requirements:** Python 3.13+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/Gesoti/Nero.git
cd Nero
uv sync --extra dev
uv run python main.py        # starts server, seeds DB on first run
uv run pytest tests/ -v      # run tests (850+, <10s)
```

## Pull Request Process

1. Fork the repository and create a feature branch
2. Write tests for your changes
3. Ensure all tests pass: `uv run pytest tests/ -v`
4. Rebuild CSS if you changed templates: `./tailwindcss -c tailwind.config.js -i app/static/css/input.css -o app/static/css/tailwind.min.css --minify`
5. Submit a pull request with a clear description of the change

## Code Style

- Python with type hints throughout. No `Any` types.
- Pydantic v2 for validation and settings.
- Raw SQL with parameterised queries (no ORM).
- Tests with pytest + pytest-asyncio. Use `httpx.AsyncClient` with `ASGITransport`.
- Every `<script>` tag in templates must include `nonce="{{ request.state.csp_nonce }}"`.

## Adding a New Country

1. Create `app/providers/{cc}.py` implementing the `DataProvider` protocol from `app/providers/base.py`
2. Add the country to all 4 dicts in `app/country_config.py`
3. Register the provider in `app/main.py` `_build_provider_registry()`
4. Create `app/{cc}_dam_descriptions.py` with prose descriptions for each reservoir
5. Create `app/templates/{cc}/layout.html` extending `base.html`
6. Add description imports and routing in `app/routes/pages.py`
7. Add dam URLs to the sitemap handler and map zoom in `map_zoom` dict
8. Update `WL_ENABLED_COUNTRIES` in `app/config.py` default and `Dockerfile` ENV
9. Add tests

## Translation Contributions

We welcome translations. See the README for the `pybabel` workflow. Add new locales to `SUPPORTED_LOCALES` and `LANGUAGE_LABELS` in `app/i18n.py`.
