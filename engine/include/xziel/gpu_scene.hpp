#pragma once

#include "xziel/renderer_capabilities.hpp"

#include <cstdint>

namespace xziel {

enum class SceneSubmissionMode : std::uint8_t {
    CpuIndividual,
    CpuInstanced,
    GpuIndirect,
    GpuMultiDrawIndirect,
};

struct GpuSceneCapabilities {
    bool drawIndirect = true;
    bool multiDrawIndirect = false;
    bool computeCulling = true;
    bool bufferDeviceAddress = false;
};

struct GpuSceneInput {
    std::uint32_t visibleObjectCount = 0;
    std::uint32_t repeatedInstanceCount = 0;
    std::uint32_t materialCount = 0;

    bool cpuBoundLikely = false;
};

struct GpuScenePlan {
    SceneSubmissionMode mode = SceneSubmissionMode::CpuIndividual;

    bool runGpuFrustumCull = false;
    bool runGpuOcclusionCull = false;

    std::uint32_t maxIndirectDraws = 0;
    std::uint32_t preferredInstanceBatchSize = 1;
};

class GpuScenePlanner final {
public:
    [[nodiscard]] GpuScenePlan plan(
        const RendererFeaturePlan& renderer,
        const GpuSceneCapabilities& capabilities,
        const GpuSceneInput& input) const noexcept;
};

} // namespace xziel
