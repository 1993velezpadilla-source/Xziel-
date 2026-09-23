# Workspace Isolation Rules — Felix / Volnox

## Allowed

- Read and audit repository content.
- Use owner project documentation, research, sound-effect references, map research, tools, and model pipelines as reference.
- Create new collaborator-owned maps, models, assets, audio work, experiments, patches, research, and notes under `collaborators/felix-volnox/`.
- Commit Felix / Volnox work to `collab/felix-volnox-sandbox`.
- Prepare Pull Requests/diffs for owner review.

## Not allowed without explicit owner approval

- Direct changes to `main`.
- Direct changes to any existing owner branch.
- Editing owner project files outside `collaborators/felix-volnox/`.
- Merging Pull Requests.
- Rewriting branch history or force-pushing owner branches.
- Deleting branches, tags, releases, assets, or project files.
- Moving sandbox work into production paths.
- Changing repository security, access controls, Actions secrets, or release configuration.

## Owner gate

The repository owner is the final approval gate. A Pull Request is only a proposal. No collaborator or assisting AI should interpret an open PR, successful build, or completed map as authorization to merge.

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
