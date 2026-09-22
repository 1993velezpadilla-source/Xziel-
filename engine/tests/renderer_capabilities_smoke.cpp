#include "xziel/renderer_capabilities.hpp"

#include <cassert>

int main() {
    xziel::RendererCapabilityPlanner planner;

    xziel::RendererDeviceCapabilities flagship{};
    flagship.androidApiLevel = 36;
    flagship.vulkanMajor = 1;
    flagship.vulkanMinor = 3;
    flagship.deviceClass = xziel::DeviceClass::Flagship;
    flagship.hasASTC = true;
    flagship.hasFp16Arithmetic = true;
    flagship.hasTimelineSemaphores = true;
    flagship.hasDynamicRendering = true;
    flagship.hasDescriptorIndexing = true;
    flagship.hasMemoryBudget = true;
    flagship.hasPresentTiming = true;
    flagship.hasRayQuery = true;
    flagship.hasAsyncComputeQueue = true;
    flagship.approximateDeviceMemoryMB = 12288;

    auto plan = planner.plan(
        flagship,
        {
            .preferVulkan = true,
            .allowCompatibilityRenderer = true,
            .enableFp16WhenSafe = true,
            .enableAsyncCompute = true,
            .enableRayQueryExperimental = false,
        });

    assert(plan.backend == xziel::RendererBackend::Vulkan);
    assert(plan.textureCompression == xziel::TextureCompression::ASTC);
    assert(plan.useSwappy);
    assert(plan.useFp16Arithmetic);
    assert(plan.useAsyncCompute);
    assert(!plan.useRayQuery);
    assert(plan.usePersistentPipelineCache);
    assert(plan.textureBudgetMB > 0);

    xziel::RendererDeviceCapabilities old{};
    old.androidApiLevel = 28;
    old.vulkanMajor = 1;
    old.vulkanMinor = 0;
    old.hasVulkan = true;
    old.hasOpenGLES3 = true;
    old.hasASTC = false;
    old.hasETC2 = true;
    old.deviceClass = xziel::DeviceClass::Entry;

    plan = planner.plan(old);
    assert(
        plan.backend ==
        xziel::RendererBackend::CompatibilityOpenGLES);
    assert(plan.textureCompression == xziel::TextureCompression::ETC2);

    old.hasOpenGLES3 = false;
    plan = planner.plan(old);
    assert(plan.backend == xziel::RendererBackend::Unsupported);

    return 0;
}
