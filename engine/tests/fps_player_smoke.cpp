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

    // Authored multi-level maps must be able to descend below the player
    // spawn floor. The legacy config floor must not clamp or fake grounded
    // state once walkable surfaces are installed.
    {
        xziel::FpsPlayerController multiFloorPlayer;
        multiFloorPlayer.setSpawn(
            {0.0f, 1.0f, 0.0f},
            0.0f);
        multiFloorPlayer.clearWalkableSurfaces();

        assert(
            multiFloorPlayer.addWalkableSurface(
                {
                    .minimum = {-2.0f, -0.10f, -2.0f},
                    .maximum = { 2.0f,  0.00f,  2.0f},
                }));

        xziel::FpsPlayerFrame lower{};
        for (int i = 0; i < 240; ++i) {
            lower =
                multiFloorPlayer.fixedStep(
                    {},
                    {},
                    1.0f / 120.0f);
        }

        assert(lower.feetPosition.y < 0.01f);
        assert(lower.feetPosition.y > -0.01f);
        assert(
            lower.movement.mode !=
            xziel::MovementMode::Airborne);
    }

    // Pitch is hard bounded even under absurd input.
    view.look = {0.0f, 100.0f};

    player.sampleViewInput(
        view,
        1.0f / 60.0f);

    assert(
        player.frame().pitchDegrees <=
        82.0001f);

    // Runtime collision gates let doors/windows open without rebuilding
    // player collision state.
    {
        xziel::FpsPlayerController dynamicPlayer;
        assert(dynamicPlayer.addDynamicObstacle(
            501,
            {
                .minimum = {-0.58f, -1.60f, -0.25f},
                .maximum = { 0.58f,  0.95f,  0.95f},
            },
            true));

        xziel::FpsPlayerFrame blocked{};
        for (int i = 0; i < 360; ++i) {
            blocked = dynamicPlayer.fixedStep(
                {0.0f, 1.0f},
                {},
                1.0f / 120.0f);
        }
        assert(blocked.feetPosition.z < -0.45f);

        assert(dynamicPlayer.setDynamicObstacleEnabled(501, false));
        for (int i = 0; i < 360; ++i) {
            blocked = dynamicPlayer.fixedStep(
                {0.0f, 1.0f},
                {},
                1.0f / 120.0f);
        }
        assert(blocked.feetPosition.z > 0.95f);
    }

    // Authored walkable surfaces support real multi-level maps. Crossing a
    // <=34 cm overlap step raises the player without changing the global
    // emergency floor or treating the slab as a horizontal wall.
    {
        xziel::FpsPlayerController stairPlayer;
        stairPlayer.clearWalkableSurfaces();
        assert(stairPlayer.addWalkableSurface(
            {
                .minimum = {-2.0f, -1.68f, -3.0f},
                .maximum = { 2.0f, -1.48f, -0.80f},
            }));
        assert(stairPlayer.addWalkableSurface(
            {
                .minimum = {-2.0f, -1.40f, -1.10f},
                .maximum = { 2.0f, -1.20f,  2.50f},
            }));
        stairPlayer.setSpawn(
            {0.0f, -1.48f, -2.0f},
            0.0f);

        xziel::FpsPlayerFrame stairFrame{};
        for (int i = 0; i < 120; ++i) {
            stairFrame =
                stairPlayer.fixedStep(
                    {0.0f, 1.0f},
                    {},
                    1.0f / 120.0f);
        }

        assert(stairFrame.feetPosition.z > -1.0f);
        assert(stairFrame.feetPosition.y > -1.25f);
        assert(stairFrame.feetPosition.y < -1.15f);
    }

    return 0;
}
