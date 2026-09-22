# SANCTUM OF ASH — Character / Creature Roster v1
Status: AUTHORITATIVE MODEL HANDOFF
Companion specs:
- `docs/SANCTUM_OF_ASH_MAP_BIBLE_V2.md`
- `docs/SANCTUM_BLENDER_AUTHORING_CONTRACT.md`
- `assets/sanctum/characters/model_manifest.json`
- `tools/sanctum_models/build_neutral_proxies.py`

## Source set

The user supplied **13 reference images** in the current Sanctum design pass. They cover **10 unique model/gameplay concepts** plus phone-view duplicates used as visual confirmation.

Canonical concepts:

1. Choir Wretch
2. Bell Ringer
3. Censer Brute
4. Reliquary Horror
5. Grave Sexton
6. Penitent Deacon
7. Stained Shade
8. Waterbound Child
9. Lost Child
10. La Llorona

Additional reference:
- La Llorona Random Encounter System gameplay blueprint.
- phone-view duplicate of Lost Child sheet.
- phone-view duplicate of La Llorona sheet.

Do not reduce this roster to only the final three uploads.

---

## Shared construction rules

All production models should use meter scale and clean, modular separation.

### Shared adult church humanoid family
Used where proportions permit:
- Choir Wretch
- Bell Ringer
- Grave Sexton
- Penitent Deacon
- Stained Shade

Use one compatible humanoid skeleton contract so locomotion, hit reactions and common animation can be shared. Individual silhouette pieces remain separate.

### Shared heavy humanoid family
- Censer Brute
- Reliquary Horror may share selected deformation conventions but is a boss-scale custom rig.

### Shared child family
- Lost Child
- Waterbound Child

### Separate hero rigs
- La Llorona
- Reliquary Horror

---

## 1. Choir Wretch

Approx. height: **1.75 m**.

Identity:
- dead choir / clergy-adjacent undead;
- distressed layered ivory and faded red choir vestments;
- screaming/open-jaw silhouette;
- rope belt, crosses, old shoes;
- thin corpse proportions.

Modular pieces:
- body/skin;
- head + removable lower jaw;
- outer choir robe;
- inner robe;
- shoulder cape/collar;
- rope belt;
- crosses/metal props;
- hair/veil if used.

Damage sockets/states:
- jaw/lower-face damage;
- headless;
- left arm missing;
- right arm missing;
- both arms missing;
- left leg missing -> stumble;
- crawler/hip-up;
- torso-only survivor.

Gameplay placement:
- nave;
- choir/altar lanes;
- tower-adjacent routes.

Do not make it the only clergy silhouette.

---

## 2. Bell Ringer

Approx. height: **1.80 m**.

Identity:
- church servant / bell attendant;
- ash blue-gray outer cloth + dirty ivory layers;
- small bell prop;
- rope/twine elements;
- old leather footwear.

Modular pieces:
- hood;
- robe layers;
- bell prop;
- rope/twine;
- arms/legs with clean damage caps.

Damage states:
- headless walker;
- left/right arm missing;
- left/right leg missing -> stumble;
- foot missing;
- crawler;
- lower-half state;
- torso-only.

Gameplay placement:
- tower stairs;
- ringing chamber;
- upper church routes.

---

## 3. Censer Brute

Approx. height: **2.80 m**.

Identity:
- heavy enemy;
- oversized hooded penitent silhouette;
- large chain-held censer;
- layered heavy cloth and crosses;
- thick rope belt.

Rig:
- shared heavy-enemy skeleton family.
- weighted cloth simulation kept simple/bounded for mobile.

Separate props:
- censer;
- chain;
- crosses;
- belt pieces.

Damage states:
- headless;
- weapon arm missing;
- off arm missing;
- left/right leg missing -> stumble;
- foot missing;
- kneeling collapse;
- lower-half state;
- torso-only.

Gameplay:
- special/heavy wave pressure;
- nave/lower service/tower transition depending encounter tuning.

---

## 4. Reliquary Horror

Approx. height: **4.50 m**.

Identity:
- boss-scale cathedral monster;
- body fused with a shrine/reliquary back structure;
- crosses, chains, candles, censers and relic architecture;
- huge corpse hand silhouette.

Rig:
- unique boss skeleton.
- back shrine is a modular assembly, not one fused deformation mesh.

Separate components:
- body;
- shrine/back assembly;
- arms;
- chains;
- censers;
- candles;
- relic/cross pieces;
- robe panels.

Boss damage stages:
1. intact;
2. left arm destroyed;
3. right arm destroyed;
4. shrine/back break stage;
5. torso rupture stage;
6. lower-half collapse;
7. crawl/drag enraged;
8. final collapse.

Use as a model concept independent of Bell Warden unless narrative explicitly merges/reassigns it later.

---

## 5. Grave Sexton

Approx. height: **1.90 m**.

Identity:
- cemetery/grave caretaker undead;
- dark worn coat and apron;
- key ring;
- shovel / grave hook;
- heavy worker silhouette.

Separate props:
- shovel;
- grave hook;
- key ring;
- belt/pouch.

Damage states:
- headless;
- weapon arm missing;
- off arm missing;
- both arms missing;
- leg damage/stumble;
- foot missing;
- crawler;
- torso-only.

Gameplay placement:
- courtyard/cemetery;
- exterior service path;
- occasional lower service route.

---

## 6. Penitent Deacon

Approx. height: **1.85 m**.

Identity:
- elite/support clergy undead;
- faded burgundy stole/hood;
- relic lantern;
- rope belt and chain/cross details.

Separate props:
- hood;
- outer robe/stole;
- under robe;
- lantern;
- chains;
- rope;
- crosses.

Damage states:
- headless;
- arm/leg variants;
- both arms missing;
- crawler;
- lower-half;
- torso-only.

Gameplay placement:
- nave/altar;
- office;
- tower progression as a rarer support silhouette.

---

## 7. Stained Shade

Approx. height: **1.85 m**.

Identity:
- spectral nun/church apparition enemy;
- pale translucent cloth;
- stained-glass blue/cyan/magenta/amber shards and emissive accents;
- floating/ghostly lower silhouette.

Construction:
- shared humanoid skeleton where practical;
- outer veil as separate transparent mesh;
- inner robes;
- stained-glass accents as separate emissive meshes;
- crucifix/rope props;
- spectral material pass separate from opaque skin.

States:
- intact shade;
- headless;
- left/right arm missing;
- lower-half fade;
- crawler;
- torso-only drift;
- broken-glass dissipate death state.

Gameplay:
- special/spectral enemy, not the passive Praying Nun.
- can use visibility disruption/mobility behavior rather than simply more HP.

---

## 8. Waterbound Child

Child-scale; use the same base child rig family as Lost Child.

Identity:
- soaked child apparition;
- wet black hair;
- waterlogged light dress;
- wet skin/water sheen;
- mud/silt;
- mist around feet.

Separate systems:
- cloth layers;
- hair cards/curves;
- mist VFX;
- water drip/splash accents.

States:
- still standing;
- quiet sobbing;
- false comfort / approach;
- sudden scream;
- aggressive lunge;
- low crawl;
- mist vanish.

Gameplay:
- La Llorona child encounter variant.
- may be neutral/hostile according to encounter state.
- should not be confused with normal zombie child combat unless explicitly enabled.

---

## 9. Lost Child

Approx. height: **1.10 m**; visual target roughly age 7–9.

Identity:
- wet, sorrowful child apparition;
- distressed ivory dress;
- wet dark hair;
- doll and rosary props;
- bare feet/mud/water.

Suggested LOD targets from sheet:
- LOD0 ~6.5k triangles;
- LOD1 ~3.2k;
- LOD2 ~1.2k.

Separate components:
- body;
- dress/underskirt/lace/collar;
- hair cards;
- cloth doll;
- rosary.

Encounter states:
- shy watcher;
- crying still;
- guiding gesture;
- gift child;
- mischief lure;
- panic run;
- fading apparition.

Gameplay:
- La Llorona encounter child variant;
- supports non-hostile, neutral and rare deceptive behaviors.

---

## 10. La Llorona

Approx. height: **1.70 m**.

Identity:
- hero supernatural presence;
- long wet black hair;
- layered waterlogged ivory/lace dress;
- corpse-pale wet skin;
- black tear streaks;
- rosary/cross;
- mist/water lower-hem treatment.

Suggested LOD targets from sheet:
- LOD0 ~32k triangles;
- LOD1 ~16k;
- LOD2 ~8k;
- LOD3 ~4k.

Modular pieces:
- body/head;
- dress base;
- lace/veil layers;
- hair cards;
- rosary/cross;
- mist VFX.

Core event states:
- calm weeping;
- beckoning;
- benevolent gift;
- cursed warning;
- enraged hunt;
- vanishing mist.

Normal Sanctum use:
- passive spatial audio/presence remains the default;
- visual appearance is an authored encounter, not a permanent collider;
- apparition anchors have no collision/nav blocker unless a specific hostile event explicitly creates an actor.

---

## La Llorona random encounter blueprint

The supplied encounter reference defines a random runtime choice instead of one predictable morality path.

High-level loop:
1. apparition/child appears at an authored Sanctum anchor;
2. player may interact or ignore;
3. runtime chooses benevolent, malevolent or testing/neutral outcome;
4. the player cannot memorize one universally safe response.

Possible child variants shown in the source sheet:
- Lost Child;
- Guiding Child;
- Mischief Child;
- Waterbound Child.

This system must remain optional to the core survival loop and must not create unavoidable punishment from invisible/random state.

---

## Non-Blender handoff

The repository includes a standard-library Python generator:
`tools/sanctum_models/build_neutral_proxies.py`

It emits engine-agnostic OBJ/MTL blockout models and JSON contracts for the ten canonical concepts. These are **scale/part/rig scaffolds**, not final production sculpts.

Purpose:
- give a non-Blender agent exact scale and part segmentation;
- establish pivot/socket names;
- provide neutral importable geometry;
- make GLTF/FBX/USD generation easier in another tool;
- keep gameplay IDs independent of DCC software.

Production meshes should replace proxy geometry while preserving the exported names/contracts.
