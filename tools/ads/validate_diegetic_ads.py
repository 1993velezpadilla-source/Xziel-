#!/usr/bin/env python3
"""
XZIEL diegetic advertising policy validator.

This intentionally validates XZIEL's stricter player-first policy, not merely the
minimum requirements of any advertising platform.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "ads" / "policy" / "google_play_guardrails_v1.json"

ALLOWED_TYPES = {
    "SURFACE_STATIC",
    "SURFACE_VIDEO",
    "SPATIAL_AUDIO",
    "PROP_BRANDING",
    "ENVIRONMENT_TEXT",
    "FLAG_BANNER",
}

REQUIRED_EXCLUSIONS = {
    "corpses",
    "gore",
    "navigation_critical_surfaces",
}

def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def validate_slot_file(path: Path, policy: dict) -> list[str]:
    errors: list[str] = []
    data = load(path)

    defaults = data.get("defaults", {})
    if defaults.get("gameplayRequired") is not False:
        fail(errors, f"{path}: ads must never be gameplayRequired")
    if defaults.get("networkRequired") is not False:
        fail(errors, f"{path}: ads must never be networkRequired")
    if defaults.get("fallbackRequired") is not True:
        fail(errors, f"{path}: fallbackRequired must be true")
    if defaults.get("audioGlobalBusAllowed") is not False:
        fail(errors, f"{path}: global ad audio is forbidden")

    exclusions = set(data.get("hardExclusions", []))
    missing = REQUIRED_EXCLUSIONS - exclusions
    if missing:
        fail(errors, f"{path}: missing hard exclusions: {sorted(missing)}")

    seen: set[str] = set()
    for i, slot in enumerate(data.get("slots", [])):
        prefix = f"{path}: slots[{i}]"
        sid = slot.get("id")
        if not sid:
            fail(errors, f"{prefix}: missing id")
        elif sid in seen:
            fail(errors, f"{prefix}: duplicate id {sid}")
        else:
            seen.add(sid)

        typ = slot.get("type")
        if typ not in ALLOWED_TYPES:
            fail(errors, f"{prefix}: unsupported type {typ!r}")

        if not slot.get("fallback"):
            fail(errors, f"{prefix}: every sellable slot needs lore fallback")

        placement = slot.get("placement", {})
        if placement.get("gameplayRequired") is True:
            fail(errors, f"{prefix}: placement cannot be gameplay-required")

        if slot.get("clickable") is True:
            interaction = slot.get("interaction", {})
            if not interaction.get("requiresDeliberateIntent", False):
                fail(errors, f"{prefix}: clickable slot requires deliberate intent")
            if interaction.get("singleTapDuringGameplay", False):
                fail(errors, f"{prefix}: single-tap gameplay click-out is forbidden")

        if typ == "SPATIAL_AUDIO":
            audio = slot.get("audio", {})
            if audio.get("globalBusPlayback") is not False:
                fail(errors, f"{prefix}: spatial sponsor audio must not use global bus")
            if audio.get("gameplayDuckingAllowed") is not False:
                fail(errors, f"{prefix}: sponsor may not duck gameplay")
            if audio.get("makeUpGainAgainstGameplayAllowed") is not False:
                fail(errors, f"{prefix}: sponsor make-up gain against gameplay forbidden")
            if audio.get("attentionStingerAllowed") is not False:
                fail(errors, f"{prefix}: attention stingers forbidden")
            if audio.get("headLockedPlaybackAllowed") is not False:
                fail(errors, f"{prefix}: sponsor audio must remain world-positioned")
            if audio.get("hardMaxCreativeSeconds", 999) > 15:
                fail(errors, f"{prefix}: ambient sponsor hard max is 15 seconds")
            if audio.get("minimumSecondsBetweenPaidStarts", 0) < 600:
                fail(errors, f"{prefix}: paid audio starts must be >=600s apart")
            if not audio.get("combatSuppression", False):
                fail(errors, f"{prefix}: sponsor audio needs combat suppression")
            if not audio.get("pauseOrFadeForCriticalNarrativeAudio", False):
                fail(errors, f"{prefix}: sponsor audio must yield to narrative audio")

        delivery = slot.get("deliveryPath", "DIRECT_DIEGETIC_SPONSOR")
        if delivery == "GOOGLE_PROGRAMMATIC":
            prog = slot.get("programmatic", {})
            if not prog.get("providerFormatExplicitlySupported", False):
                fail(errors, f"{prefix}: programmatic slot needs explicit provider-format support")
            if typ != "SPATIAL_AUDIO" and not prog.get("requiredAttributionPreserved", False):
                fail(errors, f"{prefix}: required programmatic attribution must be preserved")

    return errors

def main() -> int:
    if not POLICY.exists():
        print(f"ERROR: missing policy {POLICY}", file=sys.stderr)
        return 2
    policy = load(POLICY)

    slot_files = sorted((ROOT / "ads").glob("*/diegetic_slots_v*.json"))
    if not slot_files:
        print("No diegetic slot files found")
        return 0

    errors: list[str] = []
    for p in slot_files:
        errors.extend(validate_slot_file(p, policy))

    if errors:
        print("DIEGETIC_AD_POLICY_FAILED")
        for e in errors:
            print(" -", e)
        return 1

    print(f"DIEGETIC_AD_POLICY_OK files={len(slot_files)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
