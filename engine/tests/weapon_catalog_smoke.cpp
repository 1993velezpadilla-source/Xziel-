#include "xziel/weapon_catalog.hpp"

#include <cassert>

int main() {
    const auto sidearm =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::Sidearm);

    const auto assault =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::AssaultRifle);

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
        assault.controller.automatic);

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
