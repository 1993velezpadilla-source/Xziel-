# Sanctum immersive audio / weather / breakables pass

This pass turns the existing Xziel systems into a reusable horror-atmosphere layer without replacing gameplay authority or adding fragile physics everywhere.

## Design rule

Interaction stays deterministic. Doors, barricades, windows and breakables expose stable state; presentation reacts to that state. No cosmetic rigid body is allowed to become gameplay authority.

For wind-driven motion, only cosmetic church shutters/windows use WindowAtmosphereSystem. Buyable gameplay doors remain controlled by DoorSystem, so a gust cannot accidentally open a route, move collision, or break zombie navigation.

## Runtime mapping

| Event | Presentation | Audio cue |
| --- | --- | --- |
| Door purchase starts | Rotate real wood-door leaf around authored hinge from DoorFrame.openProgress | DoorWoodOpenStart |
| Door crosses mid travel | Continue smooth hinge animation | DoorWoodCreak |
| Door reaches fully open | Settle/latch animation | DoorWoodOpenStop |
| Zombie tears a plank | Detach authored plank presentation + short splinter burst | BarricadePlankRip |
| Final plank removed | Larger fragments/dust; existing barricade authority opens traversal | BarricadeBreach |
| Player repairs | Plank presentation returns through authored attach animation | BarricadePlankRebuild |
| Wood/stone footsteps | Material-tagged randomized one-shot | FootstepWood / FootstepStone |
| Wet surface | Wet roughness response + small splash where appropriate | FootstepWetWood / FootstepWetStone |
| Wind on cosmetic window | Bounded hinge oscillation; no gameplay collision mutation | WindowRattle / WindowWoodCreak / WindowSlam |
| Lightning | Existing EnvironmentSystem visual flash | LightningCrack, then delayed thunder |
| Thunder | Delay = strike distance / 343 m/s | ThunderNear / ThunderMid / ThunderFar |
| Rain | Existing bounded particle budgets + precipitation occlusion | RainExteriorLoop / filtered RainInteriorLoop |
| Puddles | Decal/plane + wet roughness; no mobile fluid simulation | Wet footstep/splash layer |
| Souls / distant entities | Spatial source through AcousticGraph room/portal occlusion | SoulWhisper |
| Grenade | Weapon/gameplay event remains authoritative | pin / throw / explosion layers |

## Top hero model

Poly Haven Large Castle Door is the first hero-door choice: weathered arched double wood, iron straps, rivets and ring handles, around 13K triangles. It is CC0. Use 1K or 2K textures on mobile, preserve the higher-quality source offline, set hinge pivots in the church scene, and drive rotation from DoorFrame.openProgress.

## Top CC0 audio in this pass

1. 75 CC0 breaking/falling/hit SFX — first choice for plank ripping, break impacts, glass and debris.
2. 100 CC0 SFX #2 — broad first-pass library for doors, footsteps, glass, thunder, water and wood.
3. Rain and thunders — dark rainy ambience bed.
4. Different steps on wood/stone/leaves/gravel/mud — surface footsteps.
5. Ghost Monster Voice Moaning & Growling and Voices of Madness — spatial soul/whisper layers.
6. Wind whoosh loop — cheap continuous exterior wind.
7. Muffled Distant Explosion — low-frequency distant boom / grenade-tail layer.

Do not force one recording to do the whole job. A convincing grenade, plank break or thunder should be layered from transient, body and tail, with room reverb/occlusion applied by Xziel.

## Mobile policy

- Low / Medium / High / Ultra keep the existing Xziel rain and audio voice budgets.
- Continuous ambience is virtualized when inaudible.
- Player weapons, nearby zombie threat cues and authored horror stingers outrank distant ambience.
- Puddles are decals/material response, not simulated fluid.
- Glass breakage uses authored fragments/particle bursts with strict caps; no unbounded shard rigid bodies.
- Window wind motion is deterministic and bounded.
- Rain inside the church uses filtered/occluded exterior ambience through AcousticGraph rather than a second always-on full-quality source.

## Licensing / acquisition

Only CC0 entries in the manifests are auto-downloaded by scripts/fetch_sanctum_immersive_assets.py. The GitHub Action packages them into a downloadable workflow artifact and writes SHA-256 hashes to ASSET_LOCK.json.

Sonniss GDC bundles remain useful production candidates, but raw files are not mirrored in this repository because the current license allows synchronization into finished games while restricting raw-library redistribution. If later used, keep them in a private licensed source cache and package only game-ready use permitted by that license.

Poly Haven assets are CC0. The downloader uses Poly Haven's public API with an identifying User-Agent and this project documentation identifies Poly Haven as the API source.

## C++ integration added

The reusable layer is xziel/sanctum_immersion.hpp:

- SanctumSoundEventRouter maps DoorFrame, BarricadeFrame and material footsteps into stable audio cue IDs.
- ThunderAudioScheduler implements speed-of-sound delay.
- WindowAtmosphereSystem supplies bounded cosmetic wind motion and rattle/creak/slam events.

The Android audio mixer should bind cue IDs to files from ASSET_LOCK.json. Keep cue-to-file selection data-driven so every future map can reuse the system with a different sound bank.
