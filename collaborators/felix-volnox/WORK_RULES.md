# Workspace Isolation Rules

## Allowed
- Read/audit repository content.
- Write reports, notes, experiments, patches, and prototypes inside this sandbox.
- Create commits on `collab/felix-volnox-sandbox`.
- Open Pull Requests for owner review.

## Not allowed without explicit owner approval
- Direct changes to `main`.
- Direct changes to existing owner branches.
- Merging Pull Requests.
- Rewriting branch history.
- Deleting branches, tags, releases, assets, or project files.
- Moving sandbox work into production paths.
- Changing repository security, Actions secrets, access controls, or release configuration.

## Owner gate
The repository owner is the final approval gate. A Pull Request is a proposal, not authorization to merge.

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
