#include "xziel/weapon_catalog.hpp"

#include <cassert>

int main() {
    const auto sidearm =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::Sidearm);

    const auto smg =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::SubmachineGun);

    const auto assault =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::AssaultRifle);

    const auto lmg =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::LightMachineGun);

    const auto marksman =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::MarksmanRifle);

    const auto shotgun =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::Shotgun);

    const auto sniper =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::SniperRifle);

    assert(
        sidearm.controller.magazineSize > 0U);

    assert(
        sidearm.soundFamily ==
            xziel::WeaponSoundFamily::Sidearm);

    assert(
        smg.soundFamily ==
            xziel::WeaponSoundFamily::SubmachineGun);

    assert(
        assault.soundFamily ==
            xziel::WeaponSoundFamily::AssaultRifle);

    assert(
        marksman.soundFamily ==
            xziel::WeaponSoundFamily::MarksmanRifle);

    assert(
        shotgun.soundFamily ==
            xziel::WeaponSoundFamily::Shotgun);

    assert(
        lmg.soundFamily ==
            xziel::WeaponSoundFamily::LightMachineGun);

    assert(
        sniper.soundFamily ==
            xziel::WeaponSoundFamily::SniperRifle);

    assert(sidearm.soundFamily != assault.soundFamily);
    assert(assault.soundFamily != shotgun.soundFamily);

    assert(
        assault.controller.automatic);

    assert(
        assault.viewmodel.asset ==
            xziel::WeaponViewmodelAsset::
                AssaultRifle);

    assert(
        assault.viewmodel.hip.scale > 0.0f);

    assert(
        assault.viewmodel.ads.scale > 0.0f);

    // The canonical AKM pivot is the stock/receiver seam. It must stay
    // at or just behind the renderer's 0.08 m near plane in ADS so the stock
    // clips away instead of appearing as a giant wooden cross-section.
    assert(
        assault.viewmodel.ads.z >=
            0.070f);

    assert(
        assault.viewmodel.ads.z <=
            0.080f);

    // Magnification reduction belongs to scale/FOV, not pushing the seam
    // forward through the near plane.
    assert(
        assault.viewmodel.ads.scale <=
            0.60f);

    assert(
        marksman.controller.
            fireRequiresAds);

    assert(
        sniper.controller.
            fireRequiresAds);

    assert(
        shotgun.hitscanPellets > 1U);

    const float closeDamage =
        xziel::weaponDamageAtDistance(
            assault,
            5.0f);

    const float farDamage =
        xziel::weaponDamageAtDistance(
            assault,
            assault.maximumRangeMeters);

    assert(closeDamage > farDamage);
    assert(farDamage > 0.0f);

    assert(
        xziel::weaponDamageAtDistance(
            assault,
            assault.maximumRangeMeters +
                1.0f) ==
        0.0f);

    return 0;
}
