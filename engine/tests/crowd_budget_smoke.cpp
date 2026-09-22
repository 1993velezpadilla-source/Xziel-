#include "xziel/crowd_budget.hpp"

#include <array>
#include <cassert>

int main() {
    std::array<xziel::CrowdAgent, 6> agents{{
        {.id = 1, .distanceMeters = 2.0f, .screenCoverage = 0.15f},
        {.id = 2, .distanceMeters = 10.0f, .screenCoverage = 0.04f},
        {.id = 3, .distanceMeters = 24.0f, .screenCoverage = 0.01f},
        {.id = 4, .distanceMeters = 50.0f, .screenCoverage = 0.001f},
        {.id = 5, .distanceMeters = 30.0f, .screenCoverage = 0.01f, .attackingPlayer = true},
        {.id = 6, .distanceMeters = 8.0f, .screenCoverage = 0.06f, .ragdoll = true},
    }};

    xziel::RenderWorkload workload{};
    workload.quality = xziel::RenderQuality::High;
    workload.shadowedLightBudget = 4;

    std::array<xziel::CrowdAgentPlan, 6> plans{};
    xziel::CrowdBudgetPlanner planner;

    const auto stats = planner.plan(
        agents.data(),
        agents.size(),
        workload,
        plans.data(),
        plans.size());

    assert(plans[0].poseQuality == xziel::CrowdPoseQuality::FullSkeleton);
    assert(plans[1].animationEveryNTicks == 2);
    assert(plans[2].animationEveryNTicks >= 3);
    assert(plans[3].poseQuality == xziel::CrowdPoseQuality::FrozenFarPose);

    // Attacking agent stays full-fidelity even when far.
    assert(plans[4].poseQuality == xziel::CrowdPoseQuality::FullSkeleton);

    assert(stats.fullSkeleton >= 2);
    assert(stats.ragdollsActive <= 8);
    assert(stats.dynamicShadowCasters <= 10);

    return 0;
}
