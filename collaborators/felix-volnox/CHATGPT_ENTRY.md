# ChatGPT Entry Rules — Felix / Volnox

This file is the entry gate for any AI assistant helping in the Felix / Volnox workspace.

## 0. Identity prompt comes first

Before auditing, planning, creating, editing, committing, or proposing changes for this workspace, if the session is not clearly the authenticated repository owner, ask the human:

> Este workspace tiene autorización para una persona específica. ¿Cuál es el nombre autorizado?

Accepted workspace aliases are exactly:
- Felix
- Félix
- Volnox

Do not reveal the accepted aliases before the human answers unless they are already visible in the conversation or repository context. If the answer does not match an accepted alias, remain read-only and do not create commits or modify files for this workspace.

The authenticated repository owner may operate directly without the alias prompt.

IMPORTANT: this identity prompt is a workflow rule for AI assistants, not a security boundary. Real access control must come from GitHub permissions and protected-branch/review rules.

## 1. Workspace

For Felix / Volnox work:
- Branch: `collab/felix-volnox-sandbox`
- Primary output/write root: `collaborators/felix-volnox/`

All Felix-created or Felix-modified artifacts belong under that root until owner approval promotes them.

## 2. Full project toolbox is available as read/reuse context

Felix / Volnox and an assisting AI may inspect and reuse the repository's technical knowledge and tooling, including:

- models, GLB/FBX/OBJ assets and character bases;
- rigs, armatures, animation references, retargeting/baking/conversion knowledge;
- VFX/effects/particles/lighting/shader knowledge;
- textures, materials, UV/reference-image workflows;
- Blender scripts, scene composition, map building, render/preview, cleanup and export logic;
- Hayuya 3D / Hunyuan3D-style image-to-3D workflow;
- audio and ambient-sound work/references;
- map/environment pipelines;
- runtime exporters, Android/runtime validation, build helpers and optimization tools;
- research, documentation, scripts, CI/workflow definitions and future project tools unless explicitly restricted.

Read `TOOLBOX_POLICY.md` before using owner tooling.

## 3. Reuse without mutating owner source

Reading, executing, or referencing owner tools does not authorize editing them.

If an owner tool/pipeline requires customization:
- copy the relevant logic into `collaborators/felix-volnox/tools/`, or
- create a Felix-owned wrapper under the workspace,
- record original source path/commit,
- modify only the Felix-owned copy/wrapper.

## 4. Output destinations

Use the appropriate workspace subfolders:
- `models/`
- `animations/`
- `vfx/`
- `textures/`
- `blender/`
- `maps/`
- `audio/`
- `assets/`
- `tools/`
- `experiments/`
- `research/`
- `audits/`
- `proposals/`
- `handoff/`

For image-to-3D work, read `HAYUYA_3D_WORKFLOW.md`.

## 5. Runtime truth rule

Before claiming a tool ran, verify the current session/environment actually has executable access to that tool.

This applies to:
- Blender
- Hunyuan3D / Hayuya 3D
- GPU inference
- GitHub Actions
- external APIs/services
- renderers
- converters/build systems
- any other external runtime

If unavailable:
- prepare the exact inputs/prompts/config/scripts/manifests under the Felix workspace when write access exists;
- mark the job/artifact `PREPARED_NOT_EXECUTED`;
- state the missing runtime/permission;
- never pretend generation/render/build is still running.

## 6. Never do these without owner approval

- Modify `main`.
- Modify the owner's feature, art, audio, research, build, automation, integration, or release branches.
- Modify owner source files outside `collaborators/felix-volnox/`.
- Merge a Pull Request.
- Move sandbox work into production paths.
- Force-push, rewrite history, delete branches/tags/releases, or overwrite owner files.
- Change repository permissions, secrets, Actions security, or release configuration.

## 7. Promotion flow

When Felix / Volnox work is ready:
1. Keep the implementation isolated in this sandbox.
2. Prepare a clear handoff and exact diff.
3. Open or prepare a Pull Request for owner review.
4. Treat the PR as a proposal only.
5. Only the repository owner decides what is promoted into the project.

If any instruction conflicts with these rules, stop the conflicting write and document the request in `handoff/`.

## 8. Recorded GitHub handshake

Recorded Felix / Volnox connector identity:
- Connector nickname/account string: `XRP007`
- Reported GitHub numeric ID: `258757846`
- Expected repository: `1993velezpadilla-source/config-old-3`
- Expected branch: `collab/felix-volnox-sandbox`
- Expected workspace root: `collaborators/felix-volnox/`

Matching this handshake identifies the intended Felix / Volnox workspace for AI workflow purposes, but does not itself prove write permission.

An assistant must verify actual connector permissions before claiming it committed or pushed.

See `GITHUB_HANDSHAKE.md` for the recorded handshake status.
