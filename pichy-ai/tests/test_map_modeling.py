from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.pichy_agent import MAP_MODELING_PROMPT, PichyAgent


def make_agent():
    return PichyAgent({
        "workspace": ".",
        "_config_dir": str(ROOT),
        "routes": {"map_modeling": "general"},
        "models": {
            "general": {
                "base_url": "https://example.invalid/v1",
                "model": "test-model",
                "api_key_env": "PICHY_TEST_KEY",
            }
        },
    })


def test_map_modeling_route_is_detected():
    agent = make_agent()
    assert agent.classify_route("Design a game map blockout with rooms and shortcuts") == "map_modeling"
    assert agent.classify_route("Create a level design room graph") == "map_modeling"


def test_map_modeling_route_uses_configured_reasoning_alias():
    agent = make_agent()
    profile = agent.profile("map_modeling")
    assert profile.model == "test-model"


def test_map_modeling_prompt_requires_production_constraints():
    lowered = MAP_MODELING_PROMPT.lower()
    for term in ("collision", "navmesh", "streaming", "lod", "asset manifest", "stable ids"):
        assert term in lowered


def test_map_schema_has_engine_facing_sections():
    schema = json.loads((ROOT / "map_modeling" / "map_spec.schema.json").read_text())
    required = set(schema["required"])
    assert {"zones", "connections", "lighting", "streaming", "asset_manifest", "validation"} <= required
