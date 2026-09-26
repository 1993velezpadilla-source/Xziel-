#include "xziel/door_system.hpp"

#include <cmath>
#include <limits>

namespace xziel {

bool DoorSystem::setCatalog(
    std::span<const DoorDefinition> doors) noexcept {
    if (doors.empty() ||
        doors.size() >
            doors_.size()) {
        return false;
    }

    for (std::size_t i = 0;
         i < doors.size();
         ++i) {
        const auto& door =
            doors[i];

        if (door.id.empty() ||
            door.price == 0U ||
            !std::isfinite(
                door.interactionRadiusMeters) ||
            door.interactionRadiusMeters <= 0.0f ||
            door.unlockZoneMask == 0U) {
            return false;
        }

        doors_[i] =
            door;
    }

    count_ =
        doors.size();

    reset();
    return true;
}

void DoorSystem::reset() noexcept {
    for (auto& open :
         open_) {
        open = false;
    }
}

std::optional<DoorCandidate>
DoorSystem::queryNearest(
    Vec3 playerPosition,
    std::uint32_t points,
    MapZoneMask activeZones) const noexcept {
    std::optional<DoorCandidate> best;

    for (std::size_t i = 0;
         i < count_;
         ++i) {
        const auto& door =
            doors_[i];

        if (!door.enabled ||
            open_[i] ||
            (door.requiredZoneMask != 0U &&
             (activeZones &
              door.requiredZoneMask) == 0U) ||
            (activeZones &
             door.unlockZoneMask) ==
                door.unlockZoneMask) {
            continue;
        }

        const float d =
            distance(
                playerPosition,
                door.position);

        if (d >
            door.interactionRadiusMeters) {
            continue;
        }

        if (!best.has_value() ||
            d < best->distanceMeters) {
            best = DoorCandidate{
                .index = i,
                .distanceMeters = d,
                .affordable =
                    points >=
                    door.price,
            };
        }
    }

    return best;
}

DoorResult DoorSystem::tryOpen(
    std::size_t index,
    Vec3 playerPosition,
    std::uint32_t& points,
    MapZoneMask activeZones) noexcept {
    DoorResult result{};
    result.index = index;
    result.remainingPoints = points;

    if (index >= count_) {
        result.code =
            DoorResultCode::InvalidIndex;
        return result;
    }

    const auto& door =
        doors_[index];

    result.price =
        door.price;
    result.unlockZoneMask =
        door.unlockZoneMask;

    if (!door.enabled) {
        result.code =
            DoorResultCode::Disabled;
        return result;
    }

    if (open_[index] ||
        (activeZones &
         door.unlockZoneMask) ==
            door.unlockZoneMask) {
        result.code =
            DoorResultCode::AlreadyOpen;
        return result;
    }

    if (door.requiredZoneMask != 0U &&
        (activeZones &
         door.requiredZoneMask) == 0U) {
        result.code =
            DoorResultCode::LockedByZone;
        return result;
    }

    if (distance(
            playerPosition,
            door.position) >
        door.interactionRadiusMeters) {
        result.code =
            DoorResultCode::OutOfRange;
        return result;
    }

    if (points <
        door.price) {
        result.code =
            DoorResultCode::InsufficientPoints;
        return result;
    }

    points -=
        door.price;

    open_[index] = true;

    result.code =
        DoorResultCode::Success;
    result.remainingPoints =
        points;

    return result;
}

bool DoorSystem::isOpen(
    std::size_t index) const noexcept {
    return index < count_ &&
        open_[index];
}

const DoorDefinition*
DoorSystem::door(
    std::size_t index) const noexcept {
    if (index >= count_) {
        return nullptr;
    }

    return &doors_[index];
}

std::size_t DoorSystem::count() const noexcept {
    return count_;
}

float DoorSystem::distance(
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
