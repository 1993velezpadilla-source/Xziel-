#include "xziel/player_vitals.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float positiveOr(
    float value,
    float fallback) noexcept {
    return (!std::isfinite(value) ||
            value <= 0.0f)
        ? fallback
        : value;
}

float safeDt(float value) noexcept {
    if (!std::isfinite(value) ||
        value <= 0.0f) {
        return 0.0f;
    }

    return std::min(
        value,
        0.05f);
}

} // namespace

PlayerVitals::PlayerVitals(
    PlayerVitalsConfig config)
    : config_(config) {
    config_.maxHealth =
        positiveOr(
            config_.maxHealth,
            100.0f);

    config_.regenerationDelaySeconds =
        positiveOr(
            config_.regenerationDelaySeconds,
            4.5f);

    config_.regenerationPerSecond =
        positiveOr(
            config_.regenerationPerSecond,
            22.0f);

    config_.respawnDelaySeconds =
        positiveOr(
            config_.respawnDelaySeconds,
            2.25f);

    config_.respawnInvulnerabilitySeconds =
        std::max(
            0.0f,
            std::isfinite(
                config_.respawnInvulnerabilitySeconds)
                ? config_.respawnInvulnerabilitySeconds
                : 0.75f);

    reset();
}

void PlayerVitals::reset() noexcept {
    frame_ = {};
    frame_.health =
        config_.maxHealth;
    frame_.healthRatio = 1.0f;
    frame_.alive = true;

    secondsSinceDamage_ = 9999.0f;
    deadSeconds_ = 0.0f;
    invulnerabilitySeconds_ = 0.0f;
}

bool PlayerVitals::restoreFullHealth() noexcept {
    if (!frame_.alive) {
        return false;
    }

    const bool changed =
        frame_.health <
        config_.maxHealth;

    frame_.health =
        config_.maxHealth;
    frame_.healthRatio = 1.0f;
    frame_.damageFlash = 0.0f;
    secondsSinceDamage_ = 9999.0f;

    return changed;
}

bool PlayerVitals::applyDamage(
    float damage) noexcept {
    frame_.damagedThisTick = false;
    frame_.diedThisTick = false;

    if (!frame_.alive ||
        frame_.invulnerable ||
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

    frame_.damageFlash = 1.0f;
    frame_.damagedThisTick = true;
    secondsSinceDamage_ = 0.0f;

    if (frame_.health <= 0.0f) {
        frame_.alive = false;
        frame_.diedThisTick = true;
        frame_.deathAlpha = 0.0f;
        deadSeconds_ = 0.0f;
    }

    return true;
}

PlayerVitalsFrame PlayerVitals::step(
    float deltaSeconds) noexcept {
    const float dt =
        safeDt(
            deltaSeconds);

    frame_.damagedThisTick = false;
    frame_.diedThisTick = false;
    frame_.respawnedThisTick = false;

    frame_.damageFlash =
        std::max(
            0.0f,
            frame_.damageFlash -
                dt * 3.7f);

    if (invulnerabilitySeconds_ > 0.0f) {
        invulnerabilitySeconds_ =
            std::max(
                0.0f,
                invulnerabilitySeconds_ -
                    dt);
    }

    frame_.invulnerable =
        invulnerabilitySeconds_ > 0.0f;

    if (!frame_.alive) {
        deadSeconds_ += dt;

        frame_.deathAlpha =
            std::clamp(
                deadSeconds_ /
                    0.55f,
                0.0f,
                1.0f);

        if (config_.autoRespawn &&
            deadSeconds_ >=
                config_.respawnDelaySeconds) {
            respawn();
        }

        return frame_;
    }

    secondsSinceDamage_ += dt;
    frame_.deathAlpha = 0.0f;

    if (secondsSinceDamage_ >=
            config_.regenerationDelaySeconds &&
        frame_.health <
            config_.maxHealth) {
        frame_.health =
            std::min(
                config_.maxHealth,
                frame_.health +
                    config_.regenerationPerSecond *
                    dt);

        frame_.healthRatio =
            std::clamp(
                frame_.health /
                    config_.maxHealth,
                0.0f,
                1.0f);
    }

    return frame_;
}

const PlayerVitalsFrame&
PlayerVitals::frame() const noexcept {
    return frame_;
}

const PlayerVitalsConfig&
PlayerVitals::config() const noexcept {
    return config_;
}

void PlayerVitals::respawn() noexcept {
    const std::uint64_t nextGeneration =
        frame_.generation + 1;

    frame_ = {};
    frame_.health =
        config_.maxHealth;
    frame_.healthRatio = 1.0f;
    frame_.alive = true;
    frame_.invulnerable =
        config_.respawnInvulnerabilitySeconds >
        0.0f;
    frame_.respawnedThisTick = true;
    frame_.generation =
        nextGeneration;

    secondsSinceDamage_ = 9999.0f;
    deadSeconds_ = 0.0f;
    invulnerabilitySeconds_ =
        config_.respawnInvulnerabilitySeconds;
}

} // namespace xziel
