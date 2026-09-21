#include "xziel/horde_director.hpp"

#include <cassert>
#include <cstddef>

int main() {
    xziel::HordeConfig config{};
    config.baseZombiesPerRound = 2;
    config.zombiesAddedPerRound = 1;
    config.maxActive = 2;
    config.spawnIntervalSeconds = 0.01f;
    config.interRoundDelaySeconds = 0.05f;
    config.baseMoveSpeed = 0.20f;

    xziel::HordeDirector horde(
        config);

    for (int i = 0;
         i < 20;
         ++i) {
        (void) horde.step(
            {
                0.0f,
                -1.48f,
                -2.0f,
            },
            0.01f);
    }

    assert(
        horde.frame().spawnedThisRound ==
        2U);

    std::size_t killed = 0;

    for (std::size_t slot = 0;
         slot < horde.capacity();
         ++slot) {
        if (horde.zombie(slot) == nullptr) {
            continue;
        }

        assert(
            horde.damageZombie(
                slot,
                1000.0f));

        ++killed;
    }

    assert(killed == 2U);

    for (int i = 0;
         i < 20;
         ++i) {
        (void) horde.step(
            {},
            0.01f);
    }

    assert(
        horde.frame().round >=
        2U);

    assert(
        horde.frame().targetThisRound ==
        3U);

    return 0;
}
