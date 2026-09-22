#include "xziel/gpu_scene.hpp"

#include <algorithm>

namespace xziel {

GpuScenePlan GpuScenePlanner::plan(
    const RendererFeaturePlan& renderer,
    const GpuSceneCapabilities& capabilities,
    const GpuSceneInput& input) const noexcept {
    GpuScenePlan out{};

    if (renderer.backend != RendererBackend::Vulkan) {
        if (input.repeatedInstanceCount >= 4) {
            out.mode = SceneSubmissionMode::CpuInstanced;
            out.preferredInstanceBatchSize = 32;
        }
        return out;
    }

    const bool largeScene =
        input.visibleObjectCount >= 384;
    const bool manyRepeated =
        input.repeatedInstanceCount >= 32;

    if (capabilities.multiDrawIndirect &&
        capabilities.computeCulling &&
        largeScene) {
        out.mode =
            SceneSubmissionMode::GpuMultiDrawIndirect;
        out.runGpuFrustumCull = true;
        out.runGpuOcclusionCull =
            input.visibleObjectCount >= 768;
        out.maxIndirectDraws =
            std::min<std::uint32_t>(
                input.visibleObjectCount,
                4096U);
        out.preferredInstanceBatchSize = 128;
        return out;
    }

    if (capabilities.drawIndirect &&
        capabilities.computeCulling &&
        (largeScene || input.cpuBoundLikely)) {
        out.mode = SceneSubmissionMode::GpuIndirect;
        out.runGpuFrustumCull = true;
        out.runGpuOcclusionCull =
            input.visibleObjectCount >= 1024;
        out.maxIndirectDraws =
            std::min<std::uint32_t>(
                input.visibleObjectCount,
                2048U);
        out.preferredInstanceBatchSize = 64;
        return out;
    }

    if (manyRepeated) {
        out.mode = SceneSubmissionMode::CpuInstanced;
        out.preferredInstanceBatchSize = 64;
        return out;
    }

    out.mode = SceneSubmissionMode::CpuIndividual;
    out.preferredInstanceBatchSize = 1;
    return out;
}

} // namespace xziel
