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
    assert(runtime.doors().count() == 3U);

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

    runtime.awardPoints(2500U);
    assert(runtime.points() == 2500U);

    const auto boxDoor =
        runtime.queryDoor(
            profile.doors[0].position);

    assert(boxDoor.has_value());
    assert(boxDoor->index == 0U);
    assert(boxDoor->affordable);

    const auto openedBox =
        runtime.tryOpenDoor(
            boxDoor->index,
            profile.doors[0].position);

    assert(
        openedBox.code ==
        xziel::DoorResultCode::Success);
    assert(runtime.points() == 1500U);
    assert(
        runtime.activeZones() ==
        static_cast<xziel::NachtZoneMask>(
            xziel::kNachtStartZoneMask |
            xziel::kNachtBoxZoneMask));

    assert(
        runtime.horde().config().
            spawnPointCount ==
        15U);

    const auto upperDoor =
        runtime.queryDoor(
            profile.doors[2].position);

    assert(upperDoor.has_value());
    assert(upperDoor->index == 2U);

    const auto openedUpper =
        runtime.tryOpenDoor(
            upperDoor->index,
            profile.doors[2].position);

    assert(
        openedUpper.code ==
        xziel::DoorResultCode::Success);
    assert(runtime.points() == 500U);

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
