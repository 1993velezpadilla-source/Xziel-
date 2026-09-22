#include "xziel/map_runtime.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

bool finiteVec3(Vec3 value) noexcept {
    return std::isfinite(value.x) &&
        std::isfinite(value.y) &&
        std::isfinite(value.z);
}

} // namespace

Aabb mapBoxBounds(
    const MapBoxDefinition& box) noexcept {
    const Vec3 half{
        std::max(0.001f, std::fabs(box.halfExtents.x)),
        std::max(0.001f, std::fabs(box.halfExtents.y)),
        std::max(0.001f, std::fabs(box.halfExtents.z)),
    };

    return {
        .minimum = {
            box.center.x - half.x,
            box.center.y - half.y,
            box.center.z - half.z,
        },
        .maximum = {
            box.center.x + half.x,
            box.center.y + half.y,
            box.center.z + half.z,
        },
    };
}

void MapRuntime::clear(
    FpsPlayerController& player,
    HordeDirector& horde,
    InteractionSystem& interactions) noexcept {
    interactions.clearTargets();
    player.clearWalkableSurfaces();
    player.clearStaticObstacles();
    player.clearDynamicObstacles();
    horde.clearNavigationObstacles();
    horde.clearDynamicBlockers();
    doors_.clear();
    windows_.clear();
}

MapLoadResult MapRuntime::load(
    const MapDefinition& definition,
    FpsPlayerController& player,
    HordeDirector& horde,
    InteractionSystem& interactions) noexcept {
    MapLoadResult result{};

    if (definition.boxCount > definition.boxes.size() ||
        definition.floorCount > definition.floors.size() ||
        definition.doorCount > definition.doors.size() ||
        definition.windowCount > definition.windows.size() ||
        definition.interactionCount > definition.interactions.size() ||
        definition.zombieSpawnCount > definition.zombieSpawns.size()) {
        return result;
    }

    if (definition.hasPlayerSpawn &&
        !finiteVec3(definition.playerSpawnFeet)) {
        return result;
    }

    if (definition.hasArenaBounds &&
        (!std::isfinite(definition.arenaMinimumX) ||
         !std::isfinite(definition.arenaMaximumX) ||
         !std::isfinite(definition.arenaMinimumZ) ||
         !std::isfinite(definition.arenaMaximumZ) ||
         definition.arenaMinimumX >= definition.arenaMaximumX ||
         definition.arenaMinimumZ >= definition.arenaMaximumZ)) {
        return result;
    }

    for (std::size_t i = 0;
         i < definition.zombieSpawnCount;
         ++i) {
        if (!finiteVec3(definition.zombieSpawns[i])) {
            return result;
        }
    }

    clear(player, horde, interactions);

    if (definition.hasArenaBounds) {
        if (!player.setHorizontalBounds(
                definition.arenaMinimumX,
                definition.arenaMaximumX,
                definition.arenaMinimumZ,
                definition.arenaMaximumZ) ||
            !horde.setArenaBounds(
                definition.arenaMinimumX,
                definition.arenaMaximumX,
                definition.arenaMinimumZ,
                definition.arenaMaximumZ)) {
            clear(player, horde, interactions);
            return {};
        }
        result.arenaBoundsApplied = true;
    }

    if (definition.hasPlayerSpawn) {
        player.setSpawn(
            definition.playerSpawnFeet,
            definition.playerSpawnYawDegrees);
        result.playerSpawnApplied = true;
    }

    if (definition.zombieSpawnCount > 0U) {
        if (!horde.setSpawnPoints(
                definition.zombieSpawns.data(),
                definition.zombieSpawnCount)) {
            clear(player, horde, interactions);
            return {};
        }
        result.zombieSpawns =
            definition.zombieSpawnCount;
    }

    for (std::size_t i = 0;
         i < definition.floorCount;
         ++i) {
        const auto& floor =
            definition.floors[i];

        if (floor.id == 0U ||
            !finiteVec3(floor.bounds.minimum) ||
            !finiteVec3(floor.bounds.maximum) ||
            floor.bounds.minimum.x >
                floor.bounds.maximum.x ||
            floor.bounds.minimum.y >
                floor.bounds.maximum.y ||
            floor.bounds.minimum.z >
                floor.bounds.maximum.z ||
            !player.addWalkableSurface(
                floor.bounds)) {
            clear(player, horde, interactions);
            return {};
        }

        ++result.walkableFloors;
    }

    for (std::size_t i = 0; i < definition.boxCount; ++i) {
        const auto& box = definition.boxes[i];
        if (box.id == 0U ||
            !finiteVec3(box.center) ||
            !finiteVec3(box.halfExtents)) {
            clear(player, horde, interactions);
            return {};
        }

        const Aabb bounds = mapBoxBounds(box);

        if (box.visible) {
            ++result.visibleBoxes;
        }
        if (box.blocksPlayer) {
            if (!player.addStaticObstacle(bounds)) {
                clear(player, horde, interactions);
                return {};
            }
            ++result.playerColliders;
        }
        if (box.blocksZombies) {
            if (!horde.addNavigationObstacle(bounds)) {
                clear(player, horde, interactions);
                return {};
            }
            ++result.zombieColliders;
        }
    }

    for (std::size_t i = 0; i < definition.doorCount; ++i) {
        const auto& entity = definition.doors[i];
        if (entity.door.id == 0U ||
            entity.interaction.id != entity.door.id ||
            entity.interaction.kind != InteractionKind::Door ||
            !doors_.addDoor(entity.door, horde, player) ||
            !interactions.addTarget(entity.interaction)) {
            clear(player, horde, interactions);
            return {};
        }
        ++result.doors;
        ++result.interactions;
    }

    for (std::size_t i = 0; i < definition.windowCount; ++i) {
        const auto& entity = definition.windows[i];
        if (entity.window.id == 0U ||
            entity.interaction.id != entity.window.id ||
            !windows_.addWindow(entity.window, horde, player) ||
            !interactions.addTarget(entity.interaction)) {
            clear(player, horde, interactions);
            return {};
        }
        ++result.windows;
        ++result.interactions;
    }

    for (std::size_t i = 0; i < definition.interactionCount; ++i) {
        if (!interactions.addTarget(definition.interactions[i])) {
            clear(player, horde, interactions);
            return {};
        }
        ++result.interactions;
    }

    result.success = true;
    return result;
}

void MapRuntime::beginRound() noexcept {
    windows_.beginRound();
}

DoorFrame MapRuntime::activateDoor(
    std::uint32_t id,
    FpsPlayerController& player,
    HordeDirector& horde,
    InteractionSystem& interactions,
    ScoreSystem& score) noexcept {
    auto frame = doors_.activate(
        id,
        horde,
        player,
        score);

    if (frame.openedThisTick) {
        (void) interactions.setTargetEnabled(id, false);
    }

    return frame;
}

ZombieWindowFrame MapRuntime::stepWindow(
    std::uint32_t id,
    bool playerRebuilding,
    float deltaSeconds,
    FpsPlayerController& player,
    HordeDirector& horde,
    ScoreSystem& score) noexcept {
    return windows_.stepFromHorde(
        id,
        playerRebuilding,
        deltaSeconds,
        horde,
        player,
        score);
}

const DoorSystem& MapRuntime::doors() const noexcept {
    return doors_;
}

const ZombieWindowSystem& MapRuntime::windows() const noexcept {
    return windows_;
}

} // namespace xziel
