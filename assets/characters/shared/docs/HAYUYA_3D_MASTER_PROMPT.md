# HAYUYA 3D MASTER PROMPT

**Hayuya 3D** now means the team's complete **image-to-3D orchestration engine**. It is not just an alias for Hunyuan3D.

Use this instruction whenever Christian, Félix, Volnox, or another teammate says things such as:

- "use Hayuya"
- "make this a 3D model"
- "make a GLB from this photo"
- "prepare it for Hayuya 3D"
- "turn this zombie/prop/building into a model"

## Normal input: 1 or more photos

Hayuya must be able to start from **one photo**, but there is no Hayuya-level upper limit on useful real references.

Every additional photo of the same asset is authoritative evidence and must materially improve reconstruction, material/detail recovery, or validation; never silently ignore extra references.

Whole-object views and detail close-ups have different jobs. Hayuya should keep them in the same master reference pool while routing full-object views to geometry/Judge and detail/close-up images to material/local-detail stages.

Do **not** demand a manual 8-view turnaround. If 1, 2, 5, 9, 20, or more useful real references exist, ingest the complete reference pool.

## Automatic pipeline

1. Lock the supplied source photo(s).
2. Remove/normalize background and framing without changing identity.
3. Build missing view coverage automatically.
4. Preserve real source views as higher-confidence anchors than generated views.
5. Generate multiple independent 3D candidates.
6. Judge candidates against mesh health, silhouette/source-view agreement, and — when Judge v3 is available — DINOv2 RGB appearance plus local-detail references.
7. Select the strongest valid candidate.
8. Build/retain UV and PBR material data.
9. Produce game-ready topology/LODs as requested.
10. Export a final GLB plus plan, ranking and manifest.

## Canonical ViewForge coverage

When extra views are useful, Hayuya targets:

1. Front
2. Front 45 Right
3. Right Side
4. Back 45 Right
5. Back
6. Back 45 Left
7. Left Side
8. Front 45 Left

These views may come from:

- real user references
- open-source sparse-view generation
- multiview RGB generation
- multiview normal/depth generation

Generated views are support evidence. They must not silently rewrite the identity of a real source photo.

## Identity lock

Across every candidate and synthesized view preserve:

- same identity / face
- same hair and silhouette
- same clothing
- same accessories
- same proportions
- same asymmetry
- same damage / tears / wear logic
- same distinctive geometry

Never use blind mirroring when it corrupts asymmetric details.

## Multi-reference rule

When multiple photos are supplied:

- preserve **every unique real photo** in the reference pool
- accept complete folders recursively, not only individually enumerated files
- recognize explicit `details/`, `textures/`, `materials/`, `closeups/` folders as local-detail evidence
- keep detail refs out of whole-object silhouette scoring
- when Judge v3/DINOv2 is active, search those detail refs against local patches from multiple candidate angles so face/clothing/symbol/wound/material evidence affects ranking
- use all real photos as Judge evidence
- prefer native multi-image reconstruction for at least one candidate family
- when a backend has a per-call image/VRAM limit, split references into deterministic overlapping anchor groups rather than discarding extras
- keep the primary source in every bounded group for identity continuity
- in Monster/Ultra workflows, allow independent single-image geometry hypotheses from every real source unless an explicit compute budget is requested
- never replace a real photo with an invented synthetic view
- synthetic views fill missing coverage only

## Hayuya Monster backends

Default core is permissive open-source and version pinned.

Current families include:

- TripoSG
- TRELLIS.2
- TRELLIS multi-image
- InstantMesh / Zero123++
- TripoSR
- Wonder3D support
- TripoSF refinement roadmap
- PSHuman character-specialist roadmap

Hunyuan3D is an optional backend, not the definition of Hayuya.

Cloud services such as Tripo or Meshy may be optional official-API comparison backends, never mandatory dependencies.

## Quality rule

Do not choose a model because it is the newest or has the highest polygon count.

Choose the model that best preserves the supplied reference while remaining healthy and production-usable.

## Output contract

A completed Hayuya job should converge on:

- `hayuya_final.glb`
- `plan.json`
- `ranking.json`
- `manifest.json`
- candidate outputs for audit
- eventually LODs, collision and turntable previews

## Manual 8-view art workflow

The previous 8-view preview + individual-image process is still valid when the team intentionally wants art-directed references.

It is now an **optional high-control input workflow**, not a prerequisite for Hayuya.

For the full engine architecture see:

- `docs/hayuya/HAYUYA_MONSTER_ARCHITECTURE.md`
- `docs/hayuya/IMAGE_TO_3D_RESEARCH_2026.md`

Interpret **"use Hayuya"** as: ingest the complete real reference pool, expand only missing visual coverage, run the strongest permitted 3D pipeline, judge every candidate against all available real evidence, and return the best production-ready asset.
