#include "xziel/zombie_hit_regions.hpp"

#include <cassert>
#include <cmath>

int main() {
    xziel::ZombieConfig config{};
    config.spawnPosition = {0.0f, 0.0f, 4.0f};
    config.autoRespawn = false;

    xziel::ZombieActor zombie(config);

    const auto head = xziel::raycastZombie(
        xziel::makeViewRay(
            {0.0f, config.bodyHeight * 0.88f, 0.0f},
            0.0f,
            0.0f),
        zombie,
        20.0f);

    assert(head.hit);
    assert(head.region == xziel::ZombieHitRegion::Head);
    assert(std::fabs(head.damageMultiplier - 2.0f) < 0.001f);

    const auto torso = xziel::raycastZombie(
        xziel::makeViewRay(
            {0.0f, config.bodyHeight * 0.54f, 0.0f},
            0.0f,
            0.0f),
        zombie,
        20.0f);

    assert(torso.hit);
    assert(torso.region == xziel::ZombieHitRegion::Torso);

    const auto limbs = xziel::raycastZombie(
        xziel::makeViewRay(
            {0.0f, config.bodyHeight * 0.15f, 0.0f},
            0.0f,
            0.0f),
        zombie,
        20.0f);

    assert(limbs.hit);
    assert(limbs.region == xziel::ZombieHitRegion::Limbs);

    return 0;
}
