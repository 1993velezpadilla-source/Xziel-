# Character / Ragdoll Base Library

This folder is the dimensional source of truth for reusable humanoid and ragdoll bodies used by Xziel.

## Production rule

When a new creature, zombie, monster, boss or human character is designed:

1. Show the user the stored screenshots from `docs/CHARACTER_BASE_LIBRARY.generated.md`.
2. The user selects one exact base model ID.
3. Load that model's `measurements.json`, not a remembered or approximate body proportion.
4. Generate a normal concept preview for approval.
5. Generate the production reference images/textures against the selected model's exact normalized proportions.
6. Store those production images with the creature so the 3D reconstruction step receives images already fitted to the chosen body proportions.
7. Do not silently switch body bases after approval. A base change requires a new preview/approval pass.

The normal concept preview is for human review. The production reference images are for model reconstruction and must preserve the selected GLB's proportions.

## Files produced per base

Every base model directory contains:

- `model.glb` — exact source 3D body.
- `preview.png` — screenshot/preview of that model.
- `measurements.json` — exact model bounds, per-mesh bounds, rig hierarchy, joint positions, segment lengths, animation metadata and normalized proportions.
- `measurement_front.svg` — front-view dimension template generated from the model.
- `measurement_side.svg` — side-view dimension template generated from the model.
- `LICENSE.txt` — source license.
- `SOURCE.txt` — provenance URLs plus SHA-256 hashes.

`assets/character_bases/catalog.json` is the machine-readable index.

## Scale policy

Native GLB coordinates are always preserved and recorded. A default 1.75 m world-height normalization is also generated so proportions can be reasoned about in metres, but that convenience scale does **not** overwrite the source geometry.

If a future creature is intentionally 2.4 m, 8 ft, etc., scale the chosen model uniformly to that requested height unless the design explicitly calls for anatomical deformation. Limb/head/torso ratios still come from the selected base.

## Licensing policy

The first production batch is CC0-only so the assets can be modified and redistributed with the game without attribution requirements. The source/provenance files are kept anyway.

The sync job downloads and measures the exact binaries. If a source disappears or its hash changes, the checked-in copy remains the authority until intentionally refreshed.
