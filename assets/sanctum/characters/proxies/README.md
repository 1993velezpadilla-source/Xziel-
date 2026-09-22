# DEPRECATED FOR VISUAL / IN-GAME USE

The OBJ files in this directory are primitive scale/ID scaffolds created before the real free-model pipeline existed.

**DO NOT use these meshes as visible Sanctum characters.**
**DO NOT texture them and call them production models.**
**DO NOT ship them.**

They may only be used for:
- canonical height checks;
- socket/part naming experiments;
- collision/debug placeholders;
- verifying importer scale.

Visual/modeling work must start from:
- `assets/sanctum/free_models/`
- `assets/sanctum/free_models_expanded/`
- `assets/sanctum/character_bases/`

Target-to-base mapping:
- `assets/sanctum/characters/base_assignment.json`

Authoritative character art references:
- `docs/SANCTUM_CHARACTER_ROSTER_V1.md`
- user-supplied build sheets referenced by `assets/sanctum/characters/model_manifest.json`

Reason: the primitive proxies do not meet the visual quality bar for Sanctum and must never be presented as the intended characters.
