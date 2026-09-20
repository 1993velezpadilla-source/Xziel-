# MASTER ASSET HUNT — Enhanced / Shattered NZ:P Android

## Mission

Build a high-quality optional visual/audio layer over the existing mobile port without changing the gameplay that already works.

**Classic remains untouched.**

Enhanced assets must be:
- free or already permitted for the project;
- commercially usable even if the current fan build is not monetized;
- provenance-tracked;
- mobile-conscious;
- replaceable independently;
- incapable of changing collision, enemy balance, weapon damage, round logic or map routing by accident.

Nacht der Untoten is the first vertical slice. Once the pipeline is proven there, reuse the same libraries across the rest of the maps.

---

# 1. Full replacement inventory

This inventory comes from inspecting the real NZ:P QuakeC and asset tree, not from guessing.

## A. World / architecture

- concrete walls
- brick
- plaster
- damaged concrete
- floors
- tiles
- wood floors
- wood boards
- metal panels
- corrugated/rusted metal
- doors
- doorway frames
- ceilings
- stairs
- railings
- barbed wire
- windows/glass
- dirt/mud
- gravel
- rubble
- trim
- pipes
- drains
- vents
- fences
- skybox
- fog / atmospheric treatment
- map-specific posters/signage where legally safe

### Quality rule
Do not turn every detail into geometry. Tiny floor grit, pebbles and cracks should usually be baked into textures on Low/Medium and only become sparse meshes on High/Max.

---

## B. General props

The stock asset tree includes or implies all of these categories:

- explosive barrels
- crates / boxes
- ammo cans
- trash cans
- trash bags
- lockers
- shelves
- sandbags
- rebar
- metal chairs
- couches
- tables
- lamps
- chandeliers
- radiators
- radios
- gramophones
- projector
- piano
- beds
- baths
- toilets / urinals
- body bags
- dentist/medical chairs
- fridge
- oven
- vanity table
- mop bucket
- generator
- wires
- fuse boxes
- electrical switches
- transformers
- pumps
- valves
- pipes
- jeep / military vehicle props
- trees / dead trees / swamp vegetation
- dead bodies / decorative corpses

Every common prop should have:
- low-end version or Classic fallback;
- mobile triangle budget;
- texture-size budget;
- provenance/license record.

---

## C. Zombie / enemy layer

### Regular zombies
Target a library of many ready-made visual variants, while gameplay remains one regular-zombie class.

Required compatibility:
- idle
- walk
- run
- attack
- hit reaction
- death
- crawler
- head removal
- arm removal
- lower-body/leg damage where supported
- same gameplay hit/health rules independent of skin

### Hounds
- multiple visual variants
- run
- attack
- spawn materialization/lightning
- death
- optional smoke/embers/glow
- same dog gameplay class

### Gore
- blood hit sprite
- blood decals
- 3D gibs
- limb pieces
- organs/meat chunks on high-impact deaths
- blood mist
- optional ground splatter persistence by quality tier

Primary ready-made candidates are in `content/enhanced/asset_manifest.json`.

---

# 2. First-person presentation — easy to forget, always visible

## Arms / hands
Enhanced must eventually replace the low-resolution first-person hands/arms.

Targets:
- idle
- firing support poses
- reload support
- grab/use
- knife
- grenade
- perk drink
- machine interaction
- weapon take-out / put-away

Current candidates:
- Drillimpact PSX First Person Arms — CC0, already animated.
- WRAD ARMS — CC0, ~1200 tris, IK rig.

## Weapon micro-details
Do not forget:
- shell casings
- magazine models
- bolt/slide motion
- muzzle flash variation
- post-shot smoke
- muzzle dynamic light
- bullet impact particles
- bullet-hole decals
- metal impact sparks
- reload sounds
- dry fire
- chamber / bolt sounds
- weapon handling cloth/hand sounds

These are presentation-only; shooting logic remains unchanged.

---

# 3. Mystery Box — full Enhanced checklist

Existing gameplay code already separates the presentation pieces.

Replace or improve:
- main box model/material
- lid/open animation
- close animation
- glow model/effect
- floating weapon presentation
- cycling weapon aura
- sparkles
- opening flash
- surrounding dynamic light
- smoke/dust motes
- teddy model
- teddy float/leave presentation
- box relocation sparks/woosh
- open / close / relocate audio
- nearby wall illumination on Medium+

Never change:
- cost
- RNG
- weapon list
- ownership
- teddy odds
- timing unless fixing an actual bug

### Current teddy candidate
Renend Studio low-poly vintage teddy — CC BY 4.0, ~1.5K polygons.

---

# 4. Perk-machine system

The current code already supports:
- multiple perk machine classes;
- per-machine colored light;
- vending sound;
- drink first-person model;
- player drink animation;
- machine music/voice slots;
- power-on/off behavior.

## Enhanced machine base

Use one legal generic vending-machine architecture and create multiple visual identities by swapping:
- front plate
- paint
- glass
- label
- bottle/can
- emissive panel
- light color
- decals
- audio
- purchase VFX

### Base candidates

**Valentin Laffitte Retro Vending Machine**
- CC0
- low poly / game ready
- FBX + GLTF/GLB
- best mobile base candidate

**Jonathan Dexter Ogilvie Vending Machine**
- CC BY 4.0
- modeled interior
- openable door
- good reference/base when a mechanical opening/dispensing action is useful

## Perk drink models
Use generic original bottle/can assets and custom skins.

Candidate:
**Liquid Assets: Low-Poly Drinks Pack**
- CC0
- aluminum can
- water bottle
- glass soda bottle
- FBX/Blend

## Perk-machine FX
Ready-made CC0 building blocks:
- sparks
- electricity
- glow masks
- smoke/steam
- pickup flashes
- light cookies
- small magical/energy bursts

Use Kenney Particle Pack and Brackeys VFX Bundle as primary sources.

## Perk purchase sequence target

1. interact;
2. machine flashes / button responds;
3. mechanical vend sound;
4. bottle/can dispenses;
5. player viewmodel swaps to drink hands;
6. drink animation;
7. colored acquisition flash/aura;
8. perk icon appears;
9. normal weapon viewmodel returns.

No stat/balance change.

---

# 5. Power switch / electrical systems

The existing game has a real power switch entity and handle.

Enhanced targets:
- switch cabinet
- handle
- fuse box
- circuit breaker
- cables
- exposed wires
- sparks
- transformer/generator props
- power-on flash
- lightstyle transition
- electric hum / switch clunk
- map lights waking up in sequence

Primary ready-made CC0 candidate:

**3D Retro Plumbing, Wiring & Machinery — chilly_durango**
Includes:
- circuit breaker
- fuse
- wires
- hanging wire
- on/off/unpowered switches
- turbine
- pump
- pipes
- valve
- generator
- transformer

This pack should become a reusable library for Der Riese/factory, bunkers, warehouses and custom maps.

---

# 6. Pack-a-Punch / weapon-upgrade presentation

The stock system already has:
- machine
- roller
- flag
- first-person insertion viewmodel
- floating weapon
- tick
- gear shift
- upgrade sound
- cyan light
- upgraded weapon presentation

Enhanced needs a legal/original visual machine identity, but the interaction pipeline can remain.

Required visual pieces:
- machine body
- intake slot
- moving rollers/gears
- weapon entering machine
- internal sparks/electricity
- light pulse
- processing animation
- weapon return
- upgraded weapon aura
- upgraded muzzle/weapon effect set

Reuse the electrical/VFX libraries rather than authoring effects from scratch.

---

# 7. Teleporter / high-energy interactives

The game already contains teleporter entrance, destination and mainframe-pad logic.

Enhanced checklist:
- pad/mainframe model
- cable/industrial support props
- electric arcs
- charge-up sparks
- floor glow
- flash
- smoke/fog burst
- temporary dynamic light
- zap audio
- charge loop
- cooldown state visual

Use the CC0 lightning arc textures and CC0 industrial electrical kit.

---

# 8. Power-ups — often forgotten

The current game has these stock power-up model slots:

- Nuke
- Insta-Kill
- Double Points
- Carpenter
- Max Ammo
- Free Perk
- Weapon Upgrade
- Bonus Points

They also already have:
- drop sound
- pickup sound
- sparkle model
- green light
- flashing/disappearance logic
- voiceover slots

Enhanced should replace **all of them**, not only the maps.

## Candidate building blocks

- Carpenter: Kutejnikov weathered CC0 PBR hammer (~1.5K tris)
- Max Ammo: Poly Haven CC0 military ammo box (~4K tris)
- Free Perk: generic CC0 glass/soda bottle with original skin
- Nuke: use a generic original bomb/warhead shape, not COD art
- Insta-Kill: use a legally sourced generic skull / original variant
- Double Points: original floating multiplier token/model
- Bonus Points: original point token/currency icon
- Upgrade Weapon: original energy/tool symbol

Power-up animations can remain simple:
- slow spin
- vertical bob
- sparkle
- glow
- pickup burst

No need for expensive skeletal animation.

---

# 9. Wall buys / barricades / doors

## Wall buys

Current code uses:
- chalk model
- weapon prop
- purchase prompt
- buy sound
- ammo repurchase flow

Enhanced:
- generate the silhouette/chalk graphic from the actual enhanced weapon model;
- higher-quality emissive/chalk edge;
- optional dust/chalk particles on interaction;
- modern weapon prop when map uses a 3D wall weapon.

No external chalk art library is required.

## Barricades

The real window system has many frame states for board removal/repair.

Enhanced needs:
- better wood-board model/material
- wood splinters
- board impact dust
- break sound
- repair sound
- optional small debris
- same health/state machine

## Doors/debris
- wood door
- metal door
- debris pile
- hinges / sliding mechanisms
- dust when clearing debris
- metal/wood sounds by material

---

# 10. VFX master library

Must cover:

- muzzle flash
- barrel explosion
- grenade explosion
- Ray/energy projectile
- Ray/energy impact splash
- plasma ring
- electric arc
- sparks
- fire
- embers
- smoke
- steam
- dust
- blood hit
- blood mist
- blood splatter
- bullet impact
- bullet-hole decal
- wood splinter
- concrete dust
- metal spark
- pickup sparkle
- perk acquisition
- teleporter charge
- power-switch short circuit
- Mystery Box aura
- dog spawn/lightning
- fog wisps

Primary free sources:
- Brackeys VFX Bundle — CC0
- Kenney Particle Pack — CC0, 80+ particle/light-cookie sprites
- Unity Labs CC0 flipbooks
- OpenGameArt lightning arcs — CC0
- OpenGameArt muzzle-flash sheet — CC0
- OpenGameArt blood packs — CC0

Quality presets control count/lifetime, not gameplay.

---

# 11. Audio master library

Do not leave audio as an afterthought.

## Categories

### Player
- concrete/wood/metal/dirt/water footsteps
- jump
- land
- breath
- cloth
- pain
- revive/downed
- interact

### Weapons
- gunshots
- mechanical action
- reload
- mag handling
- shell drop
- dry fire
- melee
- grenade pin/throw
- explosions
- Ray/energy weapon
- upgraded weapon layer

### Zombies/hounds
- idle groan
- alert
- attack
- hit
- death
- crawler
- dog attack
- dog death
- dog spawn

### Machines
- perk idle hum
- perk vend
- drink
- power switch
- generator hum
- Mystery Box open/close
- Mystery Box relocation
- upgrade machine
- teleporter
- electrical crackle

### Environment
- wind
- distant structure creaks
- building rumble
- fire
- metal groans
- radio/static
- room tone
- swamp/water for applicable maps
- theater projector/mechanical ambience for applicable maps

### UI
- menu navigate
- confirm
- deny
- points gain
- points spend
- power-up pickup
- round cue

## Candidate libraries

**OwlishMedia Sound Effects Pack — CC0**
Foley, footsteps, impacts, UI, human, sci-fi, technology, water.

**Fantozzi Footsteps — CC0**
Stone/hard-surface and sand/grass variations.

**BMacZero Metal Impacts — CC0**
Clangs, clinks, thuds.

**Sonniss GDC 2026 Game Audio Bundle**
7.47GB+, 347+ files, royalty-free, commercially usable, no attribution required.
Use as a cherry-pick library, not as a 7GB APK payload. Preserve its own license file with anything selected.

---

# 12. HUD / UI / typography

Enhance:
- bitmap charset/font
- points
- score gain/loss popup
- ammo numbers
- round counter
- perk icons
- power-up icons
- hit marker
- crosshair
- use prompt
- buy prompt
- down/revive indicator
- loading screen
- map thumbnail
- menu icons
- weapon switch HUD
- pause/settings presentation

Candidate font:
**Barlow Condensed — OFL 1.1**

Classic retains current font/UI.

---

# 13. Sky / fog / lighting

## Nacht
Candidate:
**Poly Haven Kloppenheim 07 Pure Sky**
- CC0
- overcast night
- convert HDRI -> six cubemap faces for Vril

Other Poly Haven abandoned/industrial HDRIs are useful as lighting/reference sources.

## Vril-safe lighting strategy

Classic:
- stock behavior

Enhanced Low:
- cheap existing dynamic-light presentation
- no model shadows

Medium:
- surface-reactive dynamic lighting

High:
- dynamic lights + projected model shadows

Max:
- same features at highest validated counts/radii
- denser particles/decals/clutter
- best LODs/textures that fit memory

Do not pretend Vril currently has FTE realtime shadow maps, HDR or bloom.

---

# 14. Map-family asset pools

## Nacht / bunker
- concrete
- ruined brick
- wood barricades
- sandbags
- ammo boxes
- industrial lamps
- barrels
- military clutter
- radio
- rubble
- wires
- old furniture

## Kino / theater-style maps
- theater seats
- stage curtains
- projectors
- spotlights
- backstage crates
- dressing-room furniture
- chandeliers/wall lamps
- posters/sign frames
- stage rigging
- cables
- velvet/fabric surfaces

## Verrückt / asylum-hospital maps
- hospital beds
- medical carts
- privacy screens
- cabinets
- sinks/baths
- toilets
- operating/dentist chairs
- body bags
- broken tiles
- institutional lamps
- medical clutter

## Shi No Numa / swamp maps
- wet wood
- mud
- swamp water
- roots/trees
- reeds
- huts
- barrels
- ropes
- crates
- fog
- insects/ambient audio

## Der Riese / industrial-factory maps
- generators
- transformers
- fuse boxes
- pipes
- valves
- catwalks
- industrial lamps
- control panels
- metal doors
- cable drums
- machinery
- heavy electrical VFX

## Current official source-map families
The upstream asset repo currently contains editable sources for:
- 4all
- b1oodv3
- b1oodv4
- boxxer
- bunker-defense
- christmas_special
- dung3on
- fegefeuer
- hangar
- lexi_house
- lexi_overlook
- lexi_temple
- loop
- ndu
- nzp_warehouse
- nzp_warehouse2
- nzp_xmas2
- wahnsinn
- weapon_test

Do not enhance all simultaneously. Build reusable libraries from Nacht, then expand per family.

---

# 15. Things easy to forget — explicit checklist

- first-person arms/hands
- perk-drink hands
- grenade hands
- knife/melee pose
- magazines
- shell casings
- shell-drop sound
- bullet holes
- bullet impact particles
- muzzle smoke
- muzzle-light response
- hit marker
- points animation
- score spend animation
- use/buy prompts
- round digits/font
- perk icons
- power-up icons
- loading screen/map thumbnail
- skybox
- fog
- floor clutter
- trash bags
- tiny stones
- broken wood
- wire/cables
- light fixtures themselves
- radio model + static
- teddy
- Mystery Box glow
- floating weapon glow
- Box relocation FX
- power switch/handle
- perk bottles/cans
- perk purchase flash
- Pack-a-Punch rollers/gears
- teleporter arcs
- power-up models
- power-up sparkle
- barricade splinters
- doors/debris dust
- blood decals
- 3D gibs
- dog spawn FX
- dog variants
- material-specific footsteps
- metal impact audio
- environmental creaks
- distant ambience
- fire loop audio
- LODs
- texture memory
- particle count caps
- dynamic-light caps
- restart/map-change memory stability

If an item is not on this checklist, add it when discovered rather than silently implementing it ad hoc.

---

# 16. Shipping/performance rule

Enhanced does not mean maximum cost at all times.

Every expensive presentation feature needs:
- preset gate;
- sane cap;
- Classic fallback;
- map-restart stability test;
- horde stress test;
- Ray Gun + fire + explosion overlap test.

The goal is **visually modern enough to feel like a high-end mobile mode while the same APK still supports low-end hardware through Classic/Low**.


---

# 19. HUD elements verified in live QuakeC — do not forget

Direct inspection of `source/client/hud.qc` confirms that Enhanced also needs to account for:

- hit marker, including kill-state coloring/fade;
- dynamic crosshair;
- sniper-scope overlay;
- hold-breath prompt;
- revive progress bar;
- frag/grenade icon and secondary-grenade icon;
- perk icons and perk ordering;
- weapon-name fade;
- weapon-tier text colors;
- round-display art/animation;
- ammo readout;
- use/buy text;
- down/revive feedback.

Ready-made legal raw-material candidates already in the manifest:

- **Kenney Crosshair Pack** — 200 CC0 crosshairs, vector sources, outline/glow variants.
- **Kenney UI Pack** — 430+ CC0 interface pieces, vectors, fonts and UI sounds.
- **Kenney Game Icons** — 105 CC0 interface/game glyphs.

These are raw materials only. Enhanced should keep a coherent Zombies-style visual identity rather than looking like an untouched Kenney demo.

---

# 20. Additional ready-made map-family pools found

## Theatre / cinema

Fastest zero-modeling sources:

- **Theatre Stage and Backstage** — 53 CC0 GLB pieces; stage deck, proscenium, curtains/tabs, fly bars, counterweights, scenery flats, seating, pit rail, dressing-room and backstage props.
- **Cinema Multiplex and Foyer** — 43 CC0 GLB pieces; tiered flip-up seating, screen, projection booth and front-of-house props.
- **Abandoned Puppet Theatre and Prop Vault** — 51 CC0 pieces; abandoned curtain/proscenium/storage/repair detail.

These 3DAssets.dev sets disclose AI-generated geometry. Treat them as optional/fallback sources: visually inspect each selected piece and optimize it before use. They are especially useful when a hard-to-find theatre prop would otherwise require custom modeling.

Non-AI lightweight helpers:
- **LUKY_LAND 3D LL Collection** — CC0 projector, facility doors, security camera, locker, lantern, shelf, wooden blockade and other tiny props.
- **Lewie PSX Retro Props Pack** — 86 non-AI CC0 interior/horror props.

## Asylum / hospital

- **Free3DAsylum** — CC0 bed, wall, conduit, circuit breaker, fuse/fuse box, shelf, mattress and modular corridor.
- **DREAM_SEARCH_REPEAT Medical Pharmacy Pack** — free CC0/non-AI medical/pharmacy clutter with fictional branding.
- **Lewie PSX Retro Props Pack** — bathroom fixtures, bed, first aid box, cabinets, generator, panel box, etc.

## Swamp

- **Aredon LowPoly Reed** — CC0 FBX/OBJ reed vegetation.
- **Kenney 3D Nature Pack** — CC0 modular plants, rocks, trees, bushes and grass.
- 3DAssets.dev swamp/mangrove pieces are an optional CC0 fallback after triangle/visual review.

## Industrial / factory

- **chilly_durango Plumbing, Wiring & Machinery** — CC0 circuit breakers, fuses, switches, wires, pipes, valve, pump, turbine, generator and transformer.
- **3DModelsCC0 Industrial Packs** — barrels, gas cans, cylinders, cable drums, work lights, generator, locker, extinguisher and pallets.
- **Kenney Factory Kit** — 140+ optimized CC0 factory/warehouse objects.
- **Kenney Conveyor Kit** — 60+ CC0 models on a shared texture, strong for large industrial rooms.

The purpose is to reuse one coherent library across several maps rather than re-searching the internet for every room.


---

# 21. WWII / classic weapon replacement pool

Enhanced should not end up with modern zombies and environments while the first-person weapon mesh remains low-resolution.

## High-priority ready-made candidates

### One-pack baseline
**J.AkioHonda WW2 Low Poly Weapons Pack — CC BY**
Includes:
- M1 Garand + clip/ammo
- Thompson M1 + magazine/ammo
- PPSh-41 + magazine/ammo
- STG 44 + magazine/ammo
- M1911
- C96
- TT pistol
- knives
- Mk2 / F1 / stick grenades

The creator states that the models are their own and permits personal/commercial use with credit. This is an unusually efficient baseline library.

### Individual hero candidates

- **MP40 — Konstantinos.Simantiras**: ~9.4K tris, separated parts, reload + aim + run + walk animations.
- **MG42 — Konstantinos.Simantiras**: ~15.3K tris, separated parts, casing/bullet, reload + barrel-change animations.
- **BAR M1918A2 — Peanut_Butcher**: ~13.3K tris, game-ready and rigged.
- **BAR M1918 — Pippa**: ~6.8K tris, simple charging animation, companion magazine/round models.
- **Thompson M1A1 — TastyTony**: ~3.9K tris.
- **Winchester M1897 — Anick_Schwartz**: ~5.9K tris.
- **PPSh-41 — MaX3Dd**: ~4.2K tris, game-ready.
- **PPSh-41 — Zillious**: ~12.4K tris, separated magazine/trigger.
- **M1 Garand — Raymond**: ~13.7K tris.
- **M1 Garand — YieldingMist206**: ~11.1K tris with clip/bullets.
- **STG-44 — Observer3D**: ~25K tris; high-quality source that needs an Android LOD.

## Integration rule

Prefer models with:
1. separate magazine/bolt/trigger/charging-handle pieces;
2. existing FPS animations;
3. known triangle count;
4. 1K/2K source textures that can be downscaled by quality preset;
5. independent creator provenance.

Never use a model merely because Sketchfab says CC if the description identifies it as ripped from Call of Duty or another commercial game.

### Quality strategy

- Low: aggressive weapon LOD / 512 textures.
- Medium: lightweight hero mesh / 1K.
- High: full mobile hero mesh / 1K.
- Max: highest validated hero mesh / selective 2K.
- Classic: untouched NZ:P weapon presentation.

Weapon damage, fire rate, reload timing, ammo count and spread remain gameplay-authoritative unless separately fixing an actual gameplay bug.
