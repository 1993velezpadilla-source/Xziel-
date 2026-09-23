# HAYUYA MONSTER — Image-to-3D Architecture

**Status:** v1 foundation  
**Branch:** `art/hayuya-monster-v1`  
**Primary contract:** give Hayuya **one or two photos** and receive a production-oriented 3D asset package.

Hayuya is no longer defined as a thin alias for Hunyuan3D. It is an orchestration engine that can use multiple image-to-3D systems, compare their outputs, and produce a reproducible final GLB.

## Product goal

For future zombie models, creatures, props, architecture pieces, map dressing, statues, weapons, furniture, ritual objects, signs, machinery and similar assets:

1. Accept 1–2 source photos.
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
- 2 photos: both are authoritative; the second is not treated as a decorative reference.
- Accepted source formats: PNG/JPEG/WebP.
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

With one image, the missing coverage is inferred with sparse/multiview priors such as InstantMesh/Zero123++ and Wonder3D RGB+normal generation.

With two images, both originals are retained as anchors and only missing coverage should be synthesized.

**Important:** synthetic views are evidence helpers, not permission to overwrite the identity in the source image.

### 2. Shape Arena

Instead of trusting one generator, Hayuya launches independent candidates.

Current executable v1 adapters:

- **TripoSG** — high-fidelity rectified-flow shape candidate.
- **TRELLIS.2** — ultra/high-resolution O-Voxel candidate with full PBR.
- **TRELLIS** — native multi-image candidate; uses both source photos when two are supplied.
- **InstantMesh** — Zero123++ six-view + LRM/FlexiCubes candidate.
- **TripoSR** — fast baseline/sanity candidate.

Pinned but not yet executable in the v1 orchestrator:

- TripoSF / SparseFlex refinement.
- Wonder3D explicit ViewForge RGB+normal pass.
- PSHuman character-specialist pass.

Optional cloud adapters are allowed later, but Hayuya must remain functional without them.

### 3. Dual-anchor mode

For `game`, `monster`, and `ultra` profiles with two photos:

- TRELLIS receives **both** photos in `run_multi_image(..., mode="multidiffusion")`.
- TripoSG also generates an independent hypothesis from the second image using a different seed.
- The first-photo candidates still run.
- All hypotheses enter the same judge.

This prevents the second photo from being ignored.

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
4. compute silhouette IoU
5. compute tolerant boundary F1
6. score each real source independently
7. combine multiple source scores with an explicit weakest-anchor penalty

Per-view score:

`0.72 * silhouette_IoU + 0.28 * boundary_F1`

Multiple real sources:

`0.70 * mean(source_scores) + 0.30 * min(source_scores)`

Final candidate score:

`0.55 * source_visual + 0.45 * production_mesh_score`

This means a model cannot win merely by having more polygons, UVs or a larger texture. With two photos, a candidate that matches one anchor but badly misses the second is intentionally pushed down.

#### Judge v3 target

Add feature and geometry-aware validation on top of v2:

1. DINO/CLIP semantic identity agreement
2. MEt3R-style multi-view feature consistency
3. RGB rerender similarity
4. normal-map agreement
5. depth-order agreement
6. camera/focal estimation
7. asymmetric-detail preservation
8. face/hands/accessory specialist checks for characters

Judge v2 is the dependency-light guardrail; v3 will add learned perceptual evidence.

### 5. Material Forge

Target material package:

- base color / albedo
- normal
- roughness
- metallic
- AO
- opacity when required

TRELLIS.2 can already supply PBR attributes directly. Other winners can later be passed through Hayuya's view-projection/PBR stage.

Never let a texture stage silently change geometry identity.

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

### Plan only — two photos

```bash
python tools/hayuya3d/hayuya.py \
  --input front.png \
  --input back.png \
  --profile monster
```

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

## Definition of done for Hayuya Monster v2

- real ViewForge output from one source image
- source camera estimation
- rendered candidate-vs-source judge
- PBR material forge for non-PBR champions
- TripoSF high-resolution refinement pass
- semantic mesh segmentation
- smart retopology/quad option
- automatic LOD pack
- humanoid/zombie specialist mode
- rig/skin validation
- automated turntable comparison report

The architectural rule is simple:

> **One photo should be enough to start. A second photo should make Hayuya materially stronger. More references should improve fidelity, never become a mandatory chore.**
