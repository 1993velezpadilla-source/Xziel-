# NZ:P Community Source-Extraction Queue

Updated: 2026-09-20

Purpose: track every community release for which editable source or a source archive is known or plausibly recoverable. This queue separates **"we know source exists"** from **"we have actually parsed it"**.

## Priority A — explicit editable source published

| Map / archive | Source evidence | Current status | Extraction target |
|---|---|---|---|
| Kino der Toten (For realsies) | release says sources included; later comment publishes source files | SOURCE_AVAILABLE | exact teleporter / meteor-song / PAP graph |
| Facility V2 | release package confirmed to contain editable `.map` | SOURCE_AVAILABLE | key card, bonus PAP, Ray Gun EE, 5-teddy graph |
| Perish | J.A.C.K Project Files + Archive item `perish_202504` | SOURCE_AVAILABLE | baseline survival/door/zone graph |
| Simulacra | J.A.C.K source package on Internet Archive | SOURCE_AVAILABLE | hidden DTII progression, ending graph |
| Poop of the Dead | J.A.C.K project files published | SOURCE_AVAILABLE | inspect for hidden quests/interactions |
| Stairway to Heaven | J.A.C.K Project Files published | SOURCE_AVAILABLE | vertical progression, zoning, collision edge cases |
| BCDeshiG original Beta map packs | original packs explicitly include released mapper source files | SOURCE_ARCHIVE_AVAILABLE | enumerate + fingerprint every source map |

## Priority B — release archive available, editable source not yet proven

| Map | Why inspect |
|---|---|
| Yume Diner | key -> wooden-door interaction and teddy activity; broken release makes source inspection especially useful |
| Die Verlorenen | unlockable PAP + song + random perk + ending |
| Yukon Yard | hidden bunker -> PAP/ending; exact opening condition intentionally undisclosed |
| Haus Uberleben | Free Perk EE + unlockable PAP + buyable ending |
| TOILETTEN | explicit two-part EE + ending |
| BusDepot v1.0 | teddy EE / EE room / ending |
| The Thingy | teddy requirements, unlockables, PAP, teleporter, ending |
| Nacht der Untoten Plus | 5-teddy PAP EE |
| No Man's Land | round-gated spawns/shop + teddies + ending |
| Croft Manor | two collectible families + full EE/map ending |
| Isolation | teddy room + timed hidden rooms + reward |
| Der Riese community recreation | revision-dependent teddy EE |
| BO2 Town | broken five-teddy vault logic is valuable failure-analysis material |

## Priority C — historical/legacy recovery

### BCDeshiG Beta archive

The preservation repack states that the original Google Drive packs contain material omitted from the repack, including mapper source files.

Research goal:
- enumerate every map
- map old classnames to current compatibility layer
- locate quest patterns that disappeared from current stock maps
- record source/runtime generation separately

### Old forum migrations

Older map releases migrated into GitHub Discussions may point to:
- dead MediaFire links
- Archive.org preservation
- Google Drive mirrors
- mapper project files
- screenshots/tutorial posts that explain hidden mechanics

Do not discard dead-link entries. A dead download is still an identifier for archive/Wayback recovery.

## Extraction format

Every successfully obtained textual source should produce:

1. `source-manifest.json`
   - author/release
   - archive URL/identifier
   - file hashes
   - license/provenance
   - map/runtime generation

2. `<map>.logic.json`
   - every top-level entity key/value
   - no brush geometry duplication unless required to understand a trigger volume
   - target graph
   - unresolved references

3. `<map>.quest-subgraph.json`
   - high-signal quest/interact entities
   - graph closure around those nodes

4. `<map>.quest-architecture.md`
   - human reconstruction
   - player-count requirements
   - fail/retry behavior
   - bugs/version caveats
   - reusable normalized pattern

## Source access blocker

The current chat environment can inspect Archive.org item metadata and links, but direct ZIP retrieval has failed on redirect/network restrictions for at least one tested archive. Those releases remain **SOURCE_AVAILABLE_NOT_EXTRACTED**, not SOURCE_EXTRACTED.

Never promote status merely because a ZIP filename is visible.

