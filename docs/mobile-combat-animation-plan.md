# Xziel Mobile Combat + Animation Upgrade Plan

## Inventory decision

Preserve the recognizable round-based Zombies weapon economy:

- 2 normal weapon slots by default.
- Mule Kick unlocks the 3rd normal weapon slot.
- Ray Gun, Ray Gun Mk II, Wunderwaffe/Tesla-style weapons and other Wonder Weapons stay in normal weapon inventory. They do not consume a separate "special ability" slot.
- Unlimited-pistol mode changes reserve-ammo behavior only. It never creates a hidden third weapon slot.

This avoids inventing a new inventory rule that would conflict with classic Zombies behavior.

## Mobile-only Special slot

Add a separate single-slot **SPECIAL** control for ability/equipment content that is intentionally outside the classic firearm inventory.

Examples:
- K9 / attack-dog summon.
- Temporary flamethrower/Purifier-style ability.
- Temporary heavy weapon / Death-Machine-style ability.
- Deployable or other future operator-style ability.

Rules:
- One active Special at a time.
- Hidden when no Special is owned/charged.
- Does not replace Weapon 1/2/3.
- Wonder Weapons are not Specials.
- Grenade and melee retain their own controls.
- New Specials must expose deterministic charge/cooldown/state to the HUD instead of using ad-hoc cvars.

## Animation modernization target

Do not replace physics, collision, weapon timing or QuakeC gameplay with animation assets. Animation is presentation layered over the existing authoritative movement/weapon state.

Required states:
- idle
- walk forward/back/strafe
- run
- sprint
- jump takeoff / airborne / land
- crouch enter / idle / move / exit
- prone enter / move / exit where supported
- firearm idle
- pistol firing
- revolver firing
- rifle/SMG firing
- shotgun firing
- heavy weapon firing
- reload by weapon family
- weapon swap
- melee
- damage/downed/revive where available

## Recoil design

NZ:P already contains per-weapon recoil values. Preserve those gameplay values.

The 2026 presentation pass should add a separate visual recoil layer:
- short weapon-model kick on discharge
- spring return to rest
- weapon-family profiles
- stronger impulse for revolvers, shotguns and high-caliber rifles
- softer impulse for SMGs and low-recoil handguns
- no fake ballistic recoil for energy/ray weapons unless their original animation calls for it

The visual recoil layer must not modify bullet spread, server aim, fire cadence or authoritative view angles.

## Open asset candidates

Prefer assets with clear CC0 terms and source files suitable for retargeting.

1. Quaternius Universal Animation Library / Universal Animation Library 2
   - humanoid locomotion, sprint, crawling, combat/gun and other actions
   - FBX / GLB / Blend
   - pack pages identify the libraries as CC0
   - https://quaternius.com/packs/universalanimationlibrary.html
   - https://quaternius.com/packs/universalanimationlibrary2.html

2. Quaternius Animated Guns / OpenGameArt mirror
   - pistol, revolver, shotgun, sniper and other animated guns
   - CC0 listing
   - https://opengameart.org/content/low-poly-animated-guns

3. OpenGameArt Low Poly FPS Rifle and Hands
   - rifle + first-person hands + shoot animation
   - CC0
   - https://opengameart.org/content/low-poly-fps-rifle-and-hands

4. Kenney CC0 animated character packs
   - useful fallback/reference rigs
   - https://kenney.nl/assets/animated-characters-protagonists
   - https://kenney.nl/assets/animated-characters-retro

## Quake MDL conversion path

Vril/NZ:P uses classic frame-based Quake MDL content in this path. Imported skeletal animations therefore need to be retargeted and baked to vertex frames before replacing runtime player assets.

Open-source conversion candidates:
- khreathor/mdl-for-blender (Quake MDL import/export)
- cmdrf/quake-export (command-line MDL export intended for automated build environments)

Do not make an imported FBX/GLB a hard build dependency until an APK smoke test verifies:
- model loads on Android GLES path
- frame interpolation remains correct
- frame count/index mapping matches QuakeC
- memory use is acceptable
- multiplayer third-person animation remains synchronized

## Rollout order

1. Preserve inventory semantics (done).
2. Build Special-slot protocol/state/UI, hidden until used.
3. Add visual recoil layer using existing weapon IDs and recoil timing.
4. Retarget CC0 locomotion set to a test player model.
5. Bake to MDL and test walk/run/sprint/crouch/jump/land only.
6. Add weapon-family upper-body firing/reload clips.
7. Replace production player animation only after side-by-side Android smoke testing.
