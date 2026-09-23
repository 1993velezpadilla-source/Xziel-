# HAYUYA 3D MASTER PROMPT

**Hayuya 3D** now means the team's complete **image-to-3D orchestration engine**. It is not just an alias for Hunyuan3D.

Use this instruction whenever Christian, Félix, Volnox, or another teammate says things such as:

- "use Hayuya"
- "make this a 3D model"
- "make a GLB from this photo"
- "prepare it for Hayuya 3D"
- "turn this zombie/prop/building into a model"

## Normal input: 1 or 2 photos

Hayuya must be able to start from **one photo**.

A second photo is an additional authoritative anchor and must materially improve the reconstruction; never ignore it.

Do **not** demand a manual 8-view turnaround when only one or two good references exist.

## Automatic pipeline

1. Lock the supplied source photo(s).
2. Remove/normalize background and framing without changing identity.
3. Build missing view coverage automatically.
4. Preserve real source views as higher-confidence anchors than generated views.
5. Generate multiple independent 3D candidates.
6. Judge the candidates against mesh health and, as the judge evolves, source-view agreement.
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

## Two-photo rule

When two photos are supplied:

- use both as reconstruction evidence
- prefer a native multi-image backend for at least one candidate
- generate at least one independent hypothesis from the second anchor in Monster/Ultra workflows
- do not replace either real photo with an invented synthetic view

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

Interpret **"use Hayuya"** as: take the available visual evidence, expand it intelligently, run the strongest permitted 3D pipeline, judge the results, and return the best production-ready asset.
