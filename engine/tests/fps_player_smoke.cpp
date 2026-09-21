#include "xziel/fps_player.hpp"

#include <cassert>
#include <cmath>

int main() {
    xziel::FpsPlayerController player;

    xziel::InputState view{};
    view.look = {0.10f, -0.05f};
    view.gyroRadiansPerSecond = {
        0.20f,
        0.30f,
        0.0f,
    };

    player.sampleViewInput(
        view,
        1.0f / 60.0f);

    const auto afterLook =
        player.frame();

    assert(
        std::fabs(afterLook.yawDegrees) >
        1.0f);

    assert(
        std::fabs(afterLook.pitchDegrees) >
        1.0f);

    xziel::MobileMovementButtons buttons{};

    auto frame =
        player.frame();

    for (int i = 0; i < 120; ++i) {
        frame =
            player.fixedStep(
                {0.0f, 1.0f},
                buttons,
                1.0f / 120.0f);
    }

    // The player must move in the facing direction while remaining bounded.
    assert(
        frame.feetPosition.z >
        -2.55f);

    assert(
        frame.feetPosition.x >=
        -2.7801f);

    assert(
        frame.feetPosition.x <=
        2.7801f);

    assert(
        frame.feetPosition.z >=
        -3.3501f);

    assert(
        frame.feetPosition.z <=
        3.3501f);

    // Jump begins an airborne arc instead of being immediately clamped away.
    buttons.jumpPressed = true;

    frame =
        player.fixedStep(
            {},
            buttons,
            1.0f / 120.0f);

    assert(
        frame.movement.mode ==
        xziel::MovementMode::Airborne);

    assert(
        frame.movement.velocity.y >
        0.0f);

    // Pitch is hard bounded even under absurd input.
    view.look = {0.0f, 100.0f};

    player.sampleViewInput(
        view,
        1.0f / 60.0f);

    assert(
        player.frame().pitchDegrees <=
        82.0001f);

    return 0;
}
