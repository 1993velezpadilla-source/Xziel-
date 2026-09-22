#include "xziel/haptics.hpp"

#include <cassert>

int main() {
    xziel::HapticsPlanner planner({
        .enabled = true,
        .userStrength = 1.0f,
        .frequentEventStrengthScale = 0.5f,
        .heartbeatStrengthScale = 0.4f,
        .minimumGapSeconds = 0.018f,
    });

    xziel::HapticCapabilities rich{};
    rich.hasVibrator = true;
    rich.hasAmplitudeControl = true;
    rich.hasCompositionPrimitives = true;
    rich.hasEnvelopeEffects = true;

    auto fire = planner.request(
        xziel::HapticEvent::FireLight,
        rich,
        1.0f);
    assert(fire.play);
    assert(fire.amplitude > 0.0f);
    assert(fire.amplitude < 0.5f);

    // Automatic fire cannot continuously hammer the actuator.
    auto spam = planner.request(
        xziel::HapticEvent::FireLight,
        rich,
        0.001f);
    assert(!spam.play);

    auto explosion = planner.request(
        xziel::HapticEvent::ExplosionNear,
        rich,
        0.10f);
    assert(explosion.play);
    assert(explosion.preferComposition);
    assert(explosion.preferEnvelope);

    xziel::HapticCapabilities simple{};
    simple.hasVibrator = true;
    simple.hasAmplitudeControl = false;

    auto simpleHit = planner.request(
        xziel::HapticEvent::PlayerHit,
        simple,
        0.10f);
    assert(simpleHit.play);
    assert(simpleHit.amplitude == 1.0f);

    return 0;
}
