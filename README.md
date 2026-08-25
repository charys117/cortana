# Description

A chat assistant for discord.

# Configuration

Copy `config.example.yml` to `config.yml` and fill in your values, or edit it
through the built-in web UI after the bot is up. `config.yml` is gitignored and
must never be committed — secrets stay in environment variables.

# Web Config UI

The bot serves a config editor (default `http://<host>:8080`) once it is ready:

- pick server emojis visually (loaded live from the guild) for the emoji map
  and the score boards
- edit boards with a live message preview, personas, awards, bark
  notifications and archive rules
- saving writes `config.yml` atomically and hot-applies it — no restart needed
  (only `timezone` requires a restart)

# Environment Variables

- `CORTANA_TOKEN` — Discord bot token (required)
- `CORTANA_WEB_TOKEN` — access token for the web UI; strongly recommended
  whenever the port is reachable beyond localhost
- `CORTANA_WEB_HOST` / `CORTANA_WEB_PORT` — bind address, default `0.0.0.0:8080`
- `CORTANA_WEB_ENABLED` — set `0` to disable the web UI
- `CORTANA_CONFIG` — path to the config file, default `./config.yml`
- `PROXY` — optional HTTP proxy for Discord/httpx

# Development

CI (`.github/workflows/ci.yml`) gates every PR on lint, tests and a Docker
build. Run the same checks locally:

```bash
uv sync            # installs dev deps (ruff, pytest)
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Images are built and pushed to GHCR by `docker-build.yml` on pushes to
`main`/`master` and on `v*` / `release-*` tags only.
