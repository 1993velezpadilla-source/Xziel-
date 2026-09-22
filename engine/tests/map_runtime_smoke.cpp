#include "xziel/map_runtime.hpp"

#include <cassert>

int main() {
    xziel::FpsPlayerController player;
    xziel::HordeDirector horde;
    xziel::InteractionSystem interactions;
    xziel::ScoreSystem score({.startingPoints = 1000});
    xziel::MapRuntime runtime;

    xziel::MapDefinition map{};
    map.hasPlayerSpawn = true;
    map.playerSpawnFeet = {12.0f, -1.58f, -9.0f};
    map.playerSpawnYawDegrees = 42.0f;
    map.hasArenaBounds = true;
    map.arenaMinimumX = -40.0f;
    map.arenaMaximumX = 40.0f;
    map.arenaMinimumZ = -35.0f;
    map.arenaMaximumZ = 45.0f;
    map.zombieSpawns[0] = {-12.0f, -1.58f, 8.0f};
    map.zombieSpawns[1] = { 14.0f, -1.58f, 9.0f};
    map.zombieSpawnCount = 2;

    map.floors[0] = {
        .id = 1000U,
        .bounds = {
            .minimum = {-20.0f, -1.78f, -20.0f},
            .maximum = { 20.0f, -1.58f,  20.0f},
        },
    };
    map.floorCount = 1;

    map.boxes[0] = {
        .id = 1,
        .center = {0.0f, -0.30f, 0.0f},
        .halfExtents = {0.50f, 0.80f, 0.50f},
        .materialId = 1,
        .visible = true,
        .blocksPlayer = true,
        .blocksZombies = true,
    };
    map.boxCount = 1;

    map.doors[0].door = {
        .id = 100,
        .blocker = {
            .minimum = {-0.8f, -1.6f, 1.0f},
            .maximum = { 0.8f,  1.0f, 1.2f},
        },
        .cost = 750,
    };
    map.doors[0].interaction = {
        .id = 100,
        .kind = xziel::InteractionKind::Door,
        .position = {0.0f, -0.4f, 0.9f},
        .maximumDistance = 1.75f,
        .minimumFacingDot = 0.1f,
        .priority = 1.2f,
        .holdSeconds = 0.15f,
        .cost = 750,
    };
    map.doorCount = 1;

    map.windows[0].window = {
        .id = 200,
        .blocker = {
            .minimum = {-0.7f, -1.6f, 2.0f},
            .maximum = { 0.7f,  0.9f, 2.2f},
        },
        .barricade = {
            .maximumPlanks = 2,
            .zombieTearSeconds = 0.10f,
            .rebuildSeconds = 0.10f,
            .rebuildPointsPerPlank = 10,
            .maximumRebuildPointsPerRound = 20,
        },
    };
    map.windows[0].interaction = {
        .id = 200,
        .kind = xziel::InteractionKind::Use,
        .position = {0.0f, -0.2f, 1.9f},
        .maximumDistance = 1.5f,
        .minimumFacingDot = 0.1f,
        .priority = 1.1f,
        .holdSeconds = 0.0f,
    };
    map.windowCount = 1;

    map.interactions[0] = {
        .id = 300,
        .kind = xziel::InteractionKind::Switch,
        .position = {-1.0f, -0.3f, 0.0f},
        .maximumDistance = 1.4f,
    };
    map.interactionCount = 1;

    const auto loaded = runtime.load(
        map,
        player,
        horde,
        interactions);

    assert(loaded.success);
    assert(loaded.visibleBoxes == 1);
    assert(loaded.playerColliders == 1);
    assert(loaded.zombieColliders == 1);
    assert(loaded.walkableFloors == 1);
    assert(loaded.doors == 1);
    assert(loaded.windows == 1);
    assert(loaded.interactions == 3);
    assert(loaded.playerSpawnApplied);
    assert(loaded.arenaBoundsApplied);
    assert(loaded.zombieSpawns == 2);
    assert(player.frame().feetPosition.x == 12.0f);
    assert(player.frame().feetPosition.z == -9.0f);
    assert(player.frame().yawDegrees == 42.0f);
    assert(horde.config().spawnPointCount == 2);
    assert(horde.config().spawnPoints[0].x == -12.0f);
    assert(horde.config().arenaMinimumX == -40.0f);
    assert(horde.config().arenaMaximumZ == 45.0f);

    const auto door = runtime.activateDoor(
        100,
        player,
        horde,
        interactions,
        score);
    assert(door.openedThisTick);
    assert(door.open);
    assert(score.frame().total == 250);

    runtime.beginRound();

    // Sanctum-sized capacity proof: progression doors + fitted barricades must
    // coexist in the same native map without exhausting dynamic blocker pools.
    {
        xziel::FpsPlayerController sanctumPlayer;
        xziel::HordeDirector sanctumHorde;
        xziel::InteractionSystem sanctumInteractions;
        xziel::MapRuntime sanctumRuntime;
        xziel::MapDefinition sanctum{};

        for (std::size_t i = 0; i < 7; ++i) {
            const std::uint32_t id =
                2000U + static_cast<std::uint32_t>(i);
            sanctum.doors[i].door = {
                .id = id,
                .blocker = {
                    .minimum = {
                        -0.2f + static_cast<float>(i),
                        -1.58f,
                        0.0f,
                    },
                    .maximum = {
                        0.2f + static_cast<float>(i),
                        1.0f,
                        0.2f,
                    },
                },
                .cost = 750U,
            };
            sanctum.doors[i].interaction = {
                .id = id,
                .kind = xziel::InteractionKind::Door,
                .position = {
                    static_cast<float>(i),
                    -0.40f,
                    0.0f,
                },
            };
        }
        sanctum.doorCount = 7;

        for (std::size_t i = 0; i < 28; ++i) {
            const std::uint32_t id =
                3000U + static_cast<std::uint32_t>(i);
            sanctum.windows[i].window = {
                .id = id,
                .blocker = {
                    .minimum = {
                        -0.8f,
                        -1.58f,
                        1.0f + static_cast<float>(i),
                    },
                    .maximum = {
                        0.8f,
                        1.0f,
                        1.2f + static_cast<float>(i),
                    },
                },
                .barricade = {
                    .maximumPlanks = 6,
                },
            };
            sanctum.windows[i].interaction = {
                .id = id,
                .kind = xziel::InteractionKind::Use,
                .position = {
                    0.0f,
                    -0.30f,
                    0.9f + static_cast<float>(i),
                },
            };
        }
        sanctum.windowCount = 28;

        const auto loadedSanctum =
            sanctumRuntime.load(
                sanctum,
                sanctumPlayer,
                sanctumHorde,
                sanctumInteractions);

        assert(loadedSanctum.success);
        assert(loadedSanctum.doors == 7);
        assert(loadedSanctum.windows == 28);
        assert(loadedSanctum.interactions == 35);
        assert(sanctumRuntime.doors().count() == 7);
        assert(sanctumRuntime.windows().count() == 28);
    }

    return 0;
}
