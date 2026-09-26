#include "xziel/purchase_system.hpp"

#include <cmath>
#include <limits>

namespace xziel {

bool PurchaseSystem::setCatalog(
    std::span<const PurchaseDefinition> purchases) noexcept {
    if (purchases.empty() ||
        purchases.size() >
            purchases_.size()) {
        return false;
    }

    for (std::size_t i = 0;
         i < purchases.size();
         ++i) {
        const auto& purchase =
            purchases[i];

        if (purchase.id.empty() ||
            purchase.displayName.empty() ||
            purchase.itemId.empty() ||
            purchase.price == 0 ||
            !std::isfinite(
                purchase.interactionRadiusMeters) ||
            purchase.interactionRadiusMeters <= 0.0f) {
            return false;
        }

        purchases_[i] =
            purchase;
    }

    count_ =
        purchases.size();

    return true;
}

std::optional<PurchaseCandidate>
PurchaseSystem::queryNearest(
    Vec3 playerPosition,
    std::uint32_t points) const noexcept {
    std::optional<PurchaseCandidate> best;

    for (std::size_t i = 0;
         i < count_;
         ++i) {
        const auto& purchase =
            purchases_[i];

        if (!purchase.enabled) {
            continue;
        }

        const float d =
            distance(
                playerPosition,
                purchase.position);

        if (d >
            purchase.interactionRadiusMeters) {
            continue;
        }

        if (!best.has_value() ||
            d < best->distanceMeters) {
            best = PurchaseCandidate{
                .index = i,
                .distanceMeters = d,
                .affordable =
                    points >=
                    purchase.price,
            };
        }
    }

    return best;
}

PurchaseResult PurchaseSystem::tryPurchase(
    std::size_t index,
    Vec3 playerPosition,
    std::uint32_t& points) const noexcept {
    PurchaseResult result{};
    result.index = index;
    result.remainingPoints = points;

    if (index >= count_) {
        result.code =
            PurchaseResultCode::InvalidIndex;
        return result;
    }

    const auto& purchase =
        purchases_[index];

    result.itemId =
        purchase.itemId;
    result.price =
        purchase.price;

    if (!purchase.enabled) {
        result.code =
            PurchaseResultCode::Disabled;
        return result;
    }

    if (distance(
            playerPosition,
            purchase.position) >
        purchase.interactionRadiusMeters) {
        result.code =
            PurchaseResultCode::OutOfRange;
        return result;
    }

    if (points <
        purchase.price) {
        result.code =
            PurchaseResultCode::InsufficientPoints;
        return result;
    }

    points -=
        purchase.price;

    result.code =
        PurchaseResultCode::Success;
    result.remainingPoints =
        points;

    return result;
}

const PurchaseDefinition*
PurchaseSystem::purchase(
    std::size_t index) const noexcept {
    if (index >= count_) {
        return nullptr;
    }

    return &purchases_[index];
}

std::size_t PurchaseSystem::count() const noexcept {
    return count_;
}

float PurchaseSystem::distance(
    Vec3 a,
    Vec3 b) noexcept {
    const float dx =
        a.x - b.x;
    const float dy =
        a.y - b.y;
    const float dz =
        a.z - b.z;

    const float squared =
        dx * dx +
        dy * dy +
        dz * dz;

    if (!std::isfinite(squared) ||
        squared < 0.0f) {
        return std::numeric_limits<float>::infinity();
    }

    return std::sqrt(squared);
}

} // namespace xziel
