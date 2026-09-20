#pragma once

#include "xziel/performance.hpp"

#include <cstddef>
#include <cstdint>

namespace xziel {

enum class CrowdPoseQuality : std::uint8_t {
    FullSkeleton,
    ReducedSkeleton,
    Interpolated,
    FrozenFarPose,
};

struct CrowdAgent {
    std::uint64_t id = 0;

    float distanceMeters = 0.0f;
    float screenCoverage = 0.0f;

    bool visible = true;
    bool attackingPlayer = false;
    bool recentlyHit = false;
    bool boss = false;
    bool ragdoll = false;
};

struct CrowdAgentPlan {
    std::uint64_t id = 0;

    CrowdPoseQuality poseQuality = CrowdPoseQuality::FullSkeleton;

    std::uint8_t animationEveryNTicks = 1;
    std::uint8_t aiSenseEveryNTicks = 1;

    bool updateRagdollPhysics = false;
    bool castDynamicShadow = false;
    bool useGpuSkinning = true;
};

struct CrowdBudgetStats {
    std::uint32_t fullSkeleton = 0;
    std::uint32_t reducedSkeleton = 0;
    std::uint32_t interpolated = 0;
    std::uint32_t frozenFarPose = 0;

    std::uint32_t ragdollsActive = 0;
    std::uint32_t dynamicShadowCasters = 0;
};

class CrowdBudgetPlanner final {
public:
    [[nodiscard]] CrowdBudgetStats plan(
        const CrowdAgent* agents,
        std::size_t agentCount,
        const RenderWorkload& workload,
        CrowdAgentPlan* destination,
        std::size_t destinationCapacity) const noexcept;

private:
    [[nodiscard]] static std::uint32_t ragdollBudget(
        RenderQuality quality) noexcept;

    [[nodiscard]] static std::uint32_t crowdShadowBudget(
        RenderQuality quality) noexcept;
};

} // namespace xziel
