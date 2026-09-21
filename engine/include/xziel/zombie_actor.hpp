#pragma once

#include "xziel/hitscan.hpp"

#include <cstdint>

namespace xziel {

enum class ZombieState : std::uint8_t {
    Chasing,
    Staggered,
    Dead,
};

struct ZombieConfig {
    Vec3 spawnPosition{
        0.0f,
        -1.48f,
        2.45f,
    };

    float maxHealth = 100.0f;
    float moveSpeed = 0.72f;
    float stopDistance = 1.05f;
    float staggerSeconds = 0.12f;
    float respawnSeconds = 1.80f;

    float halfWidth = 0.38f;
    float bodyHeight = 1.86f;
    float halfDepth = 0.34f;

    bool autoRespawn = true;
};

struct ZombieFrame {
    ZombieState state = ZombieState::Chasing;
    Vec3 position{};

    float health = 100.0f;
    float healthRatio = 1.0f;
    float yawDegrees = 180.0f;
    float stridePhase = 0.0f;

    bool inAttackRange = false;
    std::uint64_t generation = 0;
};

class ZombieActor final {
public:
    explicit ZombieActor(
        ZombieConfig config = {});

    void reset() noexcept;

    [[nodiscard]] ZombieFrame step(
        Vec3 playerFeetPosition,
        float deltaSeconds) noexcept;

    [[nodiscard]] bool applyDamage(
        float damage) noexcept;

    [[nodiscard]] Aabb bounds() const noexcept;

    [[nodiscard]] const ZombieFrame&
    frame() const noexcept;

    [[nodiscard]] const ZombieConfig&
    config() const noexcept;

private:
    void respawn() noexcept;

    ZombieConfig config_{};
    ZombieFrame frame_{};

    float stateSeconds_ = 0.0f;
};

} // namespace xziel
