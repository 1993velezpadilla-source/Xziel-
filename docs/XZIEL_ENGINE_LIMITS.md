# Xziel Mobile Engine Limits — Shipping Profile v1

This file is the human-readable companion to `engine/config/xziel_engine_limits.v1.json`.

## What the numbers mean

**Hard limits** are current engine capacities. A map that exceeds one is invalid for this engine build and must be split, simplified, or the engine constant must be intentionally raised with profiling and CI evidence.

**Soft budgets** are conservative shipping targets for Android/mobile. Exceeding a soft budget does not automatically mean the map is broken, but it should trigger profiling before the map is accepted.

These are **Xziel's current measured/implemented limits**, not claimed specifications for another game or engine.

## Core hard limits

| Area | Current hard limit |
| --- | ---: |
| XZSM batches | 2,048 |
| XZSM vertices | 8,000,000 |
| XZSM indices | 12,000,000 |
| Stream cells | 64 |
| Stream portals | 128 |
| Stream resource bindings | 512 |
| Collision/map boxes | 256 |
| Floors | 256 |
| Doors | 16 |
| Windows | 32 |
| Generic interactions | 16 |
| Zombie spawn points | 32 |
| Active Horde zombies | 16 |
| Navigation obstacles | 256 |
| Navigation floors | 256 |
| Dynamic blockers | 64 |
| Navigation links per floor | 96 |

The prepared online architecture is capped at **4 concurrent players per room**. It lives on the multiplayer foundation line until multiplayer is intentionally brought into the shipping game branch.

## Runtime memory / streaming policy

Textures use a device-derived residency budget of **96–384 MiB** (128 MiB on CPU Vulkan CI), based on one eighth of the largest device-local heap and clamped to that range.

Streamed geometry uses **64–160 MiB** (96 MiB on CPU Vulkan CI), based on one sixteenth of the largest device-local heap. Elevated memory pressure reduces the effective geometry budget to 75%; Critical reduces it to 50%, with a 32 MiB safety floor. A Hot/player-visible cell may temporarily exceed budget; Preload cells may not.

Geometry reload uses a bounded **4-range window** over **2 I/O workers on mobile GPU** (1 worker on CPU Vulkan/emulator). Xziel keeps **2 frames in flight** and retires streamed GPU resources only after both frame slots are safe.

The persistent geometry asset streamer is currently bounded to **48 MiB** of buffered data.

## Recommended shipping targets for a new map

Keep a normal mobile map at or below roughly:

- 1,024 static-mesh batches
- 5,000,000 vertices
- 7,500,000 indices
- 160 MiB XZSM file
- 32 streaming cells
- 64 portals
- 384 stream resource bindings
- 192 collision boxes / 192 floors
- 12 doors / 24 windows / 12 generic interactions
- 24 zombie spawn points
- 16 active zombies
- 48 dynamic blockers

A map may exceed a soft target only when profiling proves stable frame time, memory, thermal behavior, and hitch-free streaming on target Android hardware.

## Félix / map-author workflow

Run:

```bash
python tools/validate_xziel_map_budget.py \
  --xmap path/to/map.xmap \
  --xzsm path/to/map.xzsm
```

Exit code 0 means all hard limits passed. Warnings identify soft-budget pressure. Add `--strict-soft` when preparing a release candidate so warnings also fail the command.

Do not manually raise a hard limit just to make an exporter pass. Raise limits only together with the engine change, tests, runtime evidence, and an update to the JSON manifest.
