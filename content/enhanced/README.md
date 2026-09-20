# Enhanced Content

This directory is reserved for non-destructive visual upgrades to the Android port.

The current Classic gameplay/content remains the baseline. Enhanced content must be independently auditable and must not silently overwrite Classic source assets.

## Layout

- `asset_manifest.json` — provenance, license and intended role for every external asset.
- Future runtime-ready models/textures/sounds should be added only after an on-device validation pass.
- Source conversions should preserve enough metadata to reproduce the conversion.

## Shipping rule

No asset may ship in an Enhanced build unless:

1. its source is recorded;
2. its license explicitly permits the intended use;
3. the required attribution is known;
4. it is not ripped/extracted from a commercial game;
5. it has passed Android performance and rendering validation.

Run:

```bash
python3 scripts/validate_asset_manifest.py
```

before committing new third-party Enhanced assets.
