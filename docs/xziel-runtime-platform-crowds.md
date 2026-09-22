# Xziel Engine — Android runtime, crowds and GPU scene planning

Date: 2026-09-20

## Android lifecycle

A native Android game must treat surface lifetime separately from process/game
lifetime. Xziel's AndroidRuntimeStateMachine explicitly tracks:

- created/started/resumed
- focus
- surface availability
- renderer-recreate request
- memory-trim request
- background throttling
- generation number

Simulation and rendering are separate derived states. A destroyed surface stops
rendering without pretending the whole game process has vanished.

GameActivity is the intended platform shell for the real Android backend.

Reference:
https://developer.android.com/games/agdk/game-activity/get-started

## Android 16 headroom

Android 16 introduces CPU/GPU headroom APIs through SystemHealthManager. Android
describes them as useful for sustained, intense workloads such as games, while
also warning about TOCTOU behavior and over-reacting to individual samples.

References:
https://developer.android.com/about/versions/16/features
https://developer.android.com/ndk/reference/group/system-health

Xziel therefore smooths headroom over seconds. Headroom informs quality policy;
it does not directly change gameplay timing.

## Zombie crowd budget

A Zombies renderer has a specific worst case: dozens of similar animated
characters, blood decals, shadows and ragdolls at once.

CrowdBudgetPlanner separates gameplay simulation from presentation cost.

Near/attacking/boss/recently-hit zombies:
- full skeletal pose
- full animation cadence
- highest perception cadence
- first choice for shadows/ragdolls

Medium:
- reduced skeleton
- half-rate pose evaluation

Far visible:
- lower pose rate plus interpolation

Very far:
- frozen/cached far pose until visually relevant again

Crucially, this does not freeze movement, attacks or hit registration. It is a
render/pose/perception-budget hint.

## GPU-driven rendering

Khronos's current Vulkan sample shows GPU-generated indirect draws as a way to
reduce CPU binding/command-generation overhead in large scenes. It also
documents multi-draw indirect as a way to execute many GPU-generated draw
commands efficiently when supported.

References:
https://github.khronos.org/Vulkan-Site/samples/latest/samples/performance/multi_draw_indirect/README.html
https://github.khronos.org/Vulkan-Site/tutorial/latest/Advanced_Vulkan_Compute/07_GPU_Driven_Pipelines/04_multi_draw_indirect_mdi.html

Xziel chooses between:

- CPU individual
- CPU instancing
- GPU indirect
- GPU multi-draw indirect

based on renderer backend, capabilities, visible-object count and CPU pressure.

No map requires indirect rendering to function. Compatibility fallback remains
mandatory.

## First-person camera

CameraRig combines:

- footstep bob
- sprint FOV
- recoil
- landing kick
- slide/dive pitch
- wall-run roll
- viewmodel lowering
- subtle HorrorDirector breathing

Every component is clamped.

Reduced Motion dramatically scales camera movement while preserving the actual
player movement and controls. ADS also reduces camera motion so visual effects
do not fight aiming.

The engine intentionally avoids forcing strong full-screen motion blur as a core
movement cue.
