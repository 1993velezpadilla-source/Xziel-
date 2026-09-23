# Felix / Volnox Write Access Policy

## Required security model

GitHub repository-level `write` access is not path-scoped in this public personal repository. Therefore, Felix / Volnox must NOT be granted upstream repository-wide write access merely to work inside this folder.

Canonical workflow:

1. Upstream repository: `1993velezpadilla-source/config-old-3`
   - Felix / Volnox access: read/pull
2. Felix / Volnox works in a personal fork/copy where they have write access.
3. Intended upstream destination is restricted by project policy to:
   - Branch target: `collab/felix-volnox-sandbox`
   - Path: `collaborators/felix-volnox/**`
4. Submit a Pull Request back to the upstream repository.
5. Owner reviews the exact diff.
6. Any change outside `collaborators/felix-volnox/**` must be rejected or removed unless the owner explicitly authorizes it.

## Identity

- Human aliases: Felix / Félix / Volnox
- Connector account string: `XRP007`
- Reported GitHub numeric ID: `258757846`

## Important

Do not interpret the workspace path as a native GitHub ACL. It is a project-enforced boundary.
Do not grant repository-wide `write` access as a substitute for path-scoped access.
