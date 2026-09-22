# Runtime Zombie Variant Licensing

The generated runtime zombie models in this project combine two source classes:

1. **NZ:P zombie mesh / UV / textures / rig**
   - Upstream: https://github.com/nzp-team/assets
   - Source used by the retarget pipeline: `source/models/ai/zfull/mesh.blend` and its `texture_*.png` files.
   - Upstream assets repository license: CC BY-SA 4.0.
   - The pipeline pins the exact upstream revision used for reproducible generation.

2. **CMU Graphics Lab Motion Capture Database**
   - Human motion source: http://mocap.cs.cmu.edu
   - CMU permits copying, modification and redistribution, including inclusion in commercially sold products, subject to its published terms.
   - Required acknowledgement is retained in `../zombie_mocap/LICENSE_CMU_MOCAP.md`.

## Resulting generated MDLs

Generated MDLs that contain the NZ:P zombie geometry/textures are derivative
assets and must be distributed consistently with the applicable NZ:P
CC BY-SA 4.0 terms. Do not relabel these generated models as CC0 merely
because the motion source is permissive.

The raw CMU FBX motion files remain catalogued separately from the generated
NZ:P-derived runtime models.
