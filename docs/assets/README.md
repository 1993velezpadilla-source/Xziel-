# Xziel asset sourcing policy

Last reviewed: 2026-09-20

This repository deliberately separates assets for a future commercial Xziel game from research/reference material used while studying the NZ:P/community-port experience.

## Buckets

### 1. commercial-safe

An asset can enter this bucket only when its source page/license is verified and allows commercial use.

Preferred licenses:
- CC0 / public domain
- CC BY (with attribution tracked)
- MIT/BSD/Apache for code/shaders
- marketplace royalty-free licenses that explicitly allow commercial game use

Marketplace assets that forbid standalone redistribution may be used in compiled/embedded game builds when their EULA permits it, but the raw files must NOT be committed to this public repository.

### 2. attribution-required

Commercial use is allowed, but Xziel must preserve the creator, license, source URL and required attribution text in an attribution manifest/credits screen.

### 3. project-embedded-only

Examples: Unity Asset Store Standard EULA, Fab Standard License, CGTrader Royalty Free, Mixamo, Sonniss.

These may be commercially usable in a finished game, but raw source assets generally cannot be republished as a free asset pack or exposed for extraction. Store only metadata/source links/license notes in this public repo unless redistribution is explicitly allowed.

### 4. community-port-reference

Use for visual/motion/timing research and compatibility notes. This bucket is NOT a license to redistribute proprietary content.

Commercial-game extractions/rips (Call of Duty, etc.) must not be copied into Xziel's commercial-safe tree unless the rights holder has granted permission or the specific asset is independently released under a compatible license.

## Per-asset record

Every candidate should record:
- canonical source URL
- creator/publisher
- exact license shown at download time
- date verified
- commercial use yes/no
- raw redistribution yes/no
- attribution requirements
- formats
- rigged/animated status
- triangle/texture cost when known
- mobile suitability
- dismemberment readiness
- notes on trademarks/real-world weapon design risk

## Repository rule

Never infer that an entire marketplace is safe because one asset is safe. Verify each candidate page. If terms are unclear, classify it as `VERIFY_BEFORE_USE` rather than commercial-safe.
