from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.run_astral_gate import load_gate


def test_astral_gate_fixture_is_loadable():
    gate = load_gate(ROOT / "benchmarks" / "astral_gate_v1.json")
    assert gate["name"].startswith("Pichy Astral Gate")
    assert len(gate["tests"]) >= 8
    assert any(t["id"] == "repo-agent" for t in gate["tests"])
