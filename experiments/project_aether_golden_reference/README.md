# Project Aether Golden Reference

Purpose: ingest the official Project Aether Unreal project as a reference implementation for XZIEL engine validation.

## Official provenance

Official project page: https://verrial.itch.io/projectaether

The Project Aether author states that the Discord server contains the full source project files for anyone to download and mod.

Discord invite:
https://discord.gg/Y8w25g2s6Z

## Current access state

The source download itself is hosted/referenced inside Discord. This repository automation does not have an authenticated Discord session, so the actual source archive URL has not yet been resolved.

## Import policy

Do not substitute:
- the compiled itch.io build for the editable Unreal source;
- NZ:P/Quake remakes for the map authority;
- unrelated "Project Aether" repositories.

Do not silently republish third-party Call of Duty assets. Before mirroring source binaries/assets into GitHub, preserve the original source license/redistribution terms and verify that redistribution is explicitly permitted.

If redistribution is not explicitly granted, keep only:
- provenance,
- hashes,
- inventory,
- conversion scripts,
- derived engine tests,
- and a reproducible fetch step pointing to the official source.

## GOLDEN target

Primary first target:
- Nacht der Untoten

Validation layers:
1. world geometry
2. collision
3. materials/textures
4. lighting and baked data
5. sky/cubemaps
6. FX
7. zombie meshes/rigs/animations
8. barricade/window interactions
9. spawn and round systems
10. weapons/viewmodels
11. movement
12. audio
13. high-round stress
14. Android/mobile conversion constraints

## Ingest workflow

The workflow `.github/workflows/project-aether-source-audit.yml` accepts a direct official source archive URL. It downloads the archive on a GitHub runner, computes SHA-256, inventories Unreal assets, and uploads the audit report only.

The source payload itself is intentionally not committed by the audit workflow until redistribution permission is verified.
