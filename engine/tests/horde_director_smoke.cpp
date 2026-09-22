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

    // Barricades/doors can change navigation at runtime without rebuilding
    // the director. This is the bridge used by breakable zombie windows.
    xziel::HordeDirector dynamic(navigationConfig);
    assert(dynamic.addDynamicBlocker(
        77,
        {
            .minimum = {-0.75f, -1.60f, 0.60f},
            .maximum = { 0.75f,  0.95f, 0.85f},
        },
        true));
    assert(dynamic.setDynamicBlockerEnabled(77, false));
    assert(!dynamic.setDynamicBlockerEnabled(999, false));

    // Breakable blockers are approached instead of routed around, and the
    // director marks the zombie's attack target so gameplay can tear planks
    // without mistaking the strike for player damage.
    xziel::HordeConfig breakableConfig{};
    breakableConfig.baseZombiesPerRound = 1;
    breakableConfig.zombiesAddedPerRound = 0;
    breakableConfig.maxActive = 1;
    breakableConfig.spawnIntervalSeconds = 0.01f;
    breakableConfig.baseMoveSpeed = 1.0f;
    breakableConfig.maximumMoveSpeed = 1.0f;
    breakableConfig.spawnPointCount = 1;
    breakableConfig.spawnPoints[0] = {0.0f, -1.48f, 2.80f};

    xziel::HordeDirector breakable(breakableConfig);
    assert(breakable.addDynamicBlocker(
        88,
        {
            .minimum = {-0.75f, -1.60f, 0.60f},
            .maximum = { 0.75f,  0.95f, 0.85f},
        },
        true,
        true));

    bool attackedBarrier = false;
    for (int i = 0; i < 1200; ++i) {
        (void) breakable.step(
            {0.0f, -1.48f, -2.20f},
            1.0f / 120.0f);
        attackedBarrier =
            attackedBarrier ||
            breakable.dynamicBlockerAttackCount(88) > 0U;
    }
    assert(attackedBarrier);
    assert(breakable.zombieDynamicBlockerTarget(0) == 88U);

    // Multi-level floor following: zombies keep their feet on authored route
    // surfaces while moving horizontally toward a player on the next level.
    xziel::HordeConfig floorConfig{};
    floorConfig.baseZombiesPerRound = 1;
    floorConfig.zombiesAddedPerRound = 0;
    floorConfig.maxActive = 1;
    floorConfig.spawnIntervalSeconds = 0.01f;
    floorConfig.baseMoveSpeed = 1.0f;
    floorConfig.maximumMoveSpeed = 1.0f;
    floorConfig.spawnPointCount = 1;
    floorConfig.spawnPoints[0] = {0.0f, -1.48f, -2.0f};

    xziel::HordeDirector floors(floorConfig);
    assert(floors.addNavigationFloor(
        {
            .minimum = {-2.0f, -1.68f, -3.0f},
            .maximum = { 2.0f, -1.48f, -0.80f},
        }));
    assert(floors.addNavigationFloor(
        {
            .minimum = {-2.0f, -1.40f, -1.10f},
            .maximum = { 2.0f, -1.20f,  3.00f},
        }));

    assert(floors.navigationFloorCount() == 2U);
    assert(floors.navigationLinkCount() == 1U);

    for (int i = 0; i < 520; ++i) {
        (void) floors.step(
            {0.0f, -1.20f, 2.0f},
            1.0f / 120.0f);
    }

    const auto* climbed = floors.zombie(0);
    assert(climbed != nullptr);
    assert(climbed->frame().position.z > -1.0f);
    assert(climbed->frame().position.y > -1.25f);
    assert(climbed->frame().position.y < -1.15f);

    // Connected floor routing must follow the authored multi-level corridor
    // instead of taking a diagonal shortcut through empty space between rooms.
    xziel::HordeConfig routeConfig{};
    routeConfig.baseZombiesPerRound = 1;
    routeConfig.zombiesAddedPerRound = 0;
    routeConfig.maxActive = 1;
    routeConfig.spawnIntervalSeconds = 0.01f;
    routeConfig.baseMoveSpeed = 1.0f;
    routeConfig.maximumMoveSpeed = 1.0f;
    routeConfig.spawnPointCount = 1;
    routeConfig.spawnPoints[0] = {0.0f, -1.48f, 3.0f};

    xziel::HordeDirector route(routeConfig);

    assert(route.addNavigationFloor(
        {
            .minimum = {-1.0f, -1.68f,  2.0f},
            .maximum = { 1.0f, -1.48f,  4.0f},
        }));

    assert(route.addNavigationFloor(
        {
            .minimum = { 0.8f, -1.68f,  2.0f},
            .maximum = { 3.0f, -1.48f,  4.0f},
        }));

    assert(route.addNavigationFloor(
        {
            .minimum = { 2.8f, -1.50f,  0.8f},
            .maximum = { 4.8f, -1.30f,  2.2f},
        }));

    assert(route.addNavigationFloor(
        {
            .minimum = { 2.8f, -1.32f, -1.2f},
            .maximum = { 4.8f, -1.12f,  1.0f},
        }));

    assert(route.navigationFloorCount() == 4U);
    assert(route.navigationLinkCount() == 3U);

    for (int i = 0; i < 120; ++i) {
        (void) route.step(
            {4.0f, -1.12f, -0.5f},
            1.0f / 120.0f);
    }

    const auto* corridorZombie =
        route.zombie(0);

    assert(corridorZombie != nullptr);

    // During the first corridor leg it should still be moving east through
    // the upper aisle, not cutting diagonally straight at the player.
    assert(
        corridorZombie->frame().position.z >
        2.55f);

    for (int i = 0; i < 1400; ++i) {
        (void) route.step(
            {4.0f, -1.12f, -0.5f},
            1.0f / 120.0f);
    }

    corridorZombie = route.zombie(0);
    assert(corridorZombie != nullptr);
    assert(corridorZombie->frame().position.z < 0.8f);
    assert(corridorZombie->frame().position.y > -1.20f);

    return 0;
}
