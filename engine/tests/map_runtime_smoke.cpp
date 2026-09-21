#include "xziel/map_runtime.hpp"

#include <cassert>

int main() {
    xziel::FpsPlayerController player;
    xziel::HordeDirector horde;
    xziel::InteractionSystem interactions;
    xziel::ScoreSystem score({.startingPoints = 1000});
    xziel::MapRuntime runtime;

    xziel::MapDefinition map{};
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
    assert(loaded.doors == 1);
    assert(loaded.windows == 1);
    assert(loaded.interactions == 3);

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

    return 0;
}
