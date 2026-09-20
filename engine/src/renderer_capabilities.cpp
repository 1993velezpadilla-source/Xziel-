#include "xziel/renderer_capabilities.hpp"

#include <algorithm>

namespace xziel {

RendererFeaturePlan RendererCapabilityPlanner::plan(
    const RendererDeviceCapabilities& capabilities,
    const RendererFeatureRequest& request) const noexcept {
    RendererFeaturePlan out{};

    const bool vulkanReady =
        capabilities.hasVulkan &&
        hasAtLeastVulkan11(capabilities) &&
        capabilities.androidApiLevel >= 29;

    if (request.preferVulkan && vulkanReady) {
        out.backend = RendererBackend::Vulkan;
        out.useSwappy = true;
        out.usePersistentPipelineCache = true;
        out.useDescriptorCache = true;

        out.useFp16Arithmetic =
            request.enableFp16WhenSafe &&
            capabilities.hasFp16Arithmetic;

        out.useTimelineSemaphores =
            capabilities.hasTimelineSemaphores;
        out.useDynamicRendering =
            capabilities.hasDynamicRendering;
        out.useDescriptorIndexing =
            capabilities.hasDescriptorIndexing;
        out.useMemoryBudgetExtension =
            capabilities.hasMemoryBudget;
        out.usePresentTiming =
            capabilities.hasPresentTiming;

        out.useAsyncCompute =
            request.enableAsyncCompute &&
            capabilities.hasAsyncComputeQueue &&
            capabilities.deviceClass >= DeviceClass::High;

        // Never silently turn this on merely because the extension exists.
        out.useRayQuery =
            request.enableRayQueryExperimental &&
            capabilities.hasRayQuery &&
            capabilities.deviceClass == DeviceClass::Flagship;
    } else if (
        request.allowCompatibilityRenderer &&
        capabilities.hasOpenGLES3) {
        out.backend = RendererBackend::CompatibilityOpenGLES;
        out.useSwappy = true;
    } else if (vulkanReady) {
        out.backend = RendererBackend::Vulkan;
        out.useSwappy = true;
        out.usePersistentPipelineCache = true;
        out.useDescriptorCache = true;
    } else {
        out.backend = RendererBackend::Unsupported;
    }

    if (capabilities.hasASTC) {
        out.textureCompression = TextureCompression::ASTC;
    } else if (capabilities.hasETC2) {
        out.textureCompression = TextureCompression::ETC2;
    } else {
        out.textureCompression = TextureCompression::RGBA8;
    }

    const std::uint32_t memoryMB =
        std::max<std::uint32_t>(
            1024U,
            capabilities.approximateDeviceMemoryMB);

    // Budgets deliberately consume only a fraction of system memory. The final
    // Vulkan backend will tighten them using real heap-budget telemetry where
    // VK_EXT_memory_budget is available.
    switch (capabilities.deviceClass) {
        case DeviceClass::Entry:
            out.textureBudgetMB =
                std::min<std::uint32_t>(192U, memoryMB / 10U);
            out.meshBudgetMB =
                std::min<std::uint32_t>(64U, memoryMB / 20U);
            out.transientGpuBudgetMB =
                std::min<std::uint32_t>(64U, memoryMB / 20U);
            break;
        case DeviceClass::Mid:
            out.textureBudgetMB =
                std::min<std::uint32_t>(384U, memoryMB / 8U);
            out.meshBudgetMB =
                std::min<std::uint32_t>(128U, memoryMB / 18U);
            out.transientGpuBudgetMB =
                std::min<std::uint32_t>(128U, memoryMB / 18U);
            break;
        case DeviceClass::High:
            out.textureBudgetMB =
                std::min<std::uint32_t>(768U, memoryMB / 7U);
            out.meshBudgetMB =
                std::min<std::uint32_t>(256U, memoryMB / 16U);
            out.transientGpuBudgetMB =
                std::min<std::uint32_t>(256U, memoryMB / 16U);
            break;
        case DeviceClass::Flagship:
            out.textureBudgetMB =
                std::min<std::uint32_t>(1024U, memoryMB / 6U);
            out.meshBudgetMB =
                std::min<std::uint32_t>(384U, memoryMB / 14U);
            out.transientGpuBudgetMB =
                std::min<std::uint32_t>(384U, memoryMB / 14U);
            break;
    }

    // Uncompressed RGBA8 consumes much more memory. Keep extra headroom on
    // fallback devices instead of risking eviction storms/OOM.
    if (out.textureCompression == TextureCompression::RGBA8) {
        out.textureBudgetMB =
            std::max<std::uint32_t>(96U, out.textureBudgetMB * 3U / 4U);
    }

    return out;
}

bool RendererCapabilityPlanner::hasAtLeastVulkan11(
    const RendererDeviceCapabilities& capabilities) noexcept {
    return capabilities.vulkanMajor > 1 ||
        (capabilities.vulkanMajor == 1 &&
         capabilities.vulkanMinor >= 1);
}

} // namespace xziel
