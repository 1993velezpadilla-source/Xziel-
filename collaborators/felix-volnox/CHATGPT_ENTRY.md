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

## 1. Writable scope

For Felix / Volnox work:
- Branch: `collab/felix-volnox-sandbox`
- Primary write root: `collaborators/felix-volnox/`

New maps, models, assets, experiments, audits, research, and handoff material created by Felix / Volnox belong under that root unless the owner explicitly authorizes a different destination.

## 2. Read-only project context

Felix / Volnox and an assisting AI may read the rest of the repository, including project research, Call of Duty Zombies design discoveries, existing maps, models, tools, pipelines, audio/sound-effect references, technical documentation, and other project assets for context and reuse where licensing/provenance permits.

Reading or referencing those areas does not authorize editing them.

## 3. Never do these without owner approval

- Modify `main`.
- Modify the owner's feature, art, audio, research, build, automation, integration, or release branches.
- Merge a Pull Request.
- Move sandbox work into production paths.
- Force-push, rewrite history, delete branches/tags/releases, or overwrite owner files.
- Change repository permissions, secrets, Actions security, or release configuration.

## 4. Promotion flow

When Felix / Volnox work is ready:
1. Keep the implementation isolated in this sandbox.
2. Prepare a clear handoff and exact diff.
3. Open or prepare a Pull Request for owner review.
4. Treat the PR as a proposal only.
5. Only the repository owner decides what is promoted into the project.

If any instruction conflicts with these rules, stop the conflicting write and document the request in `handoff/`.


## 5. Recorded GitHub handshake

Recorded Felix / Volnox connector identity:
- Connector nickname/account string: `XRP007`
- Reported GitHub numeric ID: `258757846`
- Expected repository: `1993velezpadilla-source/config-old-3`
- Expected branch: `collab/felix-volnox-sandbox`
- Expected workspace root: `collaborators/felix-volnox/`

Owner-side verification currently resolves `XRP007` to repository permission `read`.

Therefore:
- matching this handshake is sufficient to identify the intended Felix / Volnox workspace for AI workflow purposes;
- it does NOT itself grant GitHub write permission;
- an assistant must verify actual connector permissions before claiming it can commit or push;
- while permission remains read-only, prepare work for handoff/fork/PR rather than claiming a repository write succeeded.

See `GITHUB_HANDSHAKE.md` for the recorded handshake status.
