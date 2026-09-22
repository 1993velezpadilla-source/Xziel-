#include "xziel/zombie_actor.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

constexpr float kPi =
    3.14159265358979323846f;

constexpr float kRadiansToDegrees =
    180.0f / kPi;

float safePositive(
    float value,
    float fallback) noexcept {
    if (!std::isfinite(value) ||
        value <= 0.0f) {
        return fallback;
    }

    return value;
}

} // namespace

ZombieActor::ZombieActor(
    ZombieConfig config)
    : config_(config) {
    config_.maxHealth =
        safePositive(
            config_.maxHealth,
            100.0f);

    config_.moveSpeed =
        safePositive(
            config_.moveSpeed,
            0.72f);

    config_.stopDistance =
        safePositive(
            config_.stopDistance,
            1.05f);

    config_.staggerSeconds =
        safePositive(
            config_.staggerSeconds,
            0.12f);

    config_.respawnSeconds =
        safePositive(
            config_.respawnSeconds,
            1.80f);

    config_.attackIntervalSeconds =
        safePositive(
            config_.attackIntervalSeconds,
            0.85f);

    config_.attackDamage =
        safePositive(
            config_.attackDamage,
            34.0f);

    config_.halfWidth =
        safePositive(
            config_.halfWidth,
            0.38f);

    config_.bodyHeight =
        safePositive(
            config_.bodyHeight,
            1.86f);

    config_.halfDepth =
        safePositive(
            config_.halfDepth,
            0.34f);

    reset();
}

void ZombieActor::reset() noexcept {
    frame_ = {};
    frame_.state =
        ZombieState::Chasing;
    frame_.position =
        config_.spawnPosition;
    frame_.health =
        config_.maxHealth;
    frame_.healthRatio = 1.0f;
    frame_.yawDegrees = 180.0f;
    frame_.stridePhase = 0.0f;
    frame_.inAttackRange = false;
    frame_.attackThisTick = false;
    frame_.generation = 0;

    stateSeconds_ = 0.0f;
    attackCooldownSeconds_ = 0.0f;
}

ZombieFrame ZombieActor::step(
    Vec3 playerFeetPosition,
    float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) ||
         deltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(
              deltaSeconds,
              0.05f);

    frame_.inAttackRange = false;
    frame_.attackThisTick = false;
    stateSeconds_ += dt;

    attackCooldownSeconds_ =
        std::max(
            0.0f,
            attackCooldownSeconds_ -
                dt);

    if (frame_.state ==
        ZombieState::Dead) {
        if (config_.autoRespawn &&
            stateSeconds_ >=
                config_.respawnSeconds) {
            respawn();
        }

        return frame_;
    }

    const float dx =
        playerFeetPosition.x -
        frame_.position.x;

    const float dz =
        playerFeetPosition.z -
        frame_.position.z;

    const float distanceSquared =
        dx * dx +
        dz * dz;

    if (distanceSquared >
        1.0e-8f) {
        frame_.yawDegrees =
            std::atan2(
                dx,
                dz) *
            kRadiansToDegrees;
    }

    if (frame_.state ==
        ZombieState::Staggered) {
        if (stateSeconds_ >=
            config_.staggerSeconds) {
            frame_.state =
                ZombieState::Chasing;
            stateSeconds_ = 0.0f;
        }

        return frame_;
    }

    const float distance =
        std::sqrt(
            std::max(
                distanceSquared,
                0.0f));

    if (distance <=
        config_.stopDistance) {
        frame_.inAttackRange = true;

        if (attackCooldownSeconds_ <= 0.0f) {
            frame_.attackThisTick = true;
            attackCooldownSeconds_ =
                config_.attackIntervalSeconds;
        }

        return frame_;
    }

    if (distance >
        1.0e-4f) {
        const float inverseDistance =
            1.0f /
            distance;

        const float travel =
            std::min(
                config_.moveSpeed * dt,
                std::max(
                    0.0f,
                    distance -
                        config_.stopDistance));

        frame_.position.x +=
            dx *
            inverseDistance *
            travel;

        frame_.position.z +=
            dz *
            inverseDistance *
            travel;

        frame_.stridePhase =
            std::fmod(
                frame_.stridePhase +
                    travel *
                    1.35f,
                1.0f);
    }

    return frame_;
}

bool ZombieActor::applyDamage(
    float damage) noexcept {
    if (frame_.state ==
            ZombieState::Dead ||
        !std::isfinite(damage) ||
        damage <= 0.0f) {
        return false;
    }

    frame_.health =
        std::max(
            0.0f,
            frame_.health -
                damage);

    frame_.healthRatio =
        std::clamp(
            frame_.health /
                config_.maxHealth,
            0.0f,
            1.0f);

    stateSeconds_ = 0.0f;

    if (frame_.health <= 0.0f) {
        frame_.state =
            ZombieState::Dead;
        frame_.inAttackRange = false;
    } else {
        frame_.state =
            ZombieState::Staggered;
    }

    return true;
}

void ZombieActor::translateHorizontal(
    float deltaX,
    float deltaZ) noexcept {
    if (std::isfinite(deltaX)) {
        frame_.position.x += deltaX;
    }

    if (std::isfinite(deltaZ)) {
        frame_.position.z += deltaZ;
    }
}

Aabb ZombieActor::bounds() const noexcept {
    return {
        .minimum = {
            frame_.position.x -
                config_.halfWidth,
            frame_.position.y,
            frame_.position.z -
                config_.halfDepth,
        },
        .maximum = {
            frame_.position.x +
                config_.halfWidth,
            frame_.position.y +
                config_.bodyHeight,
            frame_.position.z +
                config_.halfDepth,
        },
    };
}

const ZombieFrame&
ZombieActor::frame() const noexcept {
    return frame_;
}

const ZombieConfig&
ZombieActor::config() const noexcept {
    return config_;
}

void ZombieActor::respawn() noexcept {
    const std::uint64_t nextGeneration =
        frame_.generation + 1;

    frame_ = {};
    frame_.state =
        ZombieState::Chasing;
    frame_.position =
        config_.spawnPosition;
    frame_.health =
        config_.maxHealth;
    frame_.healthRatio = 1.0f;
    frame_.yawDegrees = 180.0f;
    frame_.stridePhase = 0.0f;
    frame_.inAttackRange = false;
    frame_.attackThisTick = false;
    frame_.generation =
        nextGeneration;

    stateSeconds_ = 0.0f;
    attackCooldownSeconds_ = 0.0f;
}

} // namespace xziel
