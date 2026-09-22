# Zombie Human-Mocap Library

This folder is the staging library for human-performed zombie motion used by the game.

## Source policy

Only assets whose terms allow this repository to redistribute the motion data are committed here.

Current redistributable source:
- **CMU Graphics Lab Motion Capture Database** — human optical motion capture.
- CMU states that the data may be copied, modified, or redistributed without permission, and may be included in commercially sold products, but the raw/converted data itself may not be resold as an animation-data product.
- Source: http://mocap.cs.cmu.edu
- FBX conversion used by the importer: https://huggingface.co/datasets/gbionics/cmu-fbx

Required acknowledgement retained with the library:
> The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217.

## Design goal

Do not give the whole horde one walk cycle. Runtime selection should choose among multiple human performances within the same semantic state.

Initial buckets:
- walk
- crawl
- getup
- idle
- attack
- reach
- run_transition
- death_candidate

The manifest intentionally includes explicit zombie recordings plus zombie-suitable human performances such as limp, drag-leg, hurt-leg, Frankenstein, mummy, drunk, stumble, spastic, scared, creeping, and slow walks.

## Layout

```
assets/animations/zombie_mocap/
  cmu/
    <category>/
      <variant>__<CMU_clip_id>.fbx
  catalog.csv
  LICENSE_CMU_MOCAP.md
```

`tools/zombie_mocap_manifest.tsv` is the source-of-truth selection.  
`scripts/fetch_zombie_mocap.sh` downloads exactly those clips and does not fetch marketplace/ripped/proprietary animation packs.

Commercial-use packs that prohibit raw redistribution (for example Mixamo/Rokoko/marketplace downloads when their EULA requires per-user acquisition) must be referenced separately, not committed as raw files.
