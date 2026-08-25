import copy
import os

import yaml

from src.core import init
from src.core.init import RUNTIME_KEYS, normalize_cfg, save_cfg


def test_example_config_parses_with_current_schema():
    with open(os.environ["CORTANA_CONFIG"], encoding="utf-8") as f:
        cfg = normalize_cfg(yaml.safe_load(f))
    assert cfg["pair"] == list(cfg["board"])
    for board in cfg["board"].values():
        assert isinstance(board["units"], list)
        assert board["units"]
        assert "unit_1" not in board and "unit_10" not in board
    # keys the bot reads unconditionally at startup
    for key in ("guild_id", "timezone", "cortana", "daily", "backup"):
        assert key in cfg


def test_normalize_cfg_upgrades_legacy_units():
    legacy = {
        "board": {
            "alice": {"unit_1": ":heart:", "unit_10": ":heartbeat:"},
            "bob": {"unit_1": ":coin:"},
        }
    }
    cfg = normalize_cfg(legacy)
    assert cfg["board"]["alice"]["units"] == [":heart:", ":heartbeat:"]
    assert cfg["board"]["bob"]["units"] == [":coin:"]
    assert cfg["pair"] == ["alice", "bob"]


def test_normalize_cfg_keeps_new_schema_untouched():
    modern = {
        "pair": ["bob", "alice"],
        "board": {"alice": {"units": [":heart:"]}},
    }
    assert normalize_cfg(copy.deepcopy(modern)) == modern


def test_save_cfg_roundtrip_preserves_runtime_keys(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yml"
    monkeypatch.setattr(init, "CONFIG_PATH", str(config_path))

    original_cfg = dict(init.cfg)
    try:
        init.cfg["channel"] = {"night": 1}
        init.cfg["member"] = {"alice": 2}

        new_cfg = {
            "guild_id": 42,
            "board": {"alice": {"unit_1": ":heart:"}},
            # runtime keys in the payload must not be persisted
            "channel": {"stale": 9},
        }
        save_cfg(new_cfg)

        on_disk = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert on_disk["board"]["alice"]["units"] == [":heart:"]
        for key in RUNTIME_KEYS:
            assert key not in on_disk

        # in-memory cfg is hot-swapped but keeps the live runtime maps
        assert init.cfg["guild_id"] == 42
        assert init.cfg["channel"] == {"night": 1}
        assert init.cfg["member"] == {"alice": 2}
    finally:
        init.cfg.clear()
        init.cfg.update(original_cfg)
