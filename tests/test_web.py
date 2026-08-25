import os

import pytest
import yaml
from aiohttp.test_utils import TestClient, TestServer

from src.core import init
from src.web import server
from src.web.server import _validate, build_app


def load_example_config():
    with open(os.environ["CORTANA_CONFIG"], encoding="utf-8") as f:
        return init.normalize_cfg(yaml.safe_load(f))


def read_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestValidate:
    @pytest.fixture
    def config(self):
        return load_example_config()

    def test_example_config_is_valid(self, config):
        assert _validate(config) is None

    def test_rejects_non_dict(self):
        assert _validate(["not", "a", "dict"]) is not None

    def test_rejects_missing_required_key(self, config):
        del config["guild_id"]
        assert "guild_id" in _validate(config)

    def test_rejects_unknown_key(self, config):
        config["hacked"] = True
        assert "hacked" in _validate(config)

    def test_rejects_wrong_type(self, config):
        config["timezone"] = "-8"
        assert "timezone" in _validate(config)

    def test_rejects_board_missing_field(self, config):
        del config["board"]["alice"]["channel"]
        assert "board.alice" in _validate(config)

    def test_rejects_empty_units(self, config):
        config["board"]["alice"]["units"] = []
        assert "units" in _validate(config)

    def test_rejects_persona_missing_field(self, config):
        del config["cortana"]["cortana"]["online"]
        assert "cortana.cortana" in _validate(config)


@pytest.fixture
async def client(cfg, tmp_path, monkeypatch):
    """App client backed by a throwaway copy of the example config."""
    config_path = tmp_path / "config.yml"
    with open(os.environ["CORTANA_CONFIG"], encoding="utf-8") as f:
        config_path.write_text(f.read(), encoding="utf-8")
    # without DATABASE_URL save_cfg persists to the yaml file at init.CONFIG_PATH
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(init, "CONFIG_PATH", str(config_path))
    monkeypatch.delenv("CORTANA_WEB_TOKEN", raising=False)

    test_client = TestClient(TestServer(build_app()))
    await test_client.start_server()
    yield test_client
    await test_client.close()


class TestConfigApi:
    async def test_get_config(self, client):
        resp = await client.get("/api/config")
        assert resp.status == 200
        data = await resp.json()
        # guild_id is serialized as a string for JS clients
        assert data["config"]["guild_id"] == "123456789012345678"
        assert "board" in data["config"]

    async def test_put_config_roundtrip(self, client):
        config = load_example_config()
        config["guild_id"] = str(config["guild_id"])  # as a JS client sends it
        config["board"]["alice"]["title"] = "**UPDATED**:"

        resp = await client.put("/api/config", json=config)
        assert resp.status == 200

        on_disk = read_yaml(init.CONFIG_PATH)
        assert on_disk["guild_id"] == 123456789012345678
        assert on_disk["board"]["alice"]["title"] == "**UPDATED**:"
        # the hot-applied in-memory cfg matches
        assert init.cfg["board"]["alice"]["title"] == "**UPDATED**:"

    async def test_put_rejects_invalid_json(self, client):
        resp = await client.put("/api/config", data="{not json")
        assert resp.status == 400

    async def test_put_rejects_non_numeric_guild_id(self, client):
        config = load_example_config()
        config["guild_id"] = "not-a-number"
        resp = await client.put("/api/config", json=config)
        assert resp.status == 400

    async def test_put_rejects_invalid_config(self, client):
        config = load_example_config()
        config["unknown_key"] = 1
        resp = await client.put("/api/config", json=config)
        assert resp.status == 400
        # nothing was persisted
        assert "unknown_key" not in read_yaml(init.CONFIG_PATH)

    async def test_put_upgrades_legacy_board_schema(self, client):
        config = load_example_config()
        board = config["board"]["alice"]
        board.pop("units")
        board["unit_1"] = ":heart:"
        board["unit_10"] = ":heartbeat:"

        resp = await client.put("/api/config", json=config)
        assert resp.status == 200
        on_disk = read_yaml(init.CONFIG_PATH)
        assert on_disk["board"]["alice"]["units"] == [":heart:", ":heartbeat:"]
        assert "unit_1" not in on_disk["board"]["alice"]


class TestAuth:
    @pytest.fixture
    async def secured_client(self, client, monkeypatch):
        monkeypatch.setenv("CORTANA_WEB_TOKEN", "sekrit")
        return client

    async def test_api_requires_token(self, secured_client):
        resp = await secured_client.get("/api/config")
        assert resp.status == 401

    async def test_api_rejects_wrong_token(self, secured_client):
        resp = await secured_client.get(
            "/api/config", headers={"Authorization": "Bearer wrong"}
        )
        assert resp.status == 401

    async def test_api_accepts_valid_token(self, secured_client):
        resp = await secured_client.get(
            "/api/config", headers={"Authorization": "Bearer sekrit"}
        )
        assert resp.status == 200

    async def test_non_api_paths_are_not_gated(
        self, secured_client, tmp_path, monkeypatch
    ):
        # the built frontend may be absent in CI; serve a stub index.html
        (tmp_path / "index.html").write_text("<!doctype html>", encoding="utf-8")
        monkeypatch.setattr(server, "STATIC_DIR", str(tmp_path))
        resp = await secured_client.get("/")
        assert resp.status == 200


class TestIndex:
    async def test_503_with_hint_when_frontend_not_built(
        self, client, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(server, "STATIC_DIR", str(tmp_path / "empty"))
        resp = await client.get("/")
        assert resp.status == 503
        assert "npm" in await resp.text()


class TestGuildApi:
    async def test_503_before_bot_is_connected(self, client):
        resp = await client.get("/api/guild")
        assert resp.status == 503
