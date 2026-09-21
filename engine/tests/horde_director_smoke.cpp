#include "xziel/horde_director.hpp"

#include <cassert>
#include <cstddef>

int main() {
    xziel::HordeConfig config{};
    config.baseZombiesPerRound = 2;
    config.zombiesAddedPerRound = 1;
    config.maxActive = 2;
    config.spawnIntervalSeconds = 0.01f;
    config.interRoundDelaySeconds = 0.05f;
    config.baseMoveSpeed = 0.20f;

    xziel::HordeDirector horde(
        config);

    for (int i = 0;
         i < 20;
         ++i) {
        (void) horde.step(
            {
                0.0f,
                -1.48f,
                -2.0f,
            },
            0.01f);
    }

    assert(
        horde.frame().spawnedThisRound ==
        2U);

    std::size_t killed = 0;

    for (std::size_t slot = 0;
         slot < horde.capacity();
         ++slot) {
        if (horde.zombie(slot) == nullptr) {
            continue;
        }

        assert(
            horde.damageZombie(
                slot,
                1000.0f));

        ++killed;
    }

    assert(killed == 2U);

    for (int i = 0;
         i < 20;
         ++i) {
        (void) horde.step(
            {},
            0.01f);
    }

    assert(
        horde.frame().round >=
        2U);

    assert(
        horde.frame().targetThisRound ==
        3U);

    // Obstacle steering: a zombie spawned behind a central blocker must route
    // around it instead of tunneling through the prop.
    xziel::HordeConfig navigationConfig{};
    navigationConfig.baseZombiesPerRound = 1;
    navigationConfig.zombiesAddedPerRound = 0;
    navigationConfig.maxActive = 1;
    navigationConfig.spawnIntervalSeconds = 0.01f;
    navigationConfig.baseMoveSpeed = 1.0f;
    navigationConfig.maximumMoveSpeed = 1.0f;
    navigationConfig.spawnPointCount = 1;
    navigationConfig.spawnPoints[0] = {
        0.0f,
        -1.48f,
        2.80f,
    };

    xziel::HordeDirector navigation(
        navigationConfig);

    assert(
        navigation.addNavigationObstacle(
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
         i < 1600;
         ++i) {
        (void) navigation.step(
            {
                0.0f,
                -1.48f,
                -2.20f,
            },
            1.0f / 120.0f);
    }

    const auto* routed =
        navigation.zombie(0);

    assert(routed != nullptr);

    const auto routedPosition =
        routed->frame().position;

    assert(
        routedPosition.z <
        -0.45f);

    const bool insideObstacle =
        routedPosition.x >
            -0.95f &&
        routedPosition.x <
            0.95f &&
        routedPosition.z >
            -0.60f &&
        routedPosition.z <
            1.30f;

    assert(!insideObstacle);

    return 0;
}
