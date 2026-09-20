# MAP LIBRARY EXPANSION — Native Android NZ:P

## Goal

Grow the Android port beyond the stock map set without turning map work into custom level-design from scratch.

Priority order:

1. **NZ:P-native playable map with editable source**
2. NZ:P-native playable map with compiled BSP/package
3. legacy NZ:P map with known PSP compatibility
4. original freely licensed Quake/GoldSrc brush map source
5. author-permitted Source VMF conversion candidate
6. reference-only maps with unclear/commercial IP — never bundle blindly

Classic content is preserved. Enhanced visuals are a separate presentation pass.

---

## Tier A — Best targets: NZ:P native + editable

### Nacht der Untoten
Already in upstream source:
`nzp-team/assets/source/maps/ndu/ndu.map`

Status: first Enhanced vertical slice.

### Kino der Toten (For realsies)
- NZ:P-native playable release.
- Original release explicitly includes sources.
- Later community update published source files again and fixed most waypoints/spawns plus lighting/detail.
- Known mobile/performance issues make it a perfect second optimization benchmark after Nacht.

### Facility V2
- NZ:P-native original community map.
- Download includes the actual `.map`.
- Has functional zones, interactables, waypoints and clipping fixes.
- Excellent source for a full Enhanced research-facility makeover.

### Simulacra
- NZ:P-native original map.
- Public project files.
- Existing cleanup work covers clipping, geometry and zombie-stuck cases.
- Strong candidate for high-detail suburban/lab Enhanced assets.

### Perish
- NZ:P-native original map.
- J.A.C.K Project Files are public.
- Existing presentation intentionally uses dev-style textures in places.
- One of the strongest candidates for showing how much Enhanced can transform a map while retaining gameplay.

### Stairway to Heaven
- 2026 NZ:P native release.
- J.A.C.K Project Files publicly linked.
- Zones implemented.
- Post-release collision exploits around archways were actively fixed.
- Small/mid-size map makes it a good stress/profiling candidate.

---

## Tier B — Native NZ:P playable candidates

These already provide compiled gameplay/collision and may need source/author contact before deep edits:

- Isolation
- Yukon Yard
- One Window In NZP
- Haus Uberleben
- Poop of the Dead
- Alley
- Teddy Survival
- Pump
- TOILETTEN
- The Thingy
- Bus Depot
- No Man's Land
- Shipment Survival
- Das Alte Haus

For each:
1. inspect package;
2. locate `.map`, JMF/RMF, WAD and waypoint/zone files;
3. identify author/license/redistribution permission;
4. test directly in native Android;
5. only then decide whether to Enhanced-reskin or merely support as an optional map.

---

## Tier C — COD / other-franchise fan remakes

Useful for the fan build, but keep separate from a future commercial-safe original game.

Known candidates:

- Kino der Toten
- BO2 Town
- Der Riese
- Bus Depot
- Shipment Survival
- No Man's Land / Moon-spawn concept
- Croft Manor (Tomb Raider-derived)
- Das Alte Haus (remake of a WaW custom-zombies map)

These can still be excellent technical/performance targets for the current fan port.

---

## Nuketown status

### Native NZ:P
A direct search of the current NZ:P release catalog did **not** reveal a finished Nuketown release.

There is an NZ:P discussion (#920, October 2024) specifically asking for Nuketown, with community members expressing interest in making it, but it did not become a current release entry.

### External fan-source routes found

#### BO3 — clixmods/zm_nuked
Public GitHub repository with:
- zombie/dog scripts;
- perks;
- mannequin features;
- clock feature;
- PaP-from-sky logic;
- floating debris;
- ambience.

**No map geometry/source is present.**
Use as behavior/reference only.

#### Source/TTT Nuketown Light Edition
An author publicly posted a VMF source.

Why interesting:
- VMF is editable brush geometry rather than a dead mesh;
- VMF can be converted to Valve-style `.map`;
- collision/world structure is much closer to what NZ:P needs.

Before use:
- get/confirm permission where needed;
- audit map-layout and third-party IP implications;
- throw away any ripped COD props/textures;
- replace them with our CC0 suburban library.

#### GMod/nZombies Nuketown
Useful as:
- nav/layout reference;
- zombie config reference;
- collision reference.

Do **not** reuse the ported/ripped COD props present in some GMod versions.

### Legal replacement pool already selected

- Kenney City Kit Suburban
- Kenney City Kit Roads
- CC0 mannequins
- CC0 generic cars
- CC0 bus
- CC0 wall clock
- CC0 modular vehicle library

This lets us build a visually recognizable 1950s/60s test-town *style* from clean assets even if the original fan map contains ripped prop models.

---

## Tier D — legacy NZ:P archive

BCDeshiG's preserved beta-map archive is a large research pool.

The archive/repack includes many historical NZ:P maps, while the original linked map packs reportedly include some mapper source files and additional assets.

Historical PSP-tested names include many small maps that are ideal Android candidates:
- Castle of Doom
- Ankunft Der Toten
- Haus des Grauens
- Compact
- Temple
- Reticent
- Zombie Island
- Subway
- Yard
- SmallFactory
- U-bahn
- Hall5
- UntotenHaus
- Gunstore
- Bakaara
- Desolate
- Containment
- Apartment
- NightHouse
- Olympus
- The Last Stand
- and many more

These are valuable because PSP compatibility strongly suggests lightweight geometry, but every individual package still needs provenance/asset review.

---

## Tier E — original external brush-map libraries

These are especially interesting for making **new zombie maps quickly**.

### Spirit Quake Maps GPL
Repository:
`dfsp-spirit/spirit-quake-maps-gpl`

- 21 editable `.map` sources.
- Author explicitly places his map geometry under GPL-2.0.
- Author explicitly warns that original textures/sounds/models are separate and should generally be replaced.

This is almost ideal for us:
**use legal brush layout -> replace all presentation -> add NZ:P gameplay entities.**

### Quetoo Data
Repository:
`jdolan/quetoo-data`

- 80+ editable map sources in the repo.
- TrenchBroom / Quake3-map format.
- Repository is CC-BY-SA 4.0.
- Includes original designs **and** remakes of id maps.

Rule:
Only use individually audited original maps. Do not automatically take remakes.

### RBDOOM-3-BFG Mod Unit Tests
- CC0 repo.
- Editable Valve220/Doom3 `.map` files.
- Useful mostly as conversion/testing layouts rather than finished zombie maps.

### Simple AFPS Level
- Original CC0 Quake-style arena.
- Blend + OBJ rather than brush-map source.
- Useful as a completely clean lightweight arena prototype if needed.

### GoldSrc Restored Sources
Repository claims CC0, but sources are reconstructed from commercial maps.

**REFERENCE ONLY.**
A restorer cannot automatically erase the underlying map owner's rights.

---

## Official NZ:P conversion/build pipeline

The official `nzp-team/toolbox` changes the economics of map conversion.

It can:
- create a new buildable NZ:P `.map` from a template;
- build WADs;
- compile a `.map` through the full BSP pipeline;
- generate Spawn Zones during `build-map`;
- compile QuakeC.

So an external legal brush map does **not** need to arrive as a complete zombie map.

### Conversion recipe

```text
LEGAL EDITABLE MAP SOURCE
          ↓
normalize to Valve/GoldSrc-compatible brush map
          ↓
replace foreign entities
          ↓
replace/retarget textures
          ↓
add NZ:P worldspawn/settings
          ↓
add player start
          ↓
add zombie windows/spawn_zombie
          ↓
add pathing / waypoints
          ↓
add doors / zones / prices
          ↓
add Mystery Box locations
          ↓
add power/perks/PaP if desired
          ↓
NZ:P toolbox build-map
          ↓
spawn-zone generation + BSP compilation
          ↓
native Android test
          ↓
Enhanced visual pass
```

The biggest work is therefore **zombie gameplay authoring and validation**, not rebuilding collision geometry.

---

## Tooling leads

### vmf2map
Can convert Source VMF brush maps into Valve-style `.map`.
Displacements become ordinary brushes, so output needs manual review.

### hltools
Modern GoldSrc toolchain with:
- map compile;
- BSP decompile;
- Source BSP -> GoldSrc MAP porting;
- texture/WAD tooling;
- collision/lightmap analysis.

Use conversion only for content we have rights to use.

---

## Recommended map rollout after Nacht

1. **Nacht Enhanced** — establish entire pipeline.
2. **Kino Enhanced** — large classic map + performance optimization.
3. **Facility V2 Enhanced** — first original editable community map.
4. **Perish Enhanced** — prove full visual transformation.
5. **Simulacra Enhanced** — large original map.
6. **Stairway to Heaven** — compact editable challenge map.
7. **BO2 Town fan-build test** — test external classic remake compatibility.
8. **Nuketown prototype** — only after an editable permitted geometry base is secured.
9. Start converting an **original GPL/CC brush map** into a brand-new zombie map.

This sequence maximizes reusable work instead of creating one-off map hacks.
