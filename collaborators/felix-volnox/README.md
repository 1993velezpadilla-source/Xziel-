# Felix / Volnox Collaboration Sandbox

Dedicated workspace for Felix / Volnox inside the ZOMBIESSSSSSS PORTABLE repository.

## Goal

Felix / Volnox can study and reuse the full project toolbox—models, animation, effects/VFX, textures, audio, maps, Blender pipelines, model generation, exporters, scripts, research and future tools—while keeping all collaborator-created work isolated from the owner's active project.

## Branch

Work on:

`collab/felix-volnox-sandbox`

Primary writable/output area:

`collaborators/felix-volnox/`

## Full toolbox access model

Felix / Volnox may read and reuse the rest of the repository as project context and technical source material where licensing/provenance permits.

This includes existing:
- models and character bases;
- rigs, animation research and retarget/bake knowledge;
- effects/VFX/lighting knowledge;
- texture/material/reference-image workflows;
- audio/sound-effect research and pipelines;
- maps and environment pipelines;
- Blender scripts/workflows;
- Hayuya 3D / Hunyuan3D-style image-to-3D workflow;
- exporters, runtime conversion, Android/runtime tests, build helpers and optimization knowledge;
- scripts, CI/workflow definitions, documentation and research;
- future project tools unless the owner explicitly restricts them.

See `TOOLBOX_POLICY.md` for the exact reuse/isolation contract.

## What Felix / Volnox can create here

- `maps/` — maps and map-specific work
- `models/` — GLB/FBX/OBJ/model-generation output
- `animations/` — rigs, clips, retarget/bake output and animation reports
- `vfx/` — effects, particles, shaders/effect experiments and lighting work
- `textures/` — textures, materials, masks, UV/reference-image work
- `blender/` — .blend files, Blender scripts/wrappers, renders and exports
- `audio/` — collaborator-created/approved audio work and references
- `assets/` — collaborator-created/imported assets with provenance
- `tools/` — copied/adapted helper tools and wrappers
- `audits/` — repository audits and findings
- `proposals/` — proposed changes before promotion
- `experiments/` — isolated prototypes
- `research/` — source-backed research
- `handoff/` — material prepared for owner review

## Hayuya 3D

Within this workspace, "Hayuya 3D" refers to the Hunyuan3D-style image-to-3D/GLB workflow defined in:

`HAYUYA_3D_WORKFLOW.md`

That workflow includes source/reference preparation, dimensional authority, GLB packaging, Blender finishing, previews and validation.

## Important execution rule

Being able to read a tool/pipeline does not prove the active ChatGPT session can actually execute Blender, Hunyuan3D, GPU inference, GitHub Actions, external APIs or other runtimes.

An assistant must verify execution access before claiming a tool ran. If unavailable, prepare the complete job under this workspace and mark it `PREPARED_NOT_EXECUTED`.

## Isolation rule

Owner project files outside `collaborators/felix-volnox/` are not to be modified by Felix unless the owner explicitly authorizes the exact edit.

If an owner tool needs adaptation, copy/wrap it under `collaborators/felix-volnox/tools/` or another Felix-owned subfolder and preserve provenance.

## Promotion rule

Nothing in this workspace becomes part of the main project automatically. Promotion requires owner review and approval through a Pull Request/diff.

See:
- `CHATGPT_ENTRY.md` — AI entry rules
- `WORK_RULES.md` — isolation and execution rules
- `TOOLBOX_POLICY.md` — complete toolbox access contract
- `HAYUYA_3D_WORKFLOW.md` — image-to-3D workflow
- `GITHUB_HANDSHAKE.md` — identity/access handshake status

## Verified collaborator handshake

Felix / Volnox handshake is recorded in `GITHUB_HANDSHAKE.md`.
Current GitHub account string: `XRP007`.

Actual GitHub write capability must be verified by the active connector before any assistant claims a commit/push succeeded.
