#include "xziel/nacht_reference.hpp"
#include "xziel/purchase_system.hpp"

#include <cassert>
#include <cstdint>
#include <string_view>

int main() {
    const auto& profile =
        xziel::nachtReferenceProfile();

    xziel::PurchaseSystem purchases;

    assert(
        purchases.setCatalog(
            profile.purchases));

    assert(purchases.count() == 9U);

    const auto sheiva =
        purchases.queryNearest(
            profile.purchases[7].position,
            500U);

    assert(sheiva.has_value());
    assert(sheiva->index == 7U);
    assert(sheiva->affordable);

    std::uint32_t points = 500U;

    const auto result =
        purchases.tryPurchase(
            sheiva->index,
            profile.purchases[7].position,
            points);

    assert(
        result.code ==
        xziel::PurchaseResultCode::Success);
    assert(result.price == 500U);
    assert(points == 0U);
    assert(
        result.itemId ==
        std::string_view("ar_marksman"));

    points = 4999U;

    const auto locus =
        purchases.queryNearest(
            profile.purchases[5].position,
            points);

    assert(locus.has_value());
    assert(locus->index == 5U);
    assert(!locus->affordable);

    const auto denied =
        purchases.tryPurchase(
            locus->index,
            profile.purchases[5].position,
            points);

    assert(
        denied.code ==
        xziel::PurchaseResultCode::InsufficientPoints);
    assert(points == 4999U);

    const auto farAway =
        purchases.tryPurchase(
            0U,
            {100.0f, 100.0f, 100.0f},
            points);

    assert(
        farAway.code ==
        xziel::PurchaseResultCode::OutOfRange);

    return 0;
}
