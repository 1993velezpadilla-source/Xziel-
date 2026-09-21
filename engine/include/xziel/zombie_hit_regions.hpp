#pragma once

#include "xziel/zombie_actor.hpp"

#include <cstdint>

namespace xziel {

enum class ZombieHitRegion : std::uint8_t {
    None,
    Head,
    Torso,
    Limbs,
};

struct ZombieHitResult {
    bool hit = false;
    ZombieHitRegion region = ZombieHitRegion::None;
    float distance = 0.0f;
    float damageMultiplier = 1.0f;
    Vec3 point{};
    Vec3 normal{};
};

[[nodiscard]] ZombieHitResult raycastZombie(
    const Ray& ray,
    const ZombieActor& zombie,
    float maximumDistance = 1000.0f) noexcept;

[[nodiscard]] float zombieRegionDamageMultiplier(
    ZombieHitRegion region) noexcept;

} // namespace xziel
