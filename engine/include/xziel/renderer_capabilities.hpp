#pragma once

#include <cstdint>

namespace xziel {

enum class RendererBackend : std::uint8_t {
    Vulkan,
    CompatibilityOpenGLES,
    Unsupported,
};

enum class TextureCompression : std::uint8_t {
    ASTC,
    ETC2,
    RGBA8,
};

enum class DeviceClass : std::uint8_t {
    Entry,
    Mid,
    High,
    Flagship,
};

struct RendererDeviceCapabilities {
    std::uint32_t androidApiLevel = 29;
    std::uint32_t vulkanMajor = 1;
    std::uint32_t vulkanMinor = 1;

    DeviceClass deviceClass = DeviceClass::Mid;

    bool hasVulkan = true;
    bool hasOpenGLES3 = true;

    bool hasASTC = false;
    bool hasETC2 = true;
    bool hasFp16Arithmetic = false;
    bool hasTimelineSemaphores = false;
    bool hasDynamicRendering = false;
    bool hasDescriptorIndexing = false;
    bool hasMemoryBudget = false;
    bool hasPresentTiming = false;
    bool hasRayQuery = false;
    bool hasAsyncComputeQueue = false;

    std::uint32_t approximateDeviceMemoryMB = 4096;
};

struct RendererFeatureRequest {
    bool preferVulkan = true;
    bool allowCompatibilityRenderer = true;

    bool enableFp16WhenSafe = true;
    bool enableAsyncCompute = true;
    bool enableRayQueryExperimental = false;
};

struct RendererFeaturePlan {
    RendererBackend backend = RendererBackend::Unsupported;
    TextureCompression textureCompression = TextureCompression::RGBA8;

    bool useSwappy = false;
    bool useFp16Arithmetic = false;
    bool useTimelineSemaphores = false;
    bool useDynamicRendering = false;
    bool useDescriptorIndexing = false;
    bool useMemoryBudgetExtension = false;
    bool usePresentTiming = false;
    bool useAsyncCompute = false;
    bool useRayQuery = false;

    // Always true for Vulkan: Xziel never builds pipelines during a draw call.
    bool usePersistentPipelineCache = false;
    bool useDescriptorCache = false;

    std::uint32_t textureBudgetMB = 256;
    std::uint32_t meshBudgetMB = 96;
    std::uint32_t transientGpuBudgetMB = 96;
};

class RendererCapabilityPlanner final {
public:
    [[nodiscard]] RendererFeaturePlan plan(
        const RendererDeviceCapabilities& capabilities,
        const RendererFeatureRequest& request = {}) const noexcept;

private:
    [[nodiscard]] static bool hasAtLeastVulkan11(
        const RendererDeviceCapabilities& capabilities) noexcept;
};

} // namespace xziel
