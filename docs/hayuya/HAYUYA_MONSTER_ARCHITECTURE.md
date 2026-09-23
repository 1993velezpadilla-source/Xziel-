# HAYUYA MONSTER — Image-to-3D Architecture

**Status:** v3 multi-reference / evidence-gated pipeline  
**Branch:** `art/hayuya-monster-v1`  
**Primary contract:** give Hayuya **one or more photos** of the same asset and receive a production-oriented 3D asset package. Hayuya itself imposes no photo-count ceiling.

Hayuya is no longer defined as a thin alias for Hunyuan3D. It is an orchestration engine that can use multiple image-to-3D systems, compare their outputs, and produce a reproducible final GLB.

## Product goal

For future zombie models, creatures, props, architecture pieces, map dressing, statues, weapons, furniture, ritual objects, signs, machinery and similar assets:

1. Accept an arbitrary pool of 1→N source photos.
2. Preserve identity, silhouette and important asymmetry.
3. Synthesize missing view coverage when needed.
4. Generate several independent geometry hypotheses.
5. Automatically reject broken meshes.
6. Rank valid candidates.
7. Normalize the champion to GLB.
8. Preserve/produce UV and texture data whenever the winning backend supports it.
9. Record every backend/version/seed/score in a manifest.
10. Keep commercial-safe permissive backends as the default stack.

## Core stages

### 0. Input Lock

Inputs are immutable anchors.

- 1 photo: primary identity anchor.
- 2+ photos: every unique real source is authoritative evidence.
- No Hayuya-level maximum reference count.
- Duplicate file paths are de-duplicated so one image cannot accidentally overweight the Judge.
- Accepted source formats: PNG/JPEG/WebP.
- Source order is preserved; the first reference is the continuity/primary anchor.
- Seed is explicit and saved.

### 1. ViewForge

Hayuya plans an 8-angle canonical coverage set:

- front
- front 45 right
- right
- back 45 right
- back
- back 45 left
- left
- front 45 left

With one image, ViewForge can now execute the pinned Wonder3D RGB+normal pipeline. It stages a foreground RGBA input, collects six canonical RGB views plus six normal maps, preserves the real input as the authoritative anchor, and exposes only the five non-front synthetic RGB views as reconstruction support.

With multiple images, all originals remain authoritative. If a backend cannot efficiently consume the entire pool in one call, Hayuya creates deterministic anchor groups: the primary reference appears in every group and the remaining real sources are distributed across groups so none are dropped.

**Important:** synthetic views are evidence helpers, not permission to overwrite identity or replace a real source image.

### 2. Shape Arena

Instead of trusting one generator, Hayuya launches independent candidates.

Current executable v1 adapters:

- **TripoSG** — high-fidelity rectified-flow shape candidate.
- **TRELLIS.2** — ultra/high-resolution O-Voxel candidate with full PBR.
- **TRELLIS** — native multi-image candidate; Hayuya can create multiple bounded TRELLIS groups from an arbitrary reference pool.
- **InstantMesh** — Zero123++ six-view + LRM/FlexiCubes candidate.
- **TripoSR** — fast baseline/sanity candidate.

Additional executable support stages:

- **Wonder3D ViewForge** — one-source RGB+normal expansion; synthetic front never replaces the real anchor.
- **TripoSF / SparseFlex** — 1024³ geometry refinement challenger for Monster/Ultra.
- **Material Bridge v1** — projects source base color onto a preferred refined topology and returns that GLB to the final arena.

Pinned specialist still not wired into normal orchestration:

- PSHuman character-specialist pass.

Optional cloud adapters are allowed later, but Hayuya must remain functional without them.

### 3. Multi-anchor / Reference Pool mode

For `game`, `monster`, and `ultra` profiles with multiple real references:

- the complete reference pool is retained
- TRELLIS receives deterministic bounded groups through `run_multi_image(..., mode="multidiffusion")`
- the first/primary source is repeated in every bounded group for identity continuity
- every non-primary source appears in at least one native multi-image group
- TripoSG can generate an independent geometry hypothesis from **every** real source by default
- `--anchor-hypothesis-budget N` is available only as an explicit compute-cost control; `0` means all references
- all candidates are judged against the **entire** real reference pool, not only the photos that produced that candidate

This makes backend-specific image limits or VRAM limits an implementation detail rather than a Hayuya input limit.

### 4. Hayuya Judge

The current v1 judge scores:

- geometry capacity relative to target face budget
- disconnected component count
- degenerate triangle ratio
- finite/non-collapsed geometry
- watertightness where appropriate
- UV availability
- textured/material readiness
- bounding-box sanity

The score is reproducible and stored in `ranking.json`.

#### Judge v2 — implemented

Judge v2 now performs source-aware software silhouette validation without needing OpenGL or a neural evaluator.

For every real source photo:

1. extract/normalize a foreground mask
2. render mesh silhouettes in software
3. search camera hypotheses across azimuth, elevation and Y-up/Z-up conventions
4. locally refine the winning orientation across orthographic and perspective camera hypotheses
5. compute silhouette IoU
6. compute tolerant boundary F1
7. estimate mask confidence so weak background segmentation has less authority
8. score each real source independently
9. combine multiple source scores with robust confidence-weighted weak-tail penalties

Per-view score:

`0.72 * silhouette_IoU + 0.28 * boundary_F1`

Multiple real sources use a confidence-weighted robust aggregation. Clean alpha masks keep near-full authority; uncertain corner/luminance segmentation is pulled toward the weighted consensus before lower-tail penalties are applied.

The v2 production/silhouette core preserves approximately:

`55% source_visual + 45% production_mesh_score`

before v3 appearance/support layers are added.

This means a model cannot win merely by having more polygons, UVs or a larger texture. With many references, a candidate that matches a few views but badly misses the weakest real anchor is intentionally pushed down.

#### Judge v3 — appearance stage implemented

Judge v3 now adds learned appearance evidence on top of the dependency-light v2 guardrail.

Implemented:

1. deterministic CPU RGB z-buffer renderer — no OpenGL/headless requirement
2. candidate RGB renders use the same camera hypotheses selected by Judge v2
3. UV/base-color textures are sampled per pixel in the CPU renderer when available, with vertex-color fallback
4. original DINOv2 ViT-S/14 LVD-142M features provide permissive Apache-2.0 appearance comparison
5. real-source embeddings are cached across candidates
6. candidate mesh/color arrays are loaded once per candidate
7. detail/close-up references are searched against 8 candidate azimuths
8. each candidate detail view exposes whole-frame + 3x3 local patches
9. detail evidence refines appearance ranking without being misused as a whole-object silhouette
10. `--appearance-judge off|auto|required` controls activation; `auto` falls back cleanly to v2

When active, Judge v3 contributes 25% of the final candidate score. The remaining 75% preserves the established v2 production/silhouette ratio.

Within the appearance subscore:
- no detail refs: 100% whole-object appearance
- detail refs present: 72% whole-object appearance + 28% local-detail retrieval

The raw DINO cosine is retained in reports; Hayuya does not label it as a calibrated probability.

#### Judge v3 synthetic normal support — implemented

When a one-photo ViewForge job produces Wonder3D normal maps, Hayuya can compare the candidate's rendered vertex normals against those six synthetic maps.

Important constraints:

- Wonder3D normals are treated in its pinned **front-view OpenGL normal coordinate system**.
- Candidate normals are transformed into the matched real-anchor front frame.
- Support views use canonical offsets: front, front-right, right, back, left, front-left.
- Synthetic normal evidence contributes only **6%** of the final ranking.
- It is explicitly classified as synthetic support, never equal to a real reference.

#### Judge v3 next geometry layer

Still to add:

1. depth-order agreement
2. stronger calibrated focal/intrinsics estimation beyond the current perspective hypothesis search
3. asymmetric-detail localization
4. face/hands/accessory specialist checks for characters

MEt3R and VGGT remain research/opt-in references rather than default dependencies because their transitive/checkpoint licensing differs from the permissive Hayuya core.

### 5. Geometry Refinement + Material Forge

For Monster/Ultra, TripoSF can now act as a **geometry challenger** rather than an automatic overwrite.

Pipeline:

1. choose a strong seed candidate using real-source silhouette evidence
2. reconstruct it through TripoSF SparseFlex at the pinned 1024³ configuration
3. restore the refined mesh to the original candidate's object-space bounds
4. compare original vs refined using real-source visual evidence + mesh health + at most 5% synthetic normal support
5. require a positive promotion margin before marking the refined geometry preferred
6. if refined geometry wins, run Material Bridge v1
7. return the bridged GLB to the full final Judge; it still has to beat the original asset

Material Bridge v1 samples source surface/base-color evidence and projects it to refined vertices with a KD-tree, producing a color-preserving GLB rather than a gray OBJ.

Current material target remains:

- base color / albedo — bridge v1 implemented
- normal
- roughness
- metallic
- AO
- opacity when required

TRELLIS.2 can already supply PBR attributes directly. **Material Bridge v2** will perform UV/PBR rebaking for refined or non-PBR champions.

Never let a texture/refinement stage silently change geometry identity.

### 6. GamePrep

Every final asset should eventually produce:

- `master.glb`
- `LOD0.glb`
- `LOD1.glb`
- `LOD2.glb`
- `LOD3.glb`
- collision proxy when relevant
- manifest
- turntable preview
- QA report

Profile targets:

| Profile | Target faces | Texture | TRELLIS.2 |
|---|---:|---:|---:|
| preview | 30k | 1K | 512 |
| mobile | 35k | 2K | 512 |
| game | 80k | 2K | 1024 |
| monster | 250k | 4K | 1024 |
| ultra | 500k | 4K | 1536 |

## Reproducible backend environments

Different 3D generators have incompatible Python/CUDA stacks. Hayuya therefore supports one Python executable per backend:

```bash
HAYUYA_TRIPOSG_PYTHON=/envs/triposg/bin/python
HAYUYA_TRIPOSR_PYTHON=/envs/triposr/bin/python
HAYUYA_INSTANTMESH_PYTHON=/envs/instantmesh/bin/python
HAYUYA_TRELLIS_PYTHON=/envs/trellis/bin/python
HAYUYA_TRELLIS2_PYTHON=/envs/trellis2/bin/python
HAYUYA_WONDER3D_PYTHON=/envs/wonder3d/bin/python
HAYUYA_TRIPOSF_PYTHON=/envs/triposf/bin/python
```

Pinned source is installed under:

```
.hayuya/models/<backend>
```

Bootstrap:

```bash
python tools/hayuya3d/bootstrap.py --all
```

Verify exact commits:

```bash
python tools/hayuya3d/bootstrap.py --verify
```

## Usage

### Plan only — one photo

```bash
python tools/hayuya3d/hayuya.py \
  --input my_asset.png \
  --profile monster
```

### Plan only — many photos

```bash
python tools/hayuya3d/hayuya.py \
  --input front.png \
  --input front_45.png \
  --input right.png \
  --input back.png \
  --input detail_left.png \
  --profile monster
```

If a native multi-image backend needs bounded calls, Hayuya groups the references automatically. The total reference pool is still preserved.

### Plan from a complete reference folder

```bash
python tools/hayuya3d/hayuya.py \
  --input-dir assets/my_asset/references \
  --profile monster
```

The scan is recursive. Folder names such as `details/`, `textures/`, `materials/`, and `closeups/` are treated as detail evidence rather than whole-object silhouette references.

### Execute installed backends

```bash
python tools/hayuya3d/hayuya.py \
  --input front.png \
  --input back.png \
  --profile monster \
  --gpu-vram 24 \
  --execute
```

Outputs are written under:

```
out/hayuya3d/<job>/
  plan.json
  candidates/
  ranking.json
  manifest.json
  hayuya_final.glb
```

## Licensing policy

Default-enabled backends must be permissive:

- MIT
- Apache-2.0

Community/restricted models are explicit opt-in only.

Hunyuan3D-2.1 remains listed for research/compatibility but is **not enabled by default** because its community license carries territory, commercial-scale and use restrictions. Its outputs must not be used to improve another AI model where the license forbids that behavior.

Cloud vendors such as Tripo or Meshy are optional adapters through their official APIs and terms. Hayuya must never depend on bypassing access controls, private endpoints, leaked code, or hidden web APIs.

## Current v3 milestone state

Implemented in code/orchestration:

- real Wonder3D ViewForge execution from one source image
- source camera search with local perspective refinement
- rendered candidate-vs-source silhouette Judge
- DINOv2 RGB/identity appearance Judge
- local detail-reference retrieval
- per-pixel UV/base-color rendering
- confidence-weighted source masks
- low-weight Wonder3D normal support
- TripoSF 1024³ geometry challenger
- Material Bridge v1 base-color transfer
- evidence-gated return of refined material-bridged geometry to the final arena

Remaining major stages:

- full PBR Material Bridge v2
- semantic mesh segmentation/repair
- smart retopology/quad option
- automatic LOD + collision pack
- humanoid/zombie specialist mode
- rig/skin validation
- automated turntable comparison report

The architectural rule is simple:

> **One photo should be enough to start. Every additional useful real reference should strengthen Hayuya. Backend per-call limits must never become a global Hayuya reference limit.**
