# Nacht: Enchanted Lab — Quake/Vril practice map

This branch keeps the work on the NZ:P/Vril/Quake lineage. It does not use the
separate Xziel Vulkan engine.

## Runtime identity

- Stock comparison map: `ndu`
- Enchanted practice map: `ndu_enchanted`

The APK stages a second BSP entry plus Nacht's waypoint and Mystery Box
metadata. That gives the experiment its own playable map identity instead of
mutating the stock map.

## Enchantment scope

The target is the entire experience: walls, plaster, floors, stairs, ceilings,
metal doors, wood, barricades, rubble, lamps, Mystery Box presentation, fog,
fire, sparks, lightning, touchscreen HUD skin, zombie models/animation,
crawlers, limb loss, decapitation, positional horror audio, round stingers and
game-over presentation.

## Quality rule

Do not intentionally crush art to legacy Quake texture quality just because
the runtime is Quake-derived. Use Vril's external texture/model paths and solve
performance with mipmaps, culling, bounded FX and optional fallbacks.

## Release rule

This duplicated Nacht layout is a development/reference derivative.
`XZIEL_INCLUDE_NACHT_ENCHANTED=0` removes it from an original public package.
The eventual Xziel release map must be redesigned in geometry, art, naming and
content while preserving the pacing lessons: tight sightlines, escalating
access, window pressure and oppressive bunker atmosphere.
