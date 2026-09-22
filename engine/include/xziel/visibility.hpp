#pragma once

#include "xziel/performance.hpp"

#include <cstddef>
#include <cstdint>

namespace xziel {

struct VisibilityCandidate {
    std::uint64_t id = 0;

    float distanceMeters = 0.0f;
    float screenCoverage = 0.0f;

    bool frustumVisible = true;
    bool occlusionEligible = true;
    bool wasVisibleLastFrame = true;
    bool important = false;

    std::uint8_t lodCount = 1;
};

struct VisibilityDecision {
    std::uint64_t id = 0;

    bool submitDraw = false;
    bool requestOcclusionTest = false;

    std::uint8_t lodIndex = 0;
};

struct VisibilityStats {
    std::uint32_t submitted = 0;
    std::uint32_t frustumCulled = 0;
    std::uint32_t distanceCulled = 0;
    std::uint32_t tinyCulled = 0;
    std::uint32_t occlusionTestsRequested = 0;
};

class VisibilityPlanner final {
public:
    [[nodiscard]] VisibilityStats plan(
        const VisibilityCandidate* candidates,
        std::size_t candidateCount,
        const RenderWorkload& workload,
        float farDistanceMeters,
        VisibilityDecision* destination,
        std::size_t destinationCapacity) const noexcept;

private:
    [[nodiscard]] static std::uint32_t occlusionBudget(
        RenderQuality quality) noexcept;

    [[nodiscard]] static std::uint8_t chooseLod(
        const VisibilityCandidate& candidate) noexcept;
};

} // namespace xziel
