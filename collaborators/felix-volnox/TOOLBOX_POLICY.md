# Felix / Volnox Full Toolbox Policy

## Purpose

Felix / Volnox may use the full technical toolbox and knowledge base already present in `1993velezpadilla-source/config-old-3` while keeping every collaborator-created output isolated inside:

- branch: `collab/felix-volnox-sandbox`
- root: `collaborators/felix-volnox/`

This is a capability-and-isolation contract. It does not magically grant a ChatGPT session access to software, GPUs, external accounts, API keys, or runtimes that are not actually connected to that session.

## Read/use access across the project

Felix / Volnox may inspect, learn from, invoke where permissions allow, and reuse the project's existing:

- model-generation workflows and GLB assets;
- character bases, rigs, skeletons, measurements, animation references, retargeting knowledge, and zombie animation research;
- Blender scripts, scene-building logic, map composition scripts, mesh cleanup, static-mesh export, rig inspection, preview/render tooling, and related automation;
- texture/material pipelines, UV/reference-image workflows, previews, and dimensional-authority rules;
- VFX / effects / particles / lighting / presentation logic when present;
- audio and ambient-sound references/pipelines;
- map-generation, church-map, Sanctum, runtime-export, Android/runtime validation, and optimization knowledge;
- scripts, CI/workflow definitions, build helpers, research, documentation, and asset catalogs;
- future tools added to the repository, unless the owner explicitly marks them restricted.

Known examples currently visible in the repository include:

- `tools/church_map/build_church_scene.py`
- `tools/church_map/export_vril_static_mesh.py`
- `tools/church_map/export_nzp_harness.py`
- `tools/church_map/design_zombies_gameplay.py`
- `.github/workflows/church-map-blender.yml`
- `.github/workflows/zombie-rig-inspect.yml`
- `tools/character_library/sync_character_bases.py`
- `assets/character_bases/**`
- `docs/mobile-combat-animation-plan.md`
- `docs/zombie-visual-pack-research.md`
- `docs/SANCTUM_OF_ASH_MAP_BIBLE.md`

These examples are not an exhaustive allow-list. The default is: project tools are readable/reusable unless the owner explicitly restricts them.

## Mandatory output isolation

Anything Felix or an assisting AI creates, modifies, derives, generates, renders, exports, retargets, bakes, converts, downloads for the task, or prepares for review MUST land under `collaborators/felix-volnox/`.

Recommended destinations:

- `models/` — GLB/FBX/OBJ/mesh outputs, model manifests, generated geometry
- `animations/` — animation clips, retarget outputs, baked animation data, rig reports
- `vfx/` — effects, particles, shaders/effect references, lighting/effect experiments
- `textures/` — texture sets, UV references, materials, masks, image-to-3D source images
- `blender/` — .blend sources, Blender scripts/wrappers, render manifests, review renders
- `maps/` — map-specific geometry, plans, scene packages and map exports
- `audio/` — collaborator audio work, approved imported sounds, manifests
- `assets/` — miscellaneous collaborator-owned/imported assets with provenance
- `tools/` — copied/adapted helper scripts and wrappers owned by Felix
- `experiments/` — disposable prototypes
- `research/` — source-backed notes and investigation
- `handoff/` — promotion-ready packages for owner review

## Copy/wrap, do not mutate owner tooling

When an existing owner script or pipeline needs modification:

1. Read the original outside the sandbox.
2. Copy only what is needed into `collaborators/felix-volnox/tools/` or another appropriate sandbox path.
3. Modify the sandbox copy or create a wrapper around the owner tool.
4. Keep provenance: record the source path/commit used.
5. Do not edit the original owner file unless the owner explicitly authorizes that exact edit.

Using an existing owner tool without modifying it is allowed when the active runtime/credential actually permits execution.

## Runtime truth rule

An AI assistant must distinguish:

- **Repository access** — it can read the code/docs/assets.
- **Execution access** — it can actually run Blender, Hunyuan3D/Hayuye 3D, Python, GPU inference, GitHub Actions, external APIs, renderers, or other software.
- **Write access** — it can actually commit/push to the Felix branch.

Never claim an operation ran merely because instructions exist in the repository.

If execution is unavailable, the assistant must still:
- prepare the exact inputs, commands, manifests, prompts, scripts, or job definition inside the Felix workspace when write access exists;
- clearly mark the artifact as `PREPARED_NOT_EXECUTED`;
- identify the missing runtime/tool connection.

If execution is available, outputs still go to the Felix sandbox.

## Secrets and paid services

- Never expose, copy, print, or commit secrets/API keys.
- Existing project secrets may be used only through already-authorized workflows/runtimes that keep the secret hidden.
- Paid generation must follow the relevant project approval/budget rules.
- External assets must preserve provenance/license information.

## Promotion

Nothing created here automatically enters the owner project. Promotion requires owner review/approval.