# Sanctum of Ash — native Xziel migration v1

This branch starts the first-map migration on the standalone Xziel engine.

## Hard boundary

Sanctum gameplay/atmosphere work added here must not depend on Quake BSP,
QuakeC, Vril, GL4ES, or the NZ:P runtime. The legacy Android harness remains
useful only as historical/reference evidence while native Xziel reaches full
map/asset parity.

The shipping path for Sanctum is:

1. validated church source asset / authored derivative
2. native Xziel mesh + material import
3. native collision/navigation data
4. native MapRuntime / HordeDirector gameplay
5. native AcousticGraph / AudioScenePlanner ambience
6. Vulkan renderer + AAudio Android presentation

## BO1-style tension rules carried into Sanctum

The map should create pressure through vulnerability, readable but dangerous
spaces, silence, distant audio, and uncertainty rather than HUD spam or constant
jump scares.

Passive horror presences are deliberately not global 2D sounds. La Llorona and
the Nun are spatial sources. Their normal passive beds can be heard from far
away when the acoustic path is open, with room/portal occlusion, low-pass
filtering, distance attenuation, and local reverb. Discrete cries/prayers are
sparse and randomized so they signal presence without becoming repetitive.

Passive timing defaults:

- La Llorona: one vocal event roughly every 12–22 seconds.
- Nun: one prayer/whisper roughly every 18–32 seconds.
- Hostile/chase state may shorten those ranges, but passive state never uses
  the chase cadence.
- Passive emitters are non-critical voices and must never steal player weapon,
  UI, or true scare-stinger priority.

## Native acoustic zones

The first graph follows the map bible progression:

Fallen Courtyard -> Nave -> Office -> Office Corridor -> Boiler Room

and

Nave -> Tower Stairs -> Ringing Chamber -> Clock Chamber -> Roof Chamber ->
Tower Top

Each area has its own reverb/absorption profile. Doors later drive portal
openness directly, so opening a route changes what the player can hear before
they physically reach the next room.

## What is implemented in v1

- Sanctum zone identifiers and names.
- Native acoustic-room and portal graph.
- Native passive-presence model for La Llorona and the Nun.
- Long-range looping presence beds with distance + occlusion.
- Sparse randomized passive cry/prayer events.
- Separate passive vs hostile cadence.
- Host smoke test that verifies distant audibility and anti-spam behavior.
- No Quake/Vril dependency in this module.
- Standalone XZSM v2 parser now lives in Xziel itself; the Blender-exported church mesh can be validated without any Quake/Vril reader.
- Sanctum gameplay tuning profile locks the vulnerable start, longer quiet inter-round beat, restrained horror presentation, and hidden-secret/no-marker defaults.

## Next native map step

The validated church mesh format is now readable by native Xziel. The next renderer step is to upload its batches into dedicated Vulkan vertex/index buffers and bind the referenced albedo textures directly. Do not convert the map back into BSP. Collision and navigation should be authored as simplified native data per zone rather than using the photogrammetry mesh as gameplay collision.
