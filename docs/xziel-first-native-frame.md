# Xziel Engine — first native Android/Vulkan executable

Date: 2026-09-20

## Purpose

This is intentionally a separate Android app under xziel-native-android/.

It does not replace or modify the existing SDL/Vril NZ:P application. Its only
job is to make the new first-party engine executable on Android early.

## Current milestone

The prototype now contains:

- AndroidX GameActivity 4.4.2
- Android 16 QPR2 / API 36.1 compile SDK, API 36 target
- Android 10 / API 29 minimum
- arm64-v8a and x86_64 native targets
- the existing first-party Xziel C++ core linked into the APK
- GameActivity lifecycle mapped into AndroidRuntimeStateMachine
- a real Vulkan 1.1 instance
- VK_KHR_android_surface
- physical-device and graphics/present queue selection
- Vulkan logical device
- VK_KHR_swapchain
- FIFO present mode
- swapchain image views and framebuffers
- render pass
- command pool and command buffers
- two frames in flight
- per-frame semaphores and fences
- per-image fence ownership
- swapchain out-of-date/suboptimal recreation
- clean surface teardown/recreation
- a slowly pulsing dark horror clear color

No shader, Quake renderer, Vril renderer, Unity code or COD Mobile code is used
in this milestone.

Android recommends GameActivity for new C/C++ intensive games. GameActivity
4.4.2 is the stable May 2026 release.

References:
https://developer.android.com/games/agdk/game-activity
https://developer.android.com/jetpack/androidx/releases/games

## Why a clear screen matters

This crosses the real platform boundary:

GameActivity -> native_app_glue -> Xziel lifecycle -> Vulkan instance/device ->
Android surface -> swapchain -> command submission -> present.

The next renderer milestones can now be added one at a time without touching the
legacy APK.

## Correctness rules already applied

The prototype uses explicit semaphores and fences rather than depending on
incidental blocking behavior from acquire/present.

Android's native Vulkan guidance warns that acquire/present behavior can vary by
driver and recommends explicit synchronization.

Reference:
https://developer.android.com/games/develop/vulkan/native-engine-support

The swapchain uses FIFO because it is the universally available Vulkan present
mode and is a conservative baseline until Swappy is connected.

## Texture pipeline decision

KTX2 plus Basis Universal remains the preferred portable content path. Khronos
documents runtime transcoding from Basis UASTC/ETC1S into GPU-native formats
such as ASTC, ETC2 and BC.

Reference:
https://github.khronos.org/Vulkan-Site/samples/latest/samples/performance/texture_compression_basisu/README.html

## Descriptor lifetime rule

Streaming texture/material descriptors will only be updated at a known safe
frame point after the corresponding frame fence has signaled.

Khronos's descriptor-indexing guidance highlights this approach as a simple way
to avoid changing descriptors still referenced by the GPU.

Reference:
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Advanced_Topics/Descriptor_Indexing_UpdateAfterBind.html

## Next renderer milestones

1. emulator or physical-device first-frame smoke test
2. Swappy
3. depth attachment
4. offline shader compilation and SPIR-V validation
5. indexed triangle/mesh
6. camera matrices
7. PBR material
8. directional plus point light
9. Forward+ bootstrap
10. shadow atlas
11. KTX2/Basis texture upload
12. GPU particles
13. weapon viewmodel
14. animated zombie test target
