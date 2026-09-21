#include "xziel/weapon.hpp"

#include <cassert>
#include <cmath>
#include <cstdint>

int main() {
    xziel::WeaponConfig config{};
    config.magazineSize = 12;
    config.startingReserve = 24;
    config.fireIntervalSeconds = 0.10f;
    config.reloadSeconds = 1.0f;

    xziel::WeaponController weapon(
        config);

    std::uint32_t fired = 0;

    for (int i = 0; i < 120; ++i) {
        const auto frame =
            weapon.step(
                {
                    .fireHeld = true,
                    .aimHeld = true,
                },
                1.0f / 120.0f);

        if (frame.firedThisTick) {
            ++fired;
            assert(
                frame.recoilPitchImpulse >
                0.0f);
            assert(
                std::fabs(
                    frame.recoilYawImpulse) >
                0.0f);
        }
    }

    assert(fired >= 9);
    assert(fired <= 11);
    assert(
        weapon.frame().magazine ==
        config.magazineSize - fired);
    assert(
        weapon.frame().adsAlpha >
        0.99f);

    // Empty the remaining magazine.
    for (int i = 0; i < 300; ++i) {
        (void) weapon.step(
            {
                .fireHeld = true,
            },
            1.0f / 120.0f);

        if (weapon.frame().magazine == 0) {
            break;
        }
    }

    assert(
        weapon.frame().magazine == 0);

    auto reload =
        weapon.step(
            {
                .reloadPressed = true,
            },
            1.0f / 120.0f);

    assert(
        reload.phase ==
        xziel::WeaponPhase::Reloading);
    assert(
        reload.reloadStartedThisTick);

    for (int i = 0; i < 121; ++i) {
        reload =
            weapon.step(
                {},
                1.0f / 120.0f);
    }

    assert(
        reload.phase ==
        xziel::WeaponPhase::Ready);
    assert(
        reload.magazine ==
        config.magazineSize);
    assert(
        reload.reserve ==
        config.startingReserve -
        config.magazineSize);

    return 0;
}
