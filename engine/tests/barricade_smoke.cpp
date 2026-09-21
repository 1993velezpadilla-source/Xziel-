#include "xziel/barricade.hpp"

#include <cassert>

int main() {
    xziel::BarricadeSystem barricade({
        .maximumPlanks = 3,
        .zombieTearSeconds = 0.10f,
        .rebuildSeconds = 0.10f,
        .rebuildPointsPerPlank = 10,
        .maximumRebuildPointsPerRound = 20,
    });

    auto frame = barricade.frame();
    assert(frame.intactPlanks == 3);
    assert(frame.blocksZombieTraversal);

    for (int plank = 0; plank < 3; ++plank) {
        for (int tick = 0; tick < 2; ++tick) {
            frame = barricade.step(true, false, 0.05f);
        }
        assert(frame.plankRemovedThisTick);
    }
    assert(frame.intactPlanks == 0);
    assert(frame.breachedThisTick);
    assert(!frame.blocksZombieTraversal);

    std::uint32_t awarded = 0;
    for (int plank = 0; plank < 3; ++plank) {
        for (int tick = 0; tick < 2; ++tick) {
            frame = barricade.step(false, true, 0.05f);
        }
        awarded += frame.pointsAwardedThisTick;
    }
    assert(frame.intactPlanks == 3);
    assert(frame.fullyRebuiltThisTick);
    assert(awarded == 20);

    // Round transition resets only the rebuild-points cap, not physical state.
    for (int tick = 0; tick < 2; ++tick) {
        frame = barricade.step(true, false, 0.05f);
    }
    barricade.beginRound();
    for (int tick = 0; tick < 2; ++tick) {
        frame = barricade.step(false, true, 0.05f);
    }
    assert(frame.pointsAwardedThisTick == 10);

    return 0;
}
