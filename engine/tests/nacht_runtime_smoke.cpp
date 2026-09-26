#include "xziel/nacht_runtime.hpp"

#include <cassert>
#include <string_view>

int main() {
    xziel::NachtRuntime runtime{};

    assert(runtime.points() == 500U);
    assert(
        runtime.activeZones() ==
        xziel::kNachtStartZoneMask);
    assert(
        runtime.horde().config().
            spawnPointCount ==
        10U);
    assert(runtime.purchases().count() == 9U);

    const auto& profile =
        xziel::nachtReferenceProfile();

    const auto rk5 =
        runtime.queryPurchase(
            profile.purchases[8].position);

    assert(rk5.has_value());
    assert(rk5->index == 8U);
    assert(rk5->affordable);

    const auto bought =
        runtime.tryPurchase(
            rk5->index,
            profile.purchases[8].position);

    assert(
        bought.code ==
        xziel::PurchaseResultCode::Success);
    assert(
        bought.itemId ==
        std::string_view("pistol_burst"));
    assert(runtime.points() == 0U);

    runtime.awardPoints(1500U);
    assert(runtime.points() == 1500U);

    assert(
        runtime.unlockZone(
            xziel::NachtZone::Box));

    assert(
        runtime.horde().config().
            spawnPointCount ==
        15U);

    assert(
        runtime.unlockZone(
            xziel::NachtZone::Upstairs));

    assert(
        runtime.horde().config().
            spawnPointCount ==
        21U);

    runtime.reset();

    assert(runtime.points() == 500U);
    assert(
        runtime.horde().config().
            spawnPointCount ==
        10U);

    return 0;
}
