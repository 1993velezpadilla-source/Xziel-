#pragma once

#include <cstdint>

namespace xziel {

struct PlayerVitalsConfig {
    float maxHealth = 100.0f;
    float regenerationDelaySeconds = 4.5f;
    float regenerationPerSecond = 22.0f;
    float respawnDelaySeconds = 2.25f;
    float respawnInvulnerabilitySeconds = 0.75f;
    bool autoRespawn = true;
};

struct PlayerVitalsFrame {
    float health = 100.0f;
    float healthRatio = 1.0f;

    bool alive = true;
    bool invulnerable = false;

    bool damagedThisTick = false;
    bool diedThisTick = false;
    bool respawnedThisTick = false;

    float damageFlash = 0.0f;
    float deathAlpha = 0.0f;

    std::uint64_t generation = 0;
};

class PlayerVitals final {
public:
    explicit PlayerVitals(
        PlayerVitalsConfig config = {});

    void reset() noexcept;

    [[nodiscard]] bool applyDamage(
        float damage) noexcept;

    [[nodiscard]] PlayerVitalsFrame step(
        float deltaSeconds) noexcept;

    [[nodiscard]] const PlayerVitalsFrame&
    frame() const noexcept;

    [[nodiscard]] const PlayerVitalsConfig&
    config() const noexcept;

private:
    void respawn() noexcept;

    PlayerVitalsConfig config_{};
    PlayerVitalsFrame frame_{};

    float secondsSinceDamage_ = 9999.0f;
    float deadSeconds_ = 0.0f;
    float invulnerabilitySeconds_ = 0.0f;
};

} // namespace xziel
