# Xziel Engine — frame architecture and visibility

Date: 2026-09-20

## Why this exists

A modern renderer can become slower than an old renderer if every visual feature
creates its own full-resolution image, memory allocation and scene pass.

Xziel therefore treats passes and intermediate images as a frame graph with
explicit lifetimes.

## FrameGraph

The current CPU planner supports up to 64 resources and 64 passes with fixed
storage.

It validates read-before-write mistakes for non-external resources and computes
first/last use of every transient resource.

Non-overlapping transient resources can share an alias group. For example a
reflection target that dies before a bloom scratch image begins does not require
two simultaneously committed blocks of transient memory.

The future Vulkan backend maps alias groups onto reusable/suballocated image
memory while respecting actual format/alignment requirements.

This follows the mobile principle emphasized by Khronos: memory bandwidth and
DRAM traffic are critical constraints, and pool/suballocation/reuse is
preferable to repeated small allocations.

References:
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Mobile_Development/03_performance_optimizations.html
https://github.khronos.org/Vulkan-Site/tutorial/latest/Advanced_Vulkan_Compute/12_Mobile_and_Embedded_Compute/03_mobile_optimization.html

## Visibility

VisibilityPlanner performs cheap CPU gates before draw submission:

1. frustum visibility
2. far-distance budget
3. tiny-object rejection
4. LOD choice
5. bounded occlusion-test requests

Important gameplay objects can bypass normal visual culling gates so a renderer
optimization never makes a required interactable/zombie disappear from game
logic. Rendering visibility and gameplay existence remain separate concepts.

The Vulkan renderer will later feed occlusion tests from a hierarchical depth
buffer/HZB. Results are consumed conservatively: an object visible last frame
can still render while being tested for a future frame, avoiding hard one-frame
popping.

Khronos mobile guidance explicitly recommends front-to-back rendering, early-Z
and occlusion culling where appropriate.

Reference:
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Mobile_Development/04_rendering_approaches.html

## Hot-path rules

- no frame-loop image/buffer allocation
- no draw-time pipeline creation
- no per-draw descriptor allocation
- no unbounded reflection/shadow/particle passes
- no optional feature without a fallback
- no renderer culling decision may delete gameplay state
