#include "xziel/crowd_budget.hpp"

#include <algorithm>

namespace xziel {

CrowdBudgetStats CrowdBudgetPlanner::plan(
    const CrowdAgent* agents,
    std::size_t agentCount,
    const RenderWorkload& workload,
    CrowdAgentPlan* destination,
    std::size_t destinationCapacity) const noexcept {
    CrowdBudgetStats stats{};

    if (agents == nullptr ||
        destination == nullptr ||
        destinationCapacity == 0) {
        return stats;
    }

    const std::size_t count =
        std::min(agentCount, destinationCapacity);

    std::uint32_t ragdollsRemaining =
        ragdollBudget(workload.quality);
    std::uint32_t shadowCastersRemaining =
        crowdShadowBudget(workload.quality);

    for (std::size_t i = 0; i < count; ++i) {
        const auto& agent = agents[i];
        auto& out = destination[i];

        out = {};
        out.id = agent.id;

        const bool urgent =
            agent.attackingPlayer ||
            agent.recentlyHit ||
            agent.boss;

        if (urgent ||
            agent.distanceMeters <= 7.0f ||
            agent.screenCoverage >= 0.08f) {
            out.poseQuality = CrowdPoseQuality::FullSkeleton;
            out.animationEveryNTicks = 1;
            out.aiSenseEveryNTicks = 1;
            ++stats.fullSkeleton;
        } else if (
            agent.visible &&
            (agent.distanceMeters <= 16.0f ||
             agent.screenCoverage >= 0.025f)) {
            out.poseQuality = CrowdPoseQuality::ReducedSkeleton;
            out.animationEveryNTicks = 2;
            out.aiSenseEveryNTicks = 2;
            ++stats.reducedSkeleton;
        } else if (
            agent.visible &&
            agent.distanceMeters <= 32.0f) {
            out.poseQuality = CrowdPoseQuality::Interpolated;
            out.animationEveryNTicks =
                workload.quality >= RenderQuality::High ? 3 : 4;
            out.aiSenseEveryNTicks = 4;
            ++stats.interpolated;
        } else {
            out.poseQuality = CrowdPoseQuality::FrozenFarPose;
            out.animationEveryNTicks = 8;
            out.aiSenseEveryNTicks = 8;
            ++stats.frozenFarPose;
        }

        // Gameplay movement/attack simulation is NOT frozen by this planner.
        // Only expensive visual pose evaluation and perception cadence hints are
        // reduced for distant non-critical agents.

        if (agent.ragdoll &&
            ragdollsRemaining > 0 &&
            (agent.visible || urgent)) {
            out.updateRagdollPhysics = true;
            --ragdollsRemaining;
            ++stats.ragdollsActive;
        }

        if (agent.visible &&
            shadowCastersRemaining > 0 &&
            (urgent ||
             agent.distanceMeters <= 12.0f) &&
            workload.shadowedLightBudget > 0) {
            out.castDynamicShadow = true;
            --shadowCastersRemaining;
            ++stats.dynamicShadowCasters;
        }

        out.useGpuSkinning =
            out.poseQuality != CrowdPoseQuality::FrozenFarPose;
    }

    return stats;
}

std::uint32_t CrowdBudgetPlanner::ragdollBudget(
    RenderQuality quality) noexcept {
    switch (quality) {
        case RenderQuality::Low: return 2;
        case RenderQuality::Medium: return 4;
        case RenderQuality::High: return 8;
        case RenderQuality::Ultra: return 12;
    }
    return 4;
}

std::uint32_t CrowdBudgetPlanner::crowdShadowBudget(
    RenderQuality quality) noexcept {
    switch (quality) {
        case RenderQuality::Low: return 3;
        case RenderQuality::Medium: return 6;
        case RenderQuality::High: return 10;
        case RenderQuality::Ultra: return 16;
    }
    return 6;
}

} // namespace xziel
