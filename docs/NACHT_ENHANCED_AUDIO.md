# Nacht Enhanced — Audio Pass

Enhanced visuals ship with an equally deliberate audio pass. Audio is not optional polish.

## Layers
- Exterior weather: cold wind bed, gusts through broken openings, distant thunder.
- Structure: timber groans, metal stress, loose debris, occasional distant impacts.
- Electrical: lamp buzz, failing fluorescent hum, intermittent sparks/arcs.
- Barricades: plank placement, wood strain, zombie hits, splinter/break layers.
- Zombies: distant exterior calls, close vocal layers, footsteps, cloth/body movement, impacts and dismemberment.
- Weapons: muzzle report, mechanical action, casing/debris where appropriate, impact-by-surface, reload/empty feedback.
- Player: footsteps by surface, landing, sprint/slide/dive movement, hurt/down/revive cues.
- Interactions: door/opening purchases, wall weapon, mystery box, power/equipment and UI confirmation.
- Round state: start/end stingers and tension beds remain readable over ambience.
- Spatial horror: one-shots are positional; global ambience stays subtle enough to preserve enemy localization.

## Runtime rules
- Classic uses stock audio unchanged.
- Enhanced audio is active only for `ndu` while `xziel_nacht_enhanced != 0`.
- Never replace gameplay-critical cues with quieter or ambiguous sounds.
- Cap simultaneous decorative one-shots and use distance attenuation.
- Random ambience uses cooldowns and variation; never trigger every frame.
- Android sources should be mono for positional SFX where practical; music/large ambience may be stereo.
- Normalize conservatively and leave headroom for weapons/zombies.

## Asset/licensing gate
All new sounds need manifest entries before packaging: source URL, author, license, redistribution, commercial-use permission, role, original filename, converted filename and modifications. Extracted/reference audio must stay outside the commercial-safe bundle.

## Existing engine hooks confirmed
NZ:P already provides `ambient_generic`/FTE `ambientsound`, attenuation radii, looping/start-silent/non-looping flags, normal `sound()`, and stock barricade sounds. Enhanced Nacht should reuse these native paths rather than invent an Android-only mixer.
