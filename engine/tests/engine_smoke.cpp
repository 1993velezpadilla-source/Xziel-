#include "xziel/engine.hpp"

#include <cassert>
#include <cmath>
#include <cstdint>

int main() {
    xziel::Engine engine({
        .fixedTickHz = 120.0,
        .maxFrameDeltaSeconds = 0.100,
        .maxCatchUpTicks = 16,
    });

    xziel::InputState input{};
    input.move = {0.5f, 1.0f};
    input.aim = true;
    engine.submitInput(input);

    std::uint64_t totalTicks = 0;
    for (int i = 0; i < 60; ++i) {
        const auto stats = engine.advance(1.0 / 60.0);
        totalTicks += stats.ticksThisFrame;
        assert(stats.interpolationAlpha >= 0.0);
        assert(stats.interpolationAlpha <= 1.0);
    }

    assert(totalTicks == 120);
    assert(engine.simulationTick() == 120);
    assert(engine.input().aim);
    assert(std::fabs(engine.input().move.x - 0.5f) < 0.0001f);

    // A giant resume/stall delta must be bounded.
    const auto stalled = engine.advance(10.0);
    assert(stalled.clampedFrameDeltaSeconds <= 0.1000001);
    assert(stalled.ticksThisFrame <= 16);

    return 0;
}
