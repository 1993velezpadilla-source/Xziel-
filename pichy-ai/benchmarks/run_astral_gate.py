from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from agent.pichy_agent import PichyAgent, load_config


def load_gate(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_gate(config_path: Path, gate_path: Path, only: set[str] | None = None) -> dict[str, Any]:
    config = load_config(str(config_path))
    gate = load_gate(gate_path)
    results: list[dict[str, Any]] = []

    for case in gate.get("tests", []):
        case_id = case["id"]
        if only and case_id not in only:
            continue
        agent = PichyAgent(config, route=case["route"])
        started = time.time()
        try:
            answer = agent.run(case["prompt"], forced_route=case["route"])
            result = {
                "id": case_id,
                "route": case["route"],
                "ok": True,
                "elapsed_seconds": round(time.time() - started, 3),
                "answer": answer,
            }
        except Exception as exc:
            result = {
                "id": case_id,
                "route": case["route"],
                "ok": False,
                "elapsed_seconds": round(time.time() - started, 3),
                "error": f"{type(exc).__name__}: {exc}",
            }
        results.append(result)

    passed = sum(1 for r in results if r["ok"])
    return {
        "gate": gate.get("name", gate_path.name),
        "executed": len(results),
        "transport_passed": passed,
        "transport_failed": len(results) - passed,
        "hard_fail_contract": gate.get("hard_fail", []),
        "results": results,
        "note": "Transport pass means the case executed and returned an answer. Human/critic grading is still required for answer quality.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the Pichy Astral Gate against configured model routes.")
    ap.add_argument("--config", default="config/pichy.local.json")
    ap.add_argument("--gate", default="benchmarks/astral_gate_v1.json")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    report = run_gate(
        Path(args.config).resolve(),
        Path(args.gate).resolve(),
        set(args.only) if args.only else None,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    print(encoded)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(encoded + "\n", encoding="utf-8")
    return 0 if report["transport_failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
