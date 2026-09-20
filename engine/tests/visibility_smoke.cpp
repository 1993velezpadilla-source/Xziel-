#include "xziel/visibility.hpp"

#include <array>
#include <cassert>

int main() {
    std::array<xziel::VisibilityCandidate, 5> candidates{{
        {
            .id = 1,
            .distanceMeters = 2.0f,
            .screenCoverage = 0.20f,
            .lodCount = 4,
        },
        {
            .id = 2,
            .distanceMeters = 25.0f,
            .screenCoverage = 0.02f,
            .lodCount = 4,
        },
        {
            .id = 3,
            .distanceMeters = 80.0f,
            .screenCoverage = 0.0001f,
            .lodCount = 4,
        },
        {
            .id = 4,
            .distanceMeters = 12.0f,
            .screenCoverage = 0.10f,
            .frustumVisible = false,
            .lodCount = 4,
        },
        {
            .id = 5,
            .distanceMeters = 120.0f,
            .screenCoverage = 0.0001f,
            .frustumVisible = false,
            .important = true,
            .lodCount = 4,
        },
    }};

    xziel::RenderWorkload workload{};
    workload.quality = xziel::RenderQuality::High;

    std::array<xziel::VisibilityDecision, 5> decisions{};
    xziel::VisibilityPlanner planner;

    const auto stats = planner.plan(
        candidates.data(),
        candidates.size(),
        workload,
        60.0f,
        decisions.data(),
        decisions.size());

    assert(decisions[0].submitDraw);
    assert(decisions[0].lodIndex == 0);

    assert(decisions[1].submitDraw);
    assert(decisions[1].lodIndex >= 1);

    assert(!decisions[2].submitDraw);
    assert(!decisions[3].submitDraw);

    // Important gameplay objects stay visible despite normal culling gates.
    assert(decisions[4].submitDraw);
    assert(decisions[4].lodIndex == 0);

    assert(stats.submitted == 3);
    assert(stats.frustumCulled == 1);
    assert(stats.distanceCulled + stats.tinyCulled >= 1);
    assert(stats.occlusionTestsRequested <= 128);

    return 0;
}
