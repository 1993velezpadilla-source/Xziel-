#!/usr/bin/env python3
"""Query and synthesize design constraints from the Xziel Zombies map DNA atlas.

This tool intentionally contains no proprietary game assets, scripts, map geometry,
or decompiled data. It operates only on public-observation design metadata.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ATLAS = ROOT / "docs" / "zombies-map-dna-atlas.v1.json"

PRESETS = {
    "sanctum_classic": [
        "waw_nacht",
        "waw_verruckt",
        "waw_der_riese",
        "bo1_kino",
        "bo2_mob",
        "bo2_origins",
        "bo3_shadows",
        "wwii_final_reich",
    ],
    "compact_survival": [
        "waw_nacht",
        "bo2_nuketown",
        "wwii_groesten_haus",
    ],
    "vertical_horror": [
        "bo1_five",
        "bo2_die_rise",
        "bo2_mob",
        "cw_mauer",
        "bo6_citadelle",
        "bo7_kowakujo",
    ],
    "large_journey": [
        "bo2_tranzit",
        "bo2_origins",
        "bo6_terminus",
        "bo7_ashes",
    ],
}


def load_atlas(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(atlas: dict) -> list[str]:
    errors: list[str] = []
    if atlas.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    maps = atlas.get("maps")
    if not isinstance(maps, list) or not maps:
        errors.append("maps must be a non-empty list")
        return errors

    source_keys = set((atlas.get("sources") or {}).keys())
    ids: set[str] = set()
    required = {
        "id", "game", "title", "year", "classification", "topology",
        "progression", "horror", "pressure", "signatureSystems",
        "transferableLessons", "sourceKeys",
    }
    for index, record in enumerate(maps):
        missing = required - set(record)
        if missing:
            errors.append(f"map[{index}] missing {sorted(missing)}")
            continue
        map_id = record["id"]
        if map_id in ids:
            errors.append(f"duplicate map id: {map_id}")
        ids.add(map_id)
        if not record["topology"]:
            errors.append(f"{map_id}: topology empty")
        if not record["transferableLessons"]:
            errors.append(f"{map_id}: transferableLessons empty")
        for key in record["sourceKeys"]:
            if key not in source_keys:
                errors.append(f"{map_id}: unknown source key {key}")
    return errors


def index_maps(atlas: dict) -> dict[str, dict]:
    return {record["id"]: record for record in atlas["maps"]}


def count_values(records: Iterable[dict], field: str) -> list[dict]:
    counter: collections.Counter[str] = collections.Counter()
    for record in records:
        counter.update(record.get(field, []))
    return [
        {"value": value, "count": count}
        for value, count in counter.most_common()
    ]


def synthesize(atlas: dict, ids: list[str]) -> dict:
    by_id = index_maps(atlas)
    missing = [map_id for map_id in ids if map_id not in by_id]
    if missing:
        raise SystemExit("unknown map ids: " + ", ".join(missing))

    records = [by_id[map_id] for map_id in ids]
    systems = count_values(records, "signatureSystems")
    lessons: list[str] = []
    seen_lessons: set[str] = set()
    for record in records:
        for lesson in record["transferableLessons"]:
            if lesson not in seen_lessons:
                lessons.append(lesson)
                seen_lessons.add(lesson)

    return {
        "schemaVersion": 1,
        "sourceMaps": ids,
        "sourceTitles": [record["title"] for record in records],
        "constraints": {
            "topology": count_values(records, "topology"),
            "progression": count_values(records, "progression"),
            "pressure": count_values(records, "pressure"),
            "horror": count_values(records, "horror"),
            "signatureSystems": systems,
        },
        "transferableLessons": lessons,
        "guardrails": [
            "Create original geometry and original art.",
            "Do not reproduce exact room dimensions or exact layouts.",
            "Do not copy proprietary scripts, code, textures, audio, meshes, or quest text.",
            "Use the source maps only to derive abstract pacing, topology, readability, and encounter principles.",
        ],
    }


def summarize(atlas: dict) -> dict:
    maps = atlas["maps"]
    classes = collections.Counter(record["classification"] for record in maps)
    games = collections.Counter(record["game"] for record in maps)
    return {
        "schemaVersion": atlas["schemaVersion"],
        "mapCount": len(maps),
        "games": dict(sorted(games.items())),
        "classifications": dict(sorted(classes.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atlas", type=Path, default=DEFAULT_ATLAS)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--preset", choices=sorted(PRESETS))
    parser.add_argument("--maps", help="comma-separated map ids")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    atlas = load_atlas(args.atlas)
    errors = validate(atlas)
    if errors:
        for error in errors:
            print("ERROR", error)
        raise SystemExit(2)

    if args.validate:
        print(f"ZOMBIES_MAP_DNA_VALID maps={len(atlas['maps'])}")

    payload = None
    if args.summary:
        payload = summarize(atlas)
    elif args.list:
        payload = [
            {
                "id": record["id"],
                "game": record["game"],
                "title": record["title"],
                "classification": record["classification"],
            }
            for record in atlas["maps"]
        ]
    elif args.preset:
        payload = synthesize(atlas, PRESETS[args.preset])
        payload["preset"] = args.preset
    elif args.maps:
        ids = [item.strip() for item in args.maps.split(",") if item.strip()]
        payload = synthesize(atlas, ids)

    if payload is not None:
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        else:
            print(text, end="")


if __name__ == "__main__":
    main()
