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

enum class WeaponSoundFamily : std::uint8_t {
    Sidearm,
    SubmachineGun,
    AssaultRifle,
    MarksmanRifle,
    Shotgun,
    LightMachineGun,
    SniperRifle,
};

enum class WeaponViewmodelAsset : std::uint8_t {
    Sidearm,
    SubmachineGun,
    AssaultRifle,
    MarksmanRifle,
    Shotgun,
    LightMachineGun,
    SniperRifle,
};

struct WeaponViewmodelPose {
    float x = 0.265f;
    float y = -0.205f;
    float z = 0.220f;

    float scale = 0.64f;

    float yawRadians = -0.055f;
    float pitchRadians = 0.018f;
    float rollRadians = 0.030f;
};

struct WeaponViewmodelProfile {
    WeaponViewmodelAsset asset =
        WeaponViewmodelAsset::AssaultRifle;

    // Calibrated in canonical XZIEL viewmodel space:
    // +X right, +Y up, +Z stock-to-muzzle.
    WeaponViewmodelPose hip{};
    WeaponViewmodelPose ads{
        -0.008f,
        -0.065f,
        0.160f,
        0.58f,
        0.0f,
        0.018f,
        0.0f,
    };

    float verticalFovDegrees = 72.0f;

    float loweringX = 0.030f;
    float loweringY = -0.20f;
    float loweringZ = 0.030f;

    float reloadY = -0.070f;
    float reloadZ = 0.024f;
    float reloadYawRadians = 0.045f;
    float reloadPitchRadians = -0.090f;
    float reloadRollRadians = -0.220f;

    float fireY = 0.016f;
    float fireZ = -0.055f;
    float firePitchRadians = 0.020f;
    float fireRollRadians = 0.020f;
};

struct WeaponProfile {
    WeaponArchetype archetype =
        WeaponArchetype::Sidearm;

    WeaponSoundFamily soundFamily =
        WeaponSoundFamily::Sidearm;

    WeaponConfig controller{};
    WeaponViewmodelProfile viewmodel{};

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
