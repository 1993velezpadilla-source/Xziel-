# Hayuya 3D / Hunyuan3D Workflow — Felix / Volnox

## Alias

Within this project, the human-friendly command **"Hayuya 3D"** means the project's **Hunyuan3D-style image-to-3D workflow** for producing a usable 3D asset, normally ending in GLB plus validation/previews.

An assistant should understand requests such as:

- "usa Hayuya"
- "haz este modelo con Hayuya 3D"
- "pasa esta imagen a 3D"
- "haz el GLB de esto"

as requests to use this workflow when an executable Hunyuan3D/Hayuye-compatible runtime is actually available.

## Required truth check before generation

Before saying generation started or completed, verify the current session/environment actually has an executable image-to-3D runtime.

If Hunyuan3D/Hayuye execution is unavailable:
- do NOT pretend generation is running;
- prepare all source images, prompts/config, dimensions, manifests and expected output paths;
- mark the job `PREPARED_NOT_EXECUTED`;
- state which runtime connection is missing.

## Input preparation

1. Inspect the requested subject and existing project references.
2. Prefer clean, full-subject views with readable silhouette and minimal occlusion.
3. When a known base model/rig exists, treat its recorded dimensions/measurements as authoritative for scale and proportion.
4. Preserve all approved source/reference images in:
   `collaborators/felix-volnox/textures/hayuya/<asset-name>/references/`
5. Record the intended real/model dimensions in a text/JSON manifest, not only in an image.
6. Generate or prepare additional orthographic/turnaround references when they materially improve reconstruction.

## Generation output

For each asset, use:

`collaborators/felix-volnox/models/hayuya/<asset-name>/`

Recommended package:

- `source/` — input images and prompt/config manifest
- `raw/` — untouched model output
- `processed/` — cleaned/optimized GLB
- `textures/` — generated/extracted texture maps
- `previews/` — front/back/left/right/3-4 views and wireframe if available
- `measurements.json` — dimensions and scale authority
- `PROVENANCE.md` — source/runtime/model/settings/license notes
- `STATUS.md` — generated, validated, rejected, or prepared-not-executed

## Blender finishing

When Blender execution is available, Blender may be used after image-to-3D generation for:

- scale normalization;
- mesh cleanup;
- normals;
- UV/material repair;
- texture hookup;
- decimation/LOD preparation;
- rigging/armature work;
- animation retargeting/baking;
- pivot/origin setup;
- collision/helper geometry;
- GLB export;
- review renders.

All Blender sources and derived scripts/renders must remain under:
`collaborators/felix-volnox/blender/`
or inside the asset's own Felix sandbox package.

Do not overwrite owner Blender sources.

## Validation before calling an asset done

Check at minimum:

- GLB opens/imports successfully;
- scale and dimensions match the intended authority;
- orientation/front direction is documented;
- textures are present and correctly linked;
- no obvious missing body/prop sections;
- silhouette matches approved references;
- mesh is usable for the target runtime;
- provenance is recorded;
- preview images exist.

For animated characters also verify:

- skeleton/armature is intact;
- expected animations/clips are enumerated;
- retarget/bake status is documented;
- runtime-specific conversion requirements are recorded.

## Relationship to project tools

Felix may read and reuse project character bases, Blender scripts, animation research, rig-inspection workflows, map/export tooling, and future model tools as described in `TOOLBOX_POLICY.md`.

If an owner tool must be changed, copy/wrap it inside the Felix workspace rather than editing the original.

## Output rule

Regardless of which generator, Blender version, animation tool, VFX tool, or model service is used, **all Felix-created artifacts remain inside `collaborators/felix-volnox/` until owner approval promotes them.**