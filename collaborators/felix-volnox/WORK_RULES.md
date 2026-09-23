# Workspace Isolation Rules — Felix / Volnox

## Core rule

Felix / Volnox may use the full project knowledge/toolbox for their own work, but every collaborator-created or collaborator-modified artifact must remain inside:

- branch: `collab/felix-volnox-sandbox`
- root: `collaborators/felix-volnox/`

until the repository owner explicitly approves promotion.

## Allowed

- Read and audit repository content.
- Inspect and reuse owner project documentation, research, models, rigs, animation knowledge, sound/audio references, textures/material references, map research, VFX/effects knowledge, tools, scripts, Blender pipelines, model-generation workflows, exporters, build helpers and optimization knowledge.
- Invoke existing owner tools/workflows when the active credential/runtime actually permits execution and the invocation does not mutate owner source files.
- Create collaborator-owned maps, models, animations, rigs, VFX/effects, textures, materials, Blender scenes/scripts, audio work, tools/wrappers, experiments, patches, research, previews, exports and notes under `collaborators/felix-volnox/`.
- Use Hayuya 3D / Hunyuan3D image-to-3D workflow as defined in `HAYUYA_3D_WORKFLOW.md`.
- Commit Felix / Volnox work to `collab/felix-volnox-sandbox`.
- Prepare Pull Requests/diffs for owner review.

## Copy/wrap rule

If an owner tool, Blender script, exporter, model pipeline, animation helper, VFX helper, workflow, or other project file needs modification:

1. Read the owner version.
2. Copy the required logic into the Felix workspace or create a Felix-owned wrapper.
3. Modify only the Felix-owned copy/wrapper.
4. Record original path/commit as provenance.

Do not edit owner source files outside the sandbox without explicit owner approval for that exact edit.

## Not allowed without explicit owner approval

- Direct changes to `main`.
- Direct changes to any existing owner branch.
- Editing owner project files outside `collaborators/felix-volnox/`.
- Merging Pull Requests.
- Rewriting branch history or force-pushing owner branches.
- Deleting branches, tags, releases, assets, or project files.
- Moving sandbox work into production paths.
- Changing repository security, access controls, Actions secrets, or release configuration.

## Runtime truth

Repository documentation is not proof that the current ChatGPT/session can execute a tool.

Before claiming Blender, Hunyuan3D/Hayuye 3D, GPU generation, GitHub Actions, an external API, a renderer, conversion tool, or build actually ran, the assistant must verify execution access in the active environment.

If execution is unavailable, prepare the exact job/assets/scripts/manifests under the Felix workspace and mark it `PREPARED_NOT_EXECUTED`.

## Owner gate

The repository owner is the final approval gate. A Pull Request is only a proposal. No collaborator or assisting AI should interpret an open PR, successful build, generated model, render, animation, or completed map as authorization to merge/promote.

## Asset discipline

Every new external asset should record source/provenance and license or usage status when known. Do not commit credentials, tokens, secrets, or content that the project is not permitted to redistribute.

## Audit discipline

Every audit should include:
- scope
- branch/commit reviewed
- findings
- severity
- evidence/path
- recommended fix
- whether a patch exists
- files changed by the patch
