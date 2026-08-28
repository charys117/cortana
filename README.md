# Description

A chat assistant for discord.

# Configuration

The live config is stored in PostgreSQL (`bot_config` table) and edited through
the built-in web UI. On first boot against an empty database, the bot seeds the
table from the yaml file at `CORTANA_CONFIG` — copy `config.example.yml` to
`config.yml` and fill in your values for that one boot; afterwards the file is
no longer read. `config.yml` is gitignored and must never be committed —
secrets stay in environment variables.

Database schema (config and message archive) is managed with Alembic: run
`alembic upgrade head` before starting the bot (the Docker image does this
automatically).

# Message Archive

Messages, edits, deletions, reactions and pins are archived to PostgreSQL in
real time via gateway listeners, with a daily incremental sweep as a safety
net. Attachment binaries are stored content-addressed (sha256) under
`archive.media_root` — mount persistent storage there. `/sync` runs a manual
sweep; `/sync full:true` backfills the entire history.

When `ARCHIVE_MEDIA_KEY` is set, media files are encrypted at rest with
AES-256-GCM (`*.enc`, see `src/core/mediacrypto.py`); without it they are
stored in plaintext. Generate a key with
`python -m src.core.mediacrypto --genkey`, decrypt a file with
`python -m src.core.mediacrypto <file.enc>`. **Losing the key means losing
every encrypted file** — keep a copy of it outside the cluster.

# Web Config UI

The bot serves a config editor (default `http://<host>:8080`) once it is ready:

- pick server emojis visually (loaded live from the guild) for the emoji map
  and the score boards
- edit boards with a live message preview, personas, awards, bark
  notifications and archive rules
- saving writes the config to PostgreSQL and hot-applies it — no restart
  needed; that includes `daily.time` (the daily task reschedules itself)

All timestamps are stored and scheduled in UTC (there is no timezone config);
the web UI renders times in the browser's timezone.

The frontend is a Vue 3 + Element Plus app in `web/`, served as static files
by the bot's aiohttp server. The Docker build compiles it automatically; for a
local (non-Docker) run, build it once first:

```
cd web && npm install && npm run build   # outputs to src/web/static/
```

For frontend development, `cd web && npm run dev` starts Vite on port 5173
with `/api` proxied to a locally running bot on port 8080.

# Environment Variables

- `DISCORD_BOT_TOKEN` — Discord bot token (required)
- `CORTANA_WEB_TOKEN` — access token for the web UI; strongly recommended
  whenever the port is reachable beyond localhost
- `CORTANA_WEB_HOST` / `CORTANA_WEB_PORT` — bind address, default `0.0.0.0:8080`
- `CORTANA_WEB_ENABLED` — set `0` to disable the web UI
- `CORTANA_CONFIG` — path to the first-boot seed config, default `./config.yml`
- `DATABASE_URL` — PostgreSQL connection string (required), e.g.
  `postgresql://cortana:...@postgres:5432/cortana`
- `ARCHIVE_MEDIA_KEY` — base64 32-byte key enabling media encryption at rest;
  strongly recommended
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
