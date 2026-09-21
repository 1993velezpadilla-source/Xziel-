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

    // Static obstacle collision blocks movement through room props while
    // keeping the controller allocation-free.
    player.reset();
    player.clearStaticObstacles();

    assert(
        player.addStaticObstacle(
            {
                .minimum = {
                    -0.58f,
                    -1.60f,
                    -0.25f,
                },
                .maximum = {
                    0.58f,
                    0.95f,
                    0.95f,
                },
            }));

    for (int i = 0;
         i < 360;
         ++i) {
        frame =
            player.fixedStep(
                {0.0f, 1.0f},
                {},
                1.0f / 120.0f);
    }

    assert(
        frame.feetPosition.z <
        -0.45f);

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

    // Mantle probe turns a nearby low obstacle into the existing contextual
    // Jump/Mantle action without adding another touch-screen button.
    {
        xziel::FpsPlayerController mantlingPlayer;

        assert(
            mantlingPlayer.addStaticObstacle(
                {
                    .minimum = {
                        -0.45f,
                        -1.60f,
                        -2.12f,
                    },
                    .maximum = {
                        0.45f,
                        -0.72f,
                        -1.55f,
                    },
                }));

        xziel::MobileMovementButtons mantleButtons{};
        mantleButtons.jumpPressed = true;

        const auto mantleFrame =
            mantlingPlayer.fixedStep(
                {0.0f, 1.0f},
                mantleButtons,
                1.0f / 120.0f);

        assert(
            mantleFrame.movement.mode ==
            xziel::MovementMode::Mantling);

        assert(
            mantleFrame.movement.cue ==
            xziel::MovementCue::MantleStart);
    }

    // Wall-run probing is geometry driven and stays opt-in through movement
    // capabilities, so classic Zombies maps can leave it disabled.
    {
        xziel::MovementCapabilities capabilities{};
        capabilities.wallRun = true;
        capabilities.wallJump = true;

        xziel::FpsPlayerController wallPlayer(
            {},
            {},
            {},
            capabilities);

        assert(
            wallPlayer.addStaticObstacle(
                {
                    .minimum = {
                        0.34f,
                        -1.60f,
                        -3.20f,
                    },
                    .maximum = {
                        0.62f,
                        1.20f,
                        -1.80f,
                    },
                }));

        xziel::MobileMovementButtons wallButtons{};
        wallButtons.jumpPressed = true;

        auto wallFrame =
            wallPlayer.fixedStep(
                {0.0f, 1.0f},
                wallButtons,
                1.0f / 120.0f);

        assert(
            wallFrame.movement.mode ==
            xziel::MovementMode::Airborne);

        wallButtons.jumpPressed = false;

        wallFrame =
            wallPlayer.fixedStep(
                {0.0f, 1.0f},
                wallButtons,
                1.0f / 120.0f);

        assert(
            wallFrame.movement.mode ==
            xziel::MovementMode::WallRunning);

        assert(
            wallFrame.movement.cue ==
            xziel::MovementCue::WallRunStart);
    }

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
