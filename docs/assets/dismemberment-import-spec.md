# Zombie rig + dismemberment import specification

Goal: make zombies support modern skeletal animation while allowing head/arms/legs to detach without turning the Android build into a CPU/GPU disaster.

## Required skeleton contract

Preferred humanoid bones:
- root / hips
- spine chain + chest
- neck + head
- upperarm/lowerarm/hand L/R
- upperleg/lowerleg/foot L/R
- optional jaw/eyes
- optional twist bones

Importer must build a canonical Xziel bone map so Quaternius, Mixamo, Unity/Fab humanoids and custom Blender rigs can retarget into one runtime state machine.

## Dismemberment zones

Minimum:
- head
- left/right upper arm
- left/right forearm
- left/right thigh
- left/right lower leg

Optional:
- jaw
- hand
- torso chunks

Each zone gets:
- bone ID
- hit capsule
- detach health threshold
- gib mesh reference
- stump/cap mesh or material
- blood emitter preset
- impulse multiplier
- gameplay capability mask (crawl, attack, bite, weapon-use)
- pooling policy

## Preferred authoring formats

Priority: GLB/glTF > FBX > Blend source > OBJ for static pieces.

Keep source rigs out of the shipping APK when the license requires embedded-only distribution. Convert to Xziel's runtime format and package non-extractable project data where the EULA requires it.

## Mesh strategy

Best candidate: model already split into skinned body-part meshes.

Fallback for CC0/derivative-friendly models:
1. duplicate body mesh in Blender;
2. split at shoulder/elbow/hip/knee/neck loops;
3. create interior stump caps;
4. transfer/clean vertex weights;
5. preserve the canonical skeleton;
6. generate intact and detached variants;
7. bake LODs;
8. export each piece with identical material conventions.

## Mobile budgets

Initial targets, to be validated on real Android devices:
- common zombie LOD0: roughly 8k–20k tris
- LOD1: 50–65% of LOD0
- LOD2: 20–35% of LOD0
- detached gib: aggressively simplified
- 1–2 material slots preferred
- 1k textures preferred for common bodies; reserve 2k for hero/close zombies
- pool gib meshes and particles
- cap concurrent detached physics bodies
- switch distant corpses to baked/static representations

These are engineering targets, not hard visual limits; profile from actual scenes.

## Animation state coverage

Every production zombie rig should eventually cover:
- idle variants
- walk/shamble variants
- sprint
- turn-in-place / directional turn
- climb/vault/barrier entry
- attack left/right/bite
- hit reactions by direction
- stumble
- headless continuation where supported
- one-arm state
- crawler locomotion
- crawler attack
- knockdown
- rise
- death variants
- ragdoll handoff

Quaternius Universal Animation Library 2 is a strong CC0 base because it explicitly includes zombie locomotion plus broader combat/parkour clips.

## Damage flow

hit -> resolve hit-zone -> health/armor -> reaction -> optional detach -> spawn pooled gib -> activate stump/blood -> update capability mask -> continue AI state.

Examples:
- leg loss => force crawler mode rather than immediate death
- arm loss => disable attacks requiring that arm
- head loss => usually lethal, but allow special zombie archetypes to override
- high-energy explosive damage => multiple-zone detach with strict pooled-particle budget

## Candidate priority

1. Studio New Punch free body-parts zombies — realistic and already split; verify live marketplace EULA.
2. Quaternius CC0 zombies — safest for modification; create our own segmented body-part derivative.
3. Other CC0/CC-BY humanoid zombies found on OpenGameArt/itch/Sketchfab after topology/rig review.
