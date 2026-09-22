# Sanctum character references

This directory is the repository-side inventory for the complete character/model reference set supplied for the current Sanctum pass.

**Scope:** 13 supplied reference images, 10 unique model/gameplay concepts.

Canonical model specifications live in:
- `docs/SANCTUM_CHARACTER_ROSTER_V1.md`
- `model_manifest.json`

A Blender-independent proxy generator lives at:
- `tools/sanctum_models/build_neutral_proxies.py`

The proxy generator is intentionally DCC-neutral. It creates importable OBJ/MTL scale-and-part scaffolds for all ten concepts so another agent can build the production model without using Blender.

Reference image IDs/names are retained in `model_manifest.json` so incoming binary reference assets can be matched deterministically and never confused with only the most recent uploads.
