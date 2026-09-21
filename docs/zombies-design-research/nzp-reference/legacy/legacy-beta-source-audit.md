# Legacy NZ:P Beta Source Archive Audit

Updated: 2026-09-20

This audit covers the **two original preservation packs** linked from the BCDeshiG beta-map archive research. Both archives were retrieved through their original Google Drive links and fingerprinted before analysis.

## Archive fingerprints

- `betaARC2.7z` — 63,782,742 bytes — SHA-256 `a63bee0fe7d5f52e3acbacfe650869668ae7a8c01a0412a4eae6df490f7e851b`
- `Beta Archiev5p.7z` — 130,790,409 bytes — SHA-256 `bd74f07509a12f1294657c8a15cfc31a570847f2021fa3e2f6e5d293e65cd776`

## Editable source recovered

**31 textual `.map` sources** were recovered:

`bigj`, `bunker`, `facility`, `five`, `four`, `fourtex`, `gunrange`, `jungle`, `junglerelease`, `mansion`, `moonagain`, `moonredux`, `moonrelease`, `newmoon`, `random`, `road`, `room`, `sector 7`, `sectorz`, `subway`, `summit`, `tele`, `test`, `themall`, `themoon`, `themoontextured`, `thenewmoon`, `theroom`, `train`, `way`, and `Research_Center_psp`.

The archive also contains an old `nzp.fgd`, old Quake definitions, readmes, map-pack notes and other historical mapper material.

## Important result: names do not imply quest fidelity

The source disproves a dangerous assumption: a filename such as **Five** or **Moon** does not mean a complete Treyarch recreation exists.

### `five.map`

- 2 top-level entities
- no target graph
- no quest primitives
- effectively a map shell/prototype in this source snapshot

### Moon family

Recovered revisions include:
- `moonagain`
- `moonredux`
- `moonrelease`
- `newmoon`
- `themoon`
- `themoontextured`
- `thenewmoon`

These are largely layout/survival iterations: zombie windows/spawns, doors and mystery-box spots. No source evidence in these revisions establishes the original Treyarch Moon main quest.

`themoon` and `themoontextured` contain a legacy `trigger_command` with `sv_gravity 300`, showing a low-gravity experiment. That is **environmental recreation**, not Moon quest fidelity.

### `facility.map`

This old archive file has only 2 top-level entities and should **not** be confused with the much newer community **Facility V2** release whose key-card/Ray-Gun/PAP quest systems are separately researched.

## Highest-value legacy sources

### `fourtex.map`

Verified systems:
- Pack-a-Punch entity
- power switch
- two mystery-box teleport spots
- multiple purchasable doors
- projector-named door
- Ray Gun display/model
- a one-step Easter egg:
  - `func_button -> target=easter1`
  - `trigger_command targetname=easter1 -> play2 sound/radio/115`

Normalized pattern:

`Shoot/activate hidden button -> dispatch named event -> play secret audio`

This is a genuine legacy Easter-egg interaction, but not a multi-stage quest.

### `Research_Center_psp.map`

Verified systems:
- four purchasable doors
- mystery box
- Pack-a-Punch
- power switch
- standard zombie/path/window graph

This is useful as an early compact **full survival-system** layout, not as a deep Easter-egg implementation.

### `bigj.map`

Verified systems:
- mystery box
- 8 NZ:P doors
- ordinary `func_door`
- Pack-a-Punch
- radio
- 9 wall-buy weapons

Three door targets (`a`, `q`, `r`) are unresolved in the recovered textual source. Preserve that as historical evidence rather than silently inventing missing destinations.

Public ModDB evidence independently confirms **Bigj** was one of the four user maps distributed in the 2011 NZ:P Map-Pack WAR.

### `mansion.map`

Primarily survival progression:
- purchasable doors
- door targets that activate later zombie spawn groups
- path/window graph

Useful precedent for traversal -> AI-spawn activation, not a quest chain.

### `bunker.map`

Primarily compact survival setup:
- two purchasable doors
- wall buys/models
- zombie windows/spawns

No hidden multi-step chain found in this source revision.

### `tele.map`

A tiny test map that directly demonstrates:

`trigger_teleport target=t2 -> info_teleport_destination targetname=t2`

Useful for historical teleporter semantics, not a Zombies quest.

## Historical FGD findings

The legacy `nzp.fgd` exposes old mapper concepts such as:

- `trigger_command` — triggered client command
- `info_command` — triggered server command
- `item_pap`
- `mystery_box`
- `mystery_box_tp_spot`
- `power_switch`
- `func_door_nzp`

This is valuable because some archived maps predate the modern `game_counter`, `trigger_interact`, modern teleporter and quest tooling used by current NZ:P.

## Generation conclusion

The archive shows a clear evolution:

**early NZ:P:** doors + spawn activation + power/PAP/box + command-trigger secrets  
→ **later NZ:P:** reusable counters, interact nodes, target fan-out, delayed/round-delayed relays, songs, world-state changes and complex side quests.

That means old Treyarch-named maps are still useful as historical geometry/progression references, but **the richer quest architecture is mainly in later official/current community source**, not these early beta recreations.

## Classification rule

Every recovered archive map is now classified by **actual source behavior**, never filename:

- `PROTOTYPE_SHELL`
- `SURVIVAL_PROGRESSION`
- `SYSTEM_TEST`
- `SECRET_INTERACTION`
- `FULL_SURVIVAL_SYSTEMS`
- `QUEST_GRAPH`
- `RECREATION_LAYOUT_ONLY`

No archive map is promoted to `QUEST_GRAPH` without a real multi-stage source graph.

