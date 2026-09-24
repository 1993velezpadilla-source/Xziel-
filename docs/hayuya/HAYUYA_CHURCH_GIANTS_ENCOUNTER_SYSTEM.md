# HAYUYA Map — Church Giants Encounter Director v1

**Branch:** `feature/hayuya-church-giants-encounter-v1`  
**Parent:** HAYUYA Map World Brain  
**Status:** design + compiler integration foundation

## Intent

The three church Giants are not ordinary special-enemy spawns. They are recurring presences whose story begins through the map before the full character appears.

The reusable loop is:

`signal -> suspicion -> glimpse -> manifestation -> interaction -> consequence -> afterimage -> cooldown`

Not every encounter uses every phase. The important rule is that **appearance is not equivalent to combat**.

## Why this is feasible without hundreds of bespoke cinematics

HAYUYA should compose encounters from reusable pieces:

- pre-authored encounter anchors in rooms, doorways, balconies, stained-glass sightlines, confessionals and altar spaces;
- short actor clips such as idle, slow walk, turn, look, subtle gesture, sit, stand and prop interaction;
- procedural head/look layers and secondary cloth motion;
- audio cues with real spatial sources or an explicitly authored supernatural source;
- lighting-group events;
- prop state changes;
- door/route state;
- serialized story flags;
- safe occlusion points for repositioning;
- a deterministic variant selector.

This means a new encounter can often be authored as data instead of requiring a new long animation.

## The three presences

### 1. The Bell Mourner — 2.25 m

Role: distant warning, impossible caller, visual foreshadowing.

The player may hear a bell before there is any visible character. Later the Mourner can cross a stained-glass sightline, stand at the far end of the nave, or leave a changed door/prop state behind.

He should normally **observe and withdraw**, not immediately attack.

### 2. The Procession Warden — 2.05 m

Role: moving ritual route and uncertain guide.

Candles can ignite in order before the Warden appears. Once visible, he follows an authored procession spline. The player can follow, keep distance, leave, or attempt to cross the route.

The route may reveal a story location, alter navigation, or use a rarer misdirection branch. The behavior remains deterministic for co-op.

### 3. The Confessional Keeper — 1.95 m

Role: memory, consequence and player-history interaction.

The first visit may contain only sound and movement from the confessional. A later visit can reveal the Keeper seated inside. Future variants can select questions or consequences from serialized match-history flags rather than arbitrary random dialogue.

He can change future encounter weighting or world state without forcing combat.

## The shared payoff

After the player has separately encountered all three, a rare event can place the trio at altar anchors as a still tableau. A short authored light transition ends the sighting only after the characters are safely occluded.

This is not a random scare. It confirms that the three presences belong to one larger story system.

## No-visible-pop-in rule

A major presence must never materialize in an unobstructed player's view because the runtime simply spawned it.

Allowed reveal/reposition strategies include:

- preload before reveal;
- actor crosses from behind geometry;
- doorway or corner traversal;
- stained-glass or silhouette layer;
- fully occluded relocation;
- authored light transition combined with visibility validation;
- streamed anchor prepared before the player can see it.

If none of those conditions is available, the encounter waits.

## Animation strategy

The minimum reusable library should cover:

`idle_a, idle_b, slow_walk, turn_45, turn_90, look_target, gesture_subtle, sit_or_rest, stand_from_rest, hold_or_ring_prop, enter_occlusion, exit_occlusion`

Animation events can expose markers for footsteps, prop contact, bell cues, light triggers, voice cues, interaction windows and safe visibility swaps.

Root motion is optional per clip. Long bespoke cinematics are optional, not foundational.

## Co-op/runtime contract

Encounter choice and state are host/server authoritative.

The runtime must serialize:

- selected encounter;
- variant seed;
- current phase;
- actor anchor;
- route/spline progress when relevant;
- prior-contact flags;
- world consequences;
- cooldown;
- interaction state.

Late joiners receive the existing state instead of independently rolling a new event.

## Rare-event philosophy

Rare variants are weighted and match-seeded, not uncontrolled random scripting. A rare event can depend on previous choices and still be exactly reproducible for debugging.

Rare variants must never be required for core progression.

## HAYUYA Map handoff

The World Brain owns the **meaning and composition** of the encounter. HAYUYA Lighting owns lighting intent. The runtime/compiler owns efficient execution.

Expected Xziel handoff includes:

- XMAP logic links;
- actor anchors;
- room/portal/streaming metadata;
- event state;
- animation markers;
- audio events;
- lighting-group cues;
- route changes;
- story flags.

The result should make players ask whether an event was scripted specifically for them, while remaining deterministic, testable and mobile-safe.
