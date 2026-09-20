#include "xziel/scene_fx.hpp"

#include <array>
#include <cassert>

int main() {
    xziel::DecalPool decals(4);

    for (int i = 0; i < 10; ++i) {
        const auto id = decals.spawn({
            .kind = xziel::DecalKind::Blood,
            .position = {static_cast<float>(i), 0.0f, 0.0f},
            .lifetimeSeconds = 0.20f,
        });
        assert(id != 0);
        assert(decals.aliveCount() <= decals.capacity());
    }

    std::array<xziel::DecalItem, 4> visible{};
    const auto visibleCount = decals.buildVisibleList(
        {0.0f, 0.0f, 0.0f},
        100.0f,
        visible.data(),
        visible.size());
    assert(visibleCount <= decals.capacity());

    decals.advance(0.10f);
    decals.advance(0.10f);
    assert(decals.aliveCount() == 0);

    xziel::RenderWorkload workload{};
    workload.quality = xziel::RenderQuality::High;

    xziel::HorrorFrame horror{};
    horror.tension = 1.0f;
    horror.adrenaline = 1.0f;
    horror.vignetteStrength = 0.28f;
    horror.exposureBiasEv = -0.45f;

    xziel::PostProcessPlanner planner;
    const auto post = planner.plan(
        workload,
        horror,
        false,
        false);

    assert(post.vignetteStrength <= 0.35f);
    assert(post.chromaticAberrationStrength <= 0.012f);
    assert(post.ambientOcclusionEnabled);
    assert(post.temporalHistoryValid);

    const auto cut = planner.plan(
        workload,
        horror,
        true,
        false);
    assert(!cut.temporalHistoryValid);

    return 0;
}
