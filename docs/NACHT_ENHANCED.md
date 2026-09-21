# Nacht: Enchanted Lab

Nacht: Enchanted Lab is a separate development/practice map. It is not a
Classic/Enhanced toggle layered over stock Nacht.

## Runtime identity
- Stock comparison map: `ndu`
- Xziel laboratory map: `ndu_enchanted`
- Menu location: User Maps
- Stock `ndu` must never load Lab-only materials, audio, FX or future zombie
  replacements.
- Loading `ndu_enchanted` automatically enables the Lab runtime profile.

## Why it is separate
The Lab lets Xziel repeatedly experiment with modern mobile presentation while
keeping a known-good stock baseline. We can aggressively change materials,
lighting, particles, audio, props, zombie models, animation feel, gore and
touch presentation without turning stock Nacht into a moving target.

## Enhancement passes
1. Environment materials: concrete, damaged plaster, metal, wood barricades,
   rubble and exterior treatment.
2. Props: sandbags, crates, debris, lamps, cables, barrels and Mystery Box
   presentation.
3. Atmosphere: bounded dust/smoke/embers/sparks, fog and lightning.
4. Lighting: authored BSP lighting plus bounded dynamic lights.
5. Zombies: real Lab-specific model/animation replacements with stock hitbox,
   damage and gameplay contracts preserved.
6. Audio: Lab-only positional ambience and original/redistribution-safe cues.
7. Gore/destruction: stronger feedback without changing scoring or rules.
8. Performance: Android-first culling, particle/light caps, texture/model
   budgets and fallbacks.

## Asset namespace rule
New Lab character/model assets must use Lab-specific paths instead of silently
overwriting stock `models/ai/*` resources. This guarantees that stock maps stay
stock while the Lab can evolve independently.

## Release rule
This duplicated Nacht layout is a development/reference derivative. The
eventual original Xziel game map must use new geometry, art, naming and content.
We keep the engineering lessons and pacing/adrenaline lessons, not the copied
map identity.
