#include "xziel/player_vitals.hpp"

#include <cassert>

int main() {
    xziel::PlayerVitalsConfig config{};
    config.maxHealth = 100.0f;
    config.regenerationDelaySeconds = 0.20f;
    config.regenerationPerSecond = 50.0f;
    config.respawnDelaySeconds = 0.25f;
    config.respawnInvulnerabilitySeconds = 0.10f;

    xziel::PlayerVitals vitals(
        config);

    assert(
        vitals.applyDamage(
            40.0f));

    assert(
        vitals.frame().health ==
        60.0f);

    for (int i = 0;
         i < 24;
         ++i) {
        (void) vitals.step(
            1.0f / 120.0f);
    }

    const float beforeRegen =
        vitals.frame().health;

    for (int i = 0;
         i < 60;
         ++i) {
        (void) vitals.step(
            1.0f / 120.0f);
    }

    assert(
        vitals.frame().health >
        beforeRegen);

    assert(
        vitals.applyDamage(
            500.0f));

    assert(
        !vitals.frame().alive);

    bool respawned = false;

    for (int i = 0;
         i < 60;
         ++i) {
        const auto frame =
            vitals.step(
                1.0f / 120.0f);

        respawned =
            respawned ||
            frame.respawnedThisTick;
    }

    assert(respawned);
    assert(
        vitals.frame().alive);
    assert(
        vitals.frame().health ==
        config.maxHealth);

    // Respawn protection must block immediate spawn damage.
    assert(
        !vitals.applyDamage(
            20.0f));

    xziel::PlayerVitals healTarget(config);
    assert(healTarget.applyDamage(37.0f));
    assert(healTarget.frame().health == 63.0f);
    assert(healTarget.restoreFullHealth());
    assert(healTarget.frame().health == config.maxHealth);
    assert(healTarget.frame().healthRatio == 1.0f);
    assert(!healTarget.restoreFullHealth());

    return 0;
}
