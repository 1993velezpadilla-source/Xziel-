#pragma once

#include "xziel/weapon.hpp"

#include <cstdint>

namespace xziel {

enum class WeaponArchetype : std::uint8_t {
    Sidearm,
    SubmachineGun,
    AssaultRifle,
    MarksmanRifle,
    Shotgun,
    LightMachineGun,
    SniperRifle,
};

struct WeaponProfile {
    WeaponArchetype archetype =
        WeaponArchetype::Sidearm;

    WeaponConfig controller{};

    float baseDamage = 34.0f;
    float falloffStartMeters = 12.0f;
    float maximumRangeMeters = 30.0f;
    float minimumDamageScale = 0.55f;

    std::uint32_t hitscanPellets = 1;
    float spreadDegrees = 0.0f;
};

[[nodiscard]] WeaponProfile makeWeaponProfile(
    WeaponArchetype archetype) noexcept;

[[nodiscard]] float weaponDamageAtDistance(
    const WeaponProfile& profile,
    float distanceMeters) noexcept;

} // namespace xziel
