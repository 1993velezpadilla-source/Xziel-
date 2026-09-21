# Xziel asset provenance gate

The engine now has a small content-policy layer so an automated asset-search
agent cannot treat the word "free" as equivalent to "safe to ship".

Every candidate model, animation, texture, particle texture, sound, font, map,
shader, or code dependency should carry provenance before it is admitted to a
first-party Xziel content pack.

Minimum record:

- logical asset ID
- original source URL
- author/creator
- exact license or license URL
- content hash
- asset category
- whether Xziel modified the asset

The default clean-engine policy accepts original work, CC0, permissive software
licenses where appropriate, and CC BY with attribution tracking. It rejects
unknown rights, non-commercial/editorial-only material, proprietary material,
ShareAlike assets unless that content pack explicitly opts in, and GPL code
dependencies unless a deliberately copyleft-compatible build opts in.

This is an engineering guardrail, not a substitute for reading the actual
license terms. The important rule for automated searches is conservative:
unknown provenance is a rejection, not an invitation to guess.

## Intended agent workflow

1. Search for a candidate asset.
2. Capture its source page before downloading.
3. Record creator + exact license.
4. Hash the downloaded source file.
5. Run the provenance policy.
6. Only then convert/optimize it into engine formats.
7. Keep attribution/change notes beside the generated content manifest.

For original procedural assets or assets created specifically for Xziel, mark
the source as Original and retain the source project when practical.

This keeps the independent Xziel engine clean while still allowing separate
community/legacy content packs to use different policies when their licenses
require it.
