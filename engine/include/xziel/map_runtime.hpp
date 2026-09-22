#pragma once

#include "xziel/door.hpp"
#include "xziel/interaction.hpp"
#include "xziel/zombie_window.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

inline constexpr std::size_t kMaxMapBoxes = 128;
inline constexpr std::size_t kMaxMapDoors = 16;
inline constexpr std::size_t kMaxMapWindows = 32;
inline constexpr std::size_t kMaxMapGenericInteractions = 16;
inline constexpr std::size_t kMaxMapZombieSpawns = 32;

struct MapBoxDefinition {
    std::uint32_t id = 0;
    Vec3 center{};
    Vec3 halfExtents{0.5f, 0.5f, 0.5f};
    std::uint32_t materialId = 0;
    bool visible = true;
    bool blocksPlayer = true;
    bool blocksZombies = true;
};

struct MapDoorEntity {
    DoorDefinition door{};
    InteractionTarget interaction{};
};

struct MapWindowEntity {
    ZombieWindowDefinition window{};
    InteractionTarget interaction{};
};

struct MapDefinition {
    std::array<MapBoxDefinition, kMaxMapBoxes> boxes{};
    std::size_t boxCount = 0;

    Vec3 playerSpawnFeet{};
    float playerSpawnYawDegrees = 0.0f;
    bool hasPlayerSpawn = false;

    std::array<Vec3, kMaxMapZombieSpawns> zombieSpawns{};
    std::size_t zombieSpawnCount = 0;

    float arenaMinimumX = 0.0f;
    float arenaMaximumX = 0.0f;
    float arenaMinimumZ = 0.0f;
    float arenaMaximumZ = 0.0f;
    bool hasArenaBounds = false;

    std::array<MapDoorEntity, kMaxMapDoors> doors{};
    std::size_t doorCount = 0;

    std::array<MapWindowEntity, kMaxMapWindows> windows{};
    std::size_t windowCount = 0;

    std::array<InteractionTarget, kMaxMapGenericInteractions>
        interactions{};
    std::size_t interactionCount = 0;
};

struct MapLoadResult {
    bool success = false;
    std::size_t visibleBoxes = 0;
    std::size_t playerColliders = 0;
    std::size_t zombieColliders = 0;
    std::size_t doors = 0;
    std::size_t windows = 0;
    std::size_t interactions = 0;
    std::size_t zombieSpawns = 0;
    bool playerSpawnApplied = false;
    bool arenaBoundsApplied = false;
};

class MapRuntime final {
public:
    void clear(
        FpsPlayerController& player,
        HordeDirector& horde,
        InteractionSystem& interactions) noexcept;

    [[nodiscard]] MapLoadResult load(
        const MapDefinition& definition,
        FpsPlayerController& player,
        HordeDirector& horde,
        InteractionSystem& interactions) noexcept;

    void beginRound() noexcept;

    [[nodiscard]] DoorFrame activateDoor(
        std::uint32_t id,
        FpsPlayerController& player,
        HordeDirector& horde,
        InteractionSystem& interactions,
        ScoreSystem& score) noexcept;

    [[nodiscard]] ZombieWindowFrame stepWindow(
        std::uint32_t id,
        bool playerRebuilding,
        float deltaSeconds,
        FpsPlayerController& player,
        HordeDirector& horde,
        ScoreSystem& score) noexcept;

    [[nodiscard]] const DoorSystem& doors() const noexcept;
    [[nodiscard]] const ZombieWindowSystem& windows() const noexcept;

private:
    DoorSystem doors_{};
    ZombieWindowSystem windows_{};
};

[[nodiscard]] Aabb mapBoxBounds(
    const MapBoxDefinition& box) noexcept;

} // namespace xziel
