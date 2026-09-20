# Xziel Engine — renderer watchdog and safe-mode policy

Date: 2026-09-20

## Why this exists

A renderer failure must not become an infinite retry loop, a black screen, or a
GPU hang that keeps submitting work to an invalid device.

Vulkan device loss is sticky for the affected logical VkDevice. Khronos states
that once a device is lost it cannot be reset back to a valid state; a new
logical device is required if recovery is possible.

Reference:
https://github.khronos.org/Vulkan-Site/spec/latest/chapters/devsandqueues.html

Khronos tooling guidance also recommends treating device loss as a central
failure path: stop submitting, persist useful diagnostic markers/crash
information, and terminate cleanly unless the application has a tested
reinitialization path.

Reference:
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Tooling/04_crash_minidump.html

## Watchdog behavior

RendererWatchdog records a fixed 16-entry recent fault ring and produces a
recovery recommendation.

Examples:

- swapchain/present failure -> recreate swapchain
- shader/pipeline failure -> disable advanced features and enter safe mode
- first out-of-memory -> drop advanced features/resource quality
- repeated out-of-memory -> compatibility renderer or clean exit
- first device lost -> stop submitting and recreate logical device
- repeated device lost -> compatibility renderer or clean exit
- Vulkan init failure -> compatibility renderer when available

The core does not itself recreate Vulkan objects. It only provides a bounded,
testable policy to the platform renderer.

## Robustness

Vulkan's robustness features can make some invalid accesses deterministic, but
Khronos notes that robustness can have a runtime cost and does not replace
correct synchronization/lifetime rules.

Reference:
https://github.khronos.org/Vulkan-Site/guide/latest/robustness.html

Xziel will query robustness features and use them selectively where streaming
or optional descriptors benefit, rather than assuming robustness is free.

## Validation

Development/beta Android builds should support
VK_LAYER_KHRONOS_validation. Android documents local/APK-based validation-layer
loading on supported Android versions.

Reference:
https://developer.android.com/ndk/guides/graphics/validation-layer

Release builds do not ship validation layers as a normal runtime dependency.
