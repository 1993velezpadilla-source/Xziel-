#include "xziel/visibility.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

VisibilityStats VisibilityPlanner::plan(
    const VisibilityCandidate* candidates,
    std::size_t candidateCount,
    const RenderWorkload& workload,
    float farDistanceMeters,
    VisibilityDecision* destination,
    std::size_t destinationCapacity) const noexcept {
    VisibilityStats stats{};

    if (candidates == nullptr ||
        destination == nullptr ||
        destinationCapacity == 0) {
        return stats;
    }

    const std::size_t count =
        std::min(candidateCount, destinationCapacity);
    const float maxDistance =
        std::max(1.0f, farDistanceMeters);
    const std::uint32_t queryBudget =
        occlusionBudget(workload.quality);

    for (std::size_t i = 0; i < count; ++i) {
        const auto& candidate = candidates[i];
        auto& out = destination[i];

        out = {};
        out.id = candidate.id;

        if (!candidate.frustumVisible &&
            !candidate.important) {
            ++stats.frustumCulled;
            continue;
        }

        if (candidate.distanceMeters > maxDistance &&
            !candidate.important) {
            ++stats.distanceCulled;
            continue;
        }

        const bool tiny =
            candidate.screenCoverage < 0.00018f &&
            candidate.distanceMeters > maxDistance * 0.45f;

        if (tiny && !candidate.important) {
            ++stats.tinyCulled;
            continue;
        }

        out.submitDraw = true;
        out.lodIndex = chooseLod(candidate);
        ++stats.submitted;

        const bool worthQuery =
            candidate.occlusionEligible &&
            !candidate.important &&
            candidate.screenCoverage >= 0.0008f &&
            candidate.distanceMeters > 5.0f;

        if (worthQuery &&
            stats.occlusionTestsRequested < queryBudget) {
            // Objects visible last frame are still drawn now and can be tested
            // for the next frame. This avoids introducing one-frame popping
            // from a late occlusion result.
            out.requestOcclusionTest = true;
            ++stats.occlusionTestsRequested;
        }
    }

    return stats;
}

std::uint32_t VisibilityPlanner::occlusionBudget(
    RenderQuality quality) noexcept {
    switch (quality) {
        case RenderQuality::Low: return 32;
        case RenderQuality::Medium: return 64;
        case RenderQuality::High: return 128;
        case RenderQuality::Ultra: return 192;
    }
    return 64;
}

std::uint8_t VisibilityPlanner::chooseLod(
    const VisibilityCandidate& candidate) noexcept {
    const std::uint8_t count =
        std::max<std::uint8_t>(1U, candidate.lodCount);

    if (count == 1 || candidate.important) {
        return 0;
    }

    const float coverage =
        std::max(0.0f, candidate.screenCoverage);

    if (coverage >= 0.08f) {
        return 0;
    }
    if (coverage >= 0.025f) {
        return std::min<std::uint8_t>(1U, count - 1U);
    }
    if (coverage >= 0.006f) {
        return std::min<std::uint8_t>(2U, count - 1U);
    }

    return count - 1U;
}

} // namespace xziel
