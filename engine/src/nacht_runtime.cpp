#include "xziel/nacht_runtime.hpp"

#include <array>
#include <limits>
#include <span>

namespace xziel {

namespace {

constexpr NachtZoneMask zoneBit(
    NachtZone zone) noexcept {
    return static_cast<NachtZoneMask>(
        1U <<
        static_cast<std::uint8_t>(
            zone));
}

} // namespace

NachtRuntime::NachtRuntime(
    NachtRuntimeConfig config)
    : config_(config),
      horde_(
          makeNachtHordeConfig(
              kNachtStartZoneMask)) {
    (void) purchases_.setCatalog(
        nachtReferenceProfile().purchases);

    reset();
}

void NachtRuntime::reset() noexcept {
    points_ =
        config_.startingPoints;

    activeZones_ =
        kNachtStartZoneMask;

    (void) refreshSpawnCatalog();
    horde_.reset();
}

bool NachtRuntime::unlockZone(
    NachtZone zone) noexcept {
    const NachtZoneMask bit =
        zoneBit(zone);

    if ((activeZones_ & bit) != 0U) {
        return true;
    }

    const NachtZoneMask previous =
        activeZones_;

    activeZones_ |= bit;

    if (!refreshSpawnCatalog()) {
        activeZones_ =
            previous;
        (void) refreshSpawnCatalog();
        return false;
    }

    return true;
}

void NachtRuntime::awardPoints(
    std::uint32_t points) noexcept {
    const auto maximum =
        std::numeric_limits<
            std::uint32_t>::max();

    if (maximum - points_ <
        points) {
        points_ = maximum;
        return;
    }

    points_ += points;
}

std::optional<PurchaseCandidate>
NachtRuntime::queryPurchase(
    Vec3 playerPosition) const noexcept {
    return purchases_.queryNearest(
        playerPosition,
        points_);
}

PurchaseResult NachtRuntime::tryPurchase(
    std::size_t index,
    Vec3 playerPosition) noexcept {
    return purchases_.tryPurchase(
        index,
        playerPosition,
        points_);
}

HordeDirector& NachtRuntime::horde() noexcept {
    return horde_;
}

const HordeDirector&
NachtRuntime::horde() const noexcept {
    return horde_;
}

const PurchaseSystem&
NachtRuntime::purchases() const noexcept {
    return purchases_;
}

std::uint32_t NachtRuntime::points() const noexcept {
    return points_;
}

NachtZoneMask NachtRuntime::activeZones() const noexcept {
    return activeZones_;
}

bool NachtRuntime::refreshSpawnCatalog() noexcept {
    std::array<Vec3, 21> points{};

    const std::size_t count =
        collectNachtSpawnPoints(
            activeZones_,
            points);

    if (count == 0U) {
        return false;
    }

    return horde_.replaceSpawnPoints(
        std::span<const Vec3>(
            points.data(),
            count));
}

} // namespace xziel
