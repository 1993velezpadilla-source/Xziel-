#pragma once

#include "xziel/zombie_actor.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace xziel {

inline constexpr std::size_t kMaxHordeZombies = 16;
inline constexpr std::size_t kMaxHordeNavigationObstacles = 8;

struct HordeConfig {
    std::uint32_t startingRound = 1;
    std::uint32_t baseZombiesPerRound = 4;
    std::uint32_t zombiesAddedPerRound = 2;
    std::uint32_t maxActive = 8;

    float spawnIntervalSeconds = 0.70f;
    float interRoundDelaySeconds = 2.20f;

    float baseHealth = 100.0f;
    float healthAddedPerRound = 16.0f;

    float baseMoveSpeed = 0.70f;
    float moveSpeedAddedPerRound = 0.035f;
    float maximumMoveSpeed = 1.45f;

    float separationRadius = 0.72f;
    float separationStrength = 0.62f;
    float minimumSpawnDistanceFromPlayer = 3.0f;

    float arenaMinimumX = -2.82f;
    float arenaMaximumX = 2.82f;
    float arenaMinimumZ = -3.25f;
    float arenaMaximumZ = 3.45f;

    std::array<Vec3, 8> spawnPoints{{
        {-2.35f, -1.48f,  3.15f},
        { 2.35f, -1.48f,  3.15f},
        {-2.55f, -1.48f,  1.55f},
        { 2.55f, -1.48f,  1.55f},
        {-1.55f, -1.48f,  3.30f},
        { 1.55f, -1.48f,  3.30f},
        {-2.65f, -1.48f, -0.10f},
        { 2.65f, -1.48f, -0.10f},
    }};

    std::uint32_t spawnPointCount = 8;
};

struct HordeFrame {
    std::uint32_t round = 1;
    std::uint32_t targetThisRound = 0;
    std::uint32_t spawnedThisRound = 0;
    std::uint32_t killedThisRound = 0;
    std::uint32_t alive = 0;

    bool interRound = false;
    bool spawnedThisTick = false;
    bool roundStartedThisTick = false;
};

class HordeDirector final {
public:
    explicit HordeDirector(
        HordeConfig config = {});

    void reset() noexcept;

    void clearNavigationObstacles() noexcept;

    [[nodiscard]] bool addNavigationObstacle(
        const Aabb& obstacle) noexcept;

    [[nodiscard]] HordeFrame step(
        Vec3 playerFeetPosition,
        float deltaSeconds) noexcept;

    [[nodiscard]] bool damageZombie(
        std::size_t slot,
        float damage) noexcept;

    [[nodiscard]] const ZombieActor*
    zombie(std::size_t slot) const noexcept;

    [[nodiscard]] ZombieActor*
    zombie(std::size_t slot) noexcept;

    [[nodiscard]] std::size_t capacity() const noexcept;
    [[nodiscard]] const HordeFrame& frame() const noexcept;
    [[nodiscard]] const HordeConfig& config() const noexcept;

private:
    [[nodiscard]] std::uint32_t targetForRound(
        std::uint32_t round) const noexcept;

    [[nodiscard]] bool spawnOne(
        Vec3 playerFeetPosition) noexcept;

    [[nodiscard]] Vec3 steeringTargetFor(
        const ZombieActor& actor,
        Vec3 playerFeetPosition) const noexcept;

    void applyCrowdSeparation() noexcept;
    void resolveNavigationPenetration() noexcept;
    void constrainToArena() noexcept;
    void beginNextRound() noexcept;

    HordeConfig config_{};
    HordeFrame frame_{};

    std::array<std::optional<ZombieActor>, kMaxHordeZombies>
        zombies_{};

    std::array<Aabb, kMaxHordeNavigationObstacles>
        navigationObstacles_{};

    std::size_t navigationObstacleCount_ = 0;

    float spawnCooldownSeconds_ = 0.0f;
    float interRoundSeconds_ = 0.0f;
    std::uint32_t nextSpawnPoint_ = 0;
};

} // namespace xziel
