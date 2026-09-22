# Quaternius Zombie Apocalypse Kit — animation source

Source: Quaternius, **Zombie Apocalypse Kit** (March 2024)  
License: **CC0 1.0 Universal / Public Domain Dedication**

This folder deliberately imports only the four animated zombie character files plus the original license. Each glTF is self-contained (embedded buffer/image data), so the animation and skeleton stay together.

Imported zombie bodies:
- `Zombie_Basic.gltf`
- `Zombie_Chubby.gltf`
- `Zombie_Arm.gltf`
- `Zombie_Ribcage.gltf`

The actual embedded clips are inspected during import and written to `animation_catalog.csv` and `animation_variants.txt`.

Known semantic clips across these bodies include:
`Crawl`, `Death`, `HitReact`, `Idle`, `Idle_Attack`, `Punch`, `Run`, `Run_Arms`, `Run_Attack`, and `Walk`, plus jump/gesture clips depending on the body.

This is a separate CC0 animation source from the CMU optical-motion-capture library. Do not label these Quaternius clips as optical mocap.
