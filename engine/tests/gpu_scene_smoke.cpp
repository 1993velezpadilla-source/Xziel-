#include "xziel/gpu_scene.hpp"

#include <cassert>

int main() {
    xziel::GpuScenePlanner planner;

    xziel::RendererFeaturePlan vulkan{};
    vulkan.backend = xziel::RendererBackend::Vulkan;

    xziel::GpuSceneCapabilities capable{};
    capable.drawIndirect = true;
    capable.multiDrawIndirect = true;
    capable.computeCulling = true;

    auto plan = planner.plan(
        vulkan,
        capable,
        {
            .visibleObjectCount = 1200,
            .repeatedInstanceCount = 500,
            .materialCount = 32,
            .cpuBoundLikely = true,
        });

    assert(
        plan.mode ==
        xziel::SceneSubmissionMode::GpuMultiDrawIndirect);
    assert(plan.runGpuFrustumCull);
    assert(plan.runGpuOcclusionCull);

    xziel::RendererFeaturePlan gles{};
    gles.backend =
        xziel::RendererBackend::CompatibilityOpenGLES;

    plan = planner.plan(
        gles,
        capable,
        {
            .visibleObjectCount = 1200,
            .repeatedInstanceCount = 100,
            .materialCount = 32,
            .cpuBoundLikely = true,
        });

    assert(
        plan.mode ==
        xziel::SceneSubmissionMode::CpuInstanced);

    return 0;
}
