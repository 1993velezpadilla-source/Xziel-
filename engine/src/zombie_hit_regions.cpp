#include "xziel/zombie_hit_regions.hpp"

namespace xziel {

namespace {

ZombieHitResult makeResult(
    const HitscanResult& hit,
    ZombieHitRegion region) noexcept {
    ZombieHitResult result{};

    if (!hit.hit) {
        return result;
    }

    result.hit = true;
    result.region = region;
    result.distance = hit.distance;
    result.damageMultiplier =
        zombieRegionDamageMultiplier(region);
    result.point = hit.point;
    result.normal = hit.normal;

    return result;
}

} // namespace

ZombieHitResult raycastZombie(
    const Ray& ray,
    const ZombieActor& zombie,
    float maximumDistance) noexcept {
    const auto& frame = zombie.frame();
    const auto& config = zombie.config();

    const float feetY = frame.position.y;
    const float torsoBottom =
        feetY + config.bodyHeight * 0.34f;
    const float headBottom =
        feetY + config.bodyHeight * 0.76f;

    const Aabb head{
        .minimum = {
            frame.position.x - config.halfWidth * 0.72f,
            headBottom,
            frame.position.z - config.halfDepth * 0.72f,
        },
        .maximum = {
            frame.position.x + config.halfWidth * 0.72f,
            feetY + config.bodyHeight,
            frame.position.z + config.halfDepth * 0.72f,
        },
    };

    const Aabb torso{
        .minimum = {
            frame.position.x - config.halfWidth,
            torsoBottom,
            frame.position.z - config.halfDepth,
        },
        .maximum = {
            frame.position.x + config.halfWidth,
            headBottom,
            frame.position.z + config.halfDepth,
        },
    };

    const Aabb limbs{
        .minimum = {
            frame.position.x - config.halfWidth,
            feetY,
            frame.position.z - config.halfDepth,
        },
        .maximum = {
            frame.position.x + config.halfWidth,
            torsoBottom,
            frame.position.z + config.halfDepth,
        },
    };

    ZombieHitResult best{};
    best.distance = maximumDistance;

    const auto consider =
        [&](const Aabb& box,
            ZombieHitRegion region) noexcept {
            const auto hit =
                raycastAabb(
                    ray,
                    box,
                    best.hit
                        ? best.distance
                        : maximumDistance);

            if (!hit.hit) {
                return;
            }

            const auto candidate =
                makeResult(hit, region);

            if (!best.hit ||
                candidate.distance <
                    best.distance) {
                best = candidate;
            }
        };

    consider(head, ZombieHitRegion::Head);
    consider(torso, ZombieHitRegion::Torso);
    consider(limbs, ZombieHitRegion::Limbs);

    return best;
}

float zombieRegionDamageMultiplier(
    ZombieHitRegion region) noexcept {
    switch (region) {
        case ZombieHitRegion::Head:
            return 2.0f;
        case ZombieHitRegion::Torso:
            return 1.0f;
        case ZombieHitRegion::Limbs:
            return 0.65f;
        case ZombieHitRegion::None:
        default:
            return 0.0f;
    }
}

} // namespace xziel
