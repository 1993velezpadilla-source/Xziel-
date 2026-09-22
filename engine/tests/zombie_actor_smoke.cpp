#include "xziel/zombie_actor.hpp"

#include <cassert>

int main() {
    xziel::ZombieConfig config{};
    config.moveSpeed = 1.0f;
    config.respawnSeconds = 0.25f;

    xziel::ZombieActor zombie(
        config);

    const float originalZ =
        zombie.frame().position.z;

    for (int i = 0;
         i < 120;
         ++i) {
        (void) zombie.step(
            {
                0.0f,
                -1.48f,
                -2.0f,
            },
            1.0f / 120.0f);
    }

    assert(
        zombie.frame().position.z <
        originalZ);

    const auto bounds =
        zombie.bounds();

    assert(
        bounds.maximum.y >
        bounds.minimum.y);

    assert(
        zombie.applyDamage(34.0f));

    assert(
        zombie.frame().state ==
        xziel::ZombieState::Staggered);

    (void) zombie.step(
        {},
        0.20f);

    assert(
        zombie.frame().state ==
        xziel::ZombieState::Chasing);

    assert(
        zombie.applyDamage(34.0f));

    assert(
        zombie.applyDamage(34.0f));

    assert(
        zombie.frame().state ==
        xziel::ZombieState::Dead);

    const auto deadGeneration =
        zombie.frame().generation;

    for (int i = 0;
         i < 40;
         ++i) {
        (void) zombie.step(
            {},
            1.0f / 120.0f);
    }

    assert(
        zombie.frame().state ==
        xziel::ZombieState::Chasing);

    assert(
        zombie.frame().generation ==
        deadGeneration + 1);

    assert(
        zombie.frame().health ==
        config.maxHealth);

    return 0;
}
