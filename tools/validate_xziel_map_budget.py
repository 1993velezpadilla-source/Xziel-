#!/usr/bin/env python3
"""Validate Xziel map assets against the versioned mobile engine budget contract."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "engine"
    / "config"
    / "xziel_engine_limits.v1.json"
)


@dataclass
class Finding:
    severity: str
    message: str


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def mib(size_bytes: int) -> float:
    return size_bytes / (1024.0 * 1024.0)


def check_limit(
    findings: list[Finding],
    label: str,
    value: int | float,
    hard: int | float | None,
    soft: int | float | None,
) -> None:
    if hard is not None and value > hard:
        findings.append(
            Finding(
                "ERROR",
                f"{label}: {value} exceeds hard limit {hard}",
            )
        )
        return

    if soft is not None and value > soft:
        findings.append(
            Finding(
                "WARN",
                f"{label}: {value} exceeds shipping soft budget {soft}",
            )
        )


def meaningful_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.split("#", 1)[0].strip()
            if line:
                yield line


def inspect_xmap(path: Path, manifest: dict) -> tuple[dict, list[Finding]]:
    findings: list[Finding] = []
    lines = list(meaningful_lines(path))

    if not lines:
        return {}, [Finding("ERROR", f"{path}: empty XMAP")]

    header = lines[0].split()
    if len(header) != 2 or header[0] != "xziel_map":
        return {}, [Finding("ERROR", f"{path}: invalid XMAP header")]

    try:
        version = int(header[1])
    except ValueError:
        return {}, [Finding("ERROR", f"{path}: invalid XMAP version")]

    counts = {
        "box": 0,
        "floor": 0,
        "door": 0,
        "window": 0,
        "interaction": 0,
        "zombie_spawn": 0,
        "light": 0,
        "player_spawn": 0,
    }

    for line in lines[1:]:
        token = line.split(None, 1)[0]
        if token in counts:
            counts[token] += 1

    hard = manifest["hard_limits"]["map_runtime"]
    soft = manifest["shipping_soft_budgets"]["map_runtime"]

    mapping = {
        "box": ("boxes", "max_boxes"),
        "floor": ("floors", "max_floors"),
        "door": ("doors", "max_doors"),
        "window": ("windows", "max_windows"),
        "interaction": (
            "generic interactions",
            "max_generic_interactions",
        ),
        "zombie_spawn": (
            "zombie spawn points",
            "max_zombie_spawns",
        ),
        "light": (
            "authored lights",
            "max_lights",
        ),
    }

    for token, (label, key) in mapping.items():
        check_limit(
            findings,
            label,
            counts[token],
            hard.get(key),
            soft.get(key),
        )

    if counts["player_spawn"] > 1 and version < 3:
        findings.append(
            Finding(
                "ERROR",
                "player spawns: XMAP v1/v2 supports at most one authored player spawn",
            )
        )

    supported = hard.get("supported_xmap_versions", [1, 2])
    if version not in supported:
        findings.append(
            Finding(
                "ERROR",
                f"XMAP version {version} is not in current shipping parser set {supported}",
            )
        )

    return {
        "version": version,
        "records": counts,
    }, findings


def inspect_xzsm(path: Path, manifest: dict) -> tuple[dict, list[Finding]]:
    findings: list[Finding] = []

    with path.open("rb") as handle:
        header = handle.read(20)

    if len(header) != 20:
        return {}, [Finding("ERROR", f"{path}: truncated XZSM header")]

    magic, version, batches, vertices, indices = struct.unpack(
        "<4sIIII", header
    )

    if magic != b"XZSM":
        return {}, [Finding("ERROR", f"{path}: invalid XZSM magic")]

    hard = manifest["hard_limits"]["static_mesh"]
    soft = manifest["shipping_soft_budgets"]["static_mesh"]

    if version not in hard["supported_xzsm_versions"]:
        findings.append(
            Finding(
                "ERROR",
                f"XZSM version {version} unsupported; expected one of "
                f"{hard['supported_xzsm_versions']}",
            )
        )

    check_limit(
        findings,
        "XZSM batches",
        batches,
        hard["max_batches"],
        soft["max_batches"],
    )
    check_limit(
        findings,
        "XZSM vertices",
        vertices,
        hard["max_vertices"],
        soft["max_vertices"],
    )
    check_limit(
        findings,
        "XZSM indices",
        indices,
        hard["max_indices"],
        soft["max_indices"],
    )

    size_bytes = path.stat().st_size
    size_mb = mib(size_bytes)
    check_limit(
        findings,
        "XZSM file MiB",
        round(size_mb, 2),
        None,
        soft["max_xzsm_file_mb"],
    )

    return {
        "version": version,
        "batches": batches,
        "vertices": vertices,
        "indices": indices,
        "file_bytes": size_bytes,
        "file_mib": round(size_mb, 2),
    }, findings


def inspect_stream_stats(path: Path, manifest: dict) -> tuple[dict, list[Finding]]:
    with path.open("r", encoding="utf-8") as handle:
        stats = json.load(handle)

    findings: list[Finding] = []
    hard = manifest["hard_limits"]["world_streaming"]
    soft = manifest["shipping_soft_budgets"]["world_streaming"]

    mapping = {
        "cells": "max_cells",
        "portals": "max_portals",
        "resource_bindings": "max_resource_bindings",
    }

    for key, limit_key in mapping.items():
        value = int(stats.get(key, 0))
        check_limit(
            findings,
            f"stream {key}",
            value,
            hard[limit_key],
            soft[limit_key],
        )

    return stats, findings


def extract_cpp_constant(path: Path, name: str) -> int:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"\b{name}\s*=\s*([0-9]+)U?\s*;",
        text,
    )
    if not match:
        raise ValueError(f"{path}: cannot find {name}")
    return int(match.group(1))


def verify_engine_source(repo_root: Path, manifest: dict) -> list[Finding]:
    findings: list[Finding] = []

    contracts = [
        (
            repo_root / "engine/include/xziel/static_mesh.hpp",
            {
                "kMaxStaticMeshBatches": (
                    "hard_limits",
                    "static_mesh",
                    "max_batches",
                ),
                "kMaxStaticMeshVertices": (
                    "hard_limits",
                    "static_mesh",
                    "max_vertices",
                ),
                "kMaxStaticMeshIndices": (
                    "hard_limits",
                    "static_mesh",
                    "max_indices",
                ),
            },
        ),
        (
            repo_root / "engine/include/xziel/world_streaming.hpp",
            {
                "kMaxStreamCells": (
                    "hard_limits",
                    "world_streaming",
                    "max_cells",
                ),
                "kMaxStreamPortals": (
                    "hard_limits",
                    "world_streaming",
                    "max_portals",
                ),
                "kMaxStreamBindings": (
                    "hard_limits",
                    "world_streaming",
                    "max_resource_bindings",
                ),
            },
        ),
        (
            repo_root / "engine/include/xziel/map_runtime.hpp",
            {
                "kMaxMapBoxes": (
                    "hard_limits",
                    "map_runtime",
                    "max_boxes",
                ),
                "kMaxMapFloors": (
                    "hard_limits",
                    "map_runtime",
                    "max_floors",
                ),
                "kMaxMapDoors": (
                    "hard_limits",
                    "map_runtime",
                    "max_doors",
                ),
                "kMaxMapWindows": (
                    "hard_limits",
                    "map_runtime",
                    "max_windows",
                ),
                "kMaxMapGenericInteractions": (
                    "hard_limits",
                    "map_runtime",
                    "max_generic_interactions",
                ),
                "kMaxMapZombieSpawns": (
                    "hard_limits",
                    "map_runtime",
                    "max_zombie_spawns",
                ),
                "kMaxMapLights": (
                    "hard_limits",
                    "map_runtime",
                    "max_lights",
                ),
            },
        ),
        (
            repo_root / "engine/include/xziel/horde_director.hpp",
            {
                "kMaxHordeZombies": (
                    "hard_limits",
                    "horde",
                    "max_active_zombies",
                ),
                "kMaxHordeNavigationObstacles": (
                    "hard_limits",
                    "horde",
                    "max_navigation_obstacles",
                ),
                "kMaxHordeNavigationFloors": (
                    "hard_limits",
                    "horde",
                    "max_navigation_floors",
                ),
                "kMaxHordeDynamicBlockers": (
                    "hard_limits",
                    "horde",
                    "max_dynamic_blockers",
                ),
                "kMaxHordeNavigationLinksPerFloor": (
                    "hard_limits",
                    "horde",
                    "max_navigation_links_per_floor",
                ),
            },
        ),
    ]

    for path, constants in contracts:
        for name, json_path in constants.items():
            try:
                actual = extract_cpp_constant(path, name)
            except (OSError, ValueError) as exc:
                findings.append(Finding("ERROR", str(exc)))
                continue

            expected = manifest
            for key in json_path:
                expected = expected[key]

            if actual != expected:
                findings.append(
                    Finding(
                        "ERROR",
                        f"contract drift: {name}={actual}, manifest={expected}",
                    )
                )

    return findings


def print_report(
    reports: dict[str, dict],
    findings: list[Finding],
) -> None:
    for name, data in reports.items():
        print(f"[{name}]")
        print(json.dumps(data, indent=2, sort_keys=True))

    if findings:
        print("[findings]")
        for finding in findings:
            print(f"{finding.severity}: {finding.message}")
    else:
        print("PASS: all requested Xziel budget checks passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--xmap", type=Path)
    parser.add_argument("--xzsm", type=Path)
    parser.add_argument("--stream-stats", type=Path)
    parser.add_argument("--verify-engine-source", action="store_true")
    parser.add_argument("--strict-soft", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    findings: list[Finding] = []
    reports: dict[str, dict] = {}

    if args.xmap:
        reports["xmap"], result = inspect_xmap(args.xmap, manifest)
        findings.extend(result)

    if args.xzsm:
        reports["xzsm"], result = inspect_xzsm(args.xzsm, manifest)
        findings.extend(result)

    if args.stream_stats:
        reports["stream"], result = inspect_stream_stats(
            args.stream_stats,
            manifest,
        )
        findings.extend(result)

    if args.verify_engine_source:
        repo_root = Path(__file__).resolve().parents[1]
        findings.extend(
            verify_engine_source(repo_root, manifest)
        )

    if not any(
        [
            args.xmap,
            args.xzsm,
            args.stream_stats,
            args.verify_engine_source,
        ]
    ):
        parser.error(
            "provide --xmap, --xzsm, --stream-stats, or --verify-engine-source"
        )

    print_report(reports, findings)

    if any(item.severity == "ERROR" for item in findings):
        return 1

    if args.strict_soft and any(
        item.severity == "WARN" for item in findings
    ):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
