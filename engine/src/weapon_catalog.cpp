#include "xziel/weapon_catalog.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

WeaponProfile makeWeaponProfile(
    WeaponArchetype archetype) noexcept {
    WeaponProfile profile{};
    profile.archetype = archetype;

    switch (archetype) {
        case WeaponArchetype::Sidearm:
            profile.viewmodel.asset =
                WeaponViewmodelAsset::Sidearm;
            profile.controller.magazineSize = 12;
            profile.controller.startingReserve = 72;
            profile.controller.fireIntervalSeconds = 0.18f;
            profile.controller.reloadSeconds = 1.35f;
            profile.controller.adsInSeconds = 0.12f;
            profile.controller.adsOutSeconds = 0.10f;
            profile.controller.recoilPitchDegrees = 0.66f;
            profile.controller.recoilYawDegrees = 0.22f;
            profile.controller.automatic = false;
            profile.baseDamage = 38.0f;
            profile.falloffStartMeters = 14.0f;
            profile.maximumRangeMeters = 28.0f;
            profile.minimumDamageScale = 0.55f;
            break;

        case WeaponArchetype::SubmachineGun:
            profile.viewmodel.asset =
                WeaponViewmodelAsset::SubmachineGun;
            profile.controller.magazineSize = 32;
            profile.controller.startingReserve = 192;
            profile.controller.fireIntervalSeconds = 0.075f;
            profile.controller.reloadSeconds = 1.62f;
            profile.controller.adsInSeconds = 0.11f;
            profile.controller.adsOutSeconds = 0.09f;
            profile.controller.recoilPitchDegrees = 0.50f;
            profile.controller.recoilYawDegrees = 0.34f;
            profile.controller.automatic = true;
            profile.baseDamage = 24.0f;
            profile.falloffStartMeters = 9.5f;
            profile.maximumRangeMeters = 24.0f;
            profile.minimumDamageScale = 0.44f;
            break;

        case WeaponArchetype::AssaultRifle:
            profile.viewmodel.asset =
                WeaponViewmodelAsset::AssaultRifle;
            profile.controller.magazineSize = 30;
            profile.controller.startingReserve = 180;
            profile.controller.fireIntervalSeconds = 0.095f;
            profile.controller.reloadSeconds = 1.82f;
            profile.controller.adsInSeconds = 0.145f;
            profile.controller.adsOutSeconds = 0.11f;
            profile.controller.recoilPitchDegrees = 0.72f;
            profile.controller.recoilYawDegrees = 0.28f;
            profile.controller.automatic = true;
            profile.baseDamage = 34.0f;
            profile.falloffStartMeters = 20.0f;
            profile.maximumRangeMeters = 42.0f;
            profile.minimumDamageScale = 0.60f;
            break;

        case WeaponArchetype::MarksmanRifle:
            profile.viewmodel.asset =
                WeaponViewmodelAsset::MarksmanRifle;
            profile.controller.magazineSize = 12;
            profile.controller.startingReserve = 72;
            profile.controller.fireIntervalSeconds = 0.24f;
            profile.controller.reloadSeconds = 1.95f;
            profile.controller.adsInSeconds = 0.20f;
            profile.controller.adsOutSeconds = 0.13f;
            profile.controller.fireRequiresAds = true;
            profile.controller.minimumAdsAlphaToFire = 0.90f;
            profile.controller.triggerBufferSeconds = 0.32f;
            profile.controller.recoilPitchDegrees = 1.15f;
            profile.controller.recoilYawDegrees = 0.20f;
            profile.controller.automatic = false;
            profile.baseDamage = 58.0f;
            profile.falloffStartMeters = 32.0f;
            profile.maximumRangeMeters = 62.0f;
            profile.minimumDamageScale = 0.68f;
            break;

        case WeaponArchetype::Shotgun:
            profile.viewmodel.asset =
                WeaponViewmodelAsset::Shotgun;
            profile.controller.magazineSize = 8;
            profile.controller.startingReserve = 48;
            profile.controller.fireIntervalSeconds = 0.72f;
            profile.controller.reloadSeconds = 2.25f;
            profile.controller.adsInSeconds = 0.18f;
            profile.controller.adsOutSeconds = 0.12f;
            profile.controller.recoilPitchDegrees = 2.10f;
            profile.controller.recoilYawDegrees = 0.44f;
            profile.controller.automatic = false;
            profile.baseDamage = 18.0f;
            profile.falloffStartMeters = 6.0f;
            profile.maximumRangeMeters = 18.0f;
            profile.minimumDamageScale = 0.20f;
            profile.hitscanPellets = 8;
            profile.spreadDegrees = 4.8f;
            break;

        case WeaponArchetype::LightMachineGun:
            profile.viewmodel.asset =
                WeaponViewmodelAsset::LightMachineGun;
            profile.controller.magazineSize = 60;
            profile.controller.startingReserve = 240;
            profile.controller.fireIntervalSeconds = 0.105f;
            profile.controller.reloadSeconds = 3.55f;
            profile.controller.adsInSeconds = 0.255f;
            profile.controller.adsOutSeconds = 0.16f;
            profile.controller.recoilPitchDegrees = 0.88f;
            profile.controller.recoilYawDegrees = 0.34f;
            profile.controller.automatic = true;
            profile.baseDamage = 32.0f;
            profile.falloffStartMeters = 24.0f;
            profile.maximumRangeMeters = 48.0f;
            profile.minimumDamageScale = 0.62f;
            break;

        case WeaponArchetype::SniperRifle:
            profile.viewmodel.asset =
                WeaponViewmodelAsset::SniperRifle;
            profile.controller.magazineSize = 5;
            profile.controller.startingReserve = 35;
            profile.controller.fireIntervalSeconds = 0.88f;
            profile.controller.reloadSeconds = 2.60f;
            profile.controller.adsInSeconds = 0.32f;
            profile.controller.adsOutSeconds = 0.18f;
            profile.controller.fireRequiresAds = true;
            profile.controller.minimumAdsAlphaToFire = 0.94f;
            profile.controller.triggerBufferSeconds = 0.40f;
            profile.controller.recoilPitchDegrees = 2.55f;
            profile.controller.recoilYawDegrees = 0.18f;
            profile.controller.automatic = false;
            profile.baseDamage = 110.0f;
            profile.falloffStartMeters = 70.0f;
            profile.maximumRangeMeters = 120.0f;
            profile.minimumDamageScale = 0.80f;
            break;
    }

    return profile;
}

float weaponDamageAtDistance(
    const WeaponProfile& profile,
    float distanceMeters) noexcept {
    if (!std::isfinite(distanceMeters) ||
        distanceMeters < 0.0f) {
        return 0.0f;
    }

    const float maximumRange =
        std::max(
            profile.maximumRangeMeters,
            0.01f);

    if (distanceMeters >
        maximumRange) {
        return 0.0f;
    }

    const float baseDamage =
        std::max(
            profile.baseDamage,
            0.0f);

    const float minimumScale =
        std::clamp(
            profile.minimumDamageScale,
            0.0f,
            1.0f);

    const float falloffStart =
        std::clamp(
            profile.falloffStartMeters,
            0.0f,
            maximumRange);

    if (distanceMeters <=
            falloffStart ||
        maximumRange -
            falloffStart <=
            1.0e-5f) {
        return baseDamage;
    }

    const float alpha =
        std::clamp(
            (distanceMeters -
             falloffStart) /
                (maximumRange -
                 falloffStart),
            0.0f,
            1.0f);

    const float scale =
        1.0f +
        (minimumScale -
         1.0f) *
            alpha;

    return baseDamage *
        scale;
}

} // namespace xziel
