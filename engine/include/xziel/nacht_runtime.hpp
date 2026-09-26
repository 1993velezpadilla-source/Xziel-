#pragma once

#include "xziel/door_system.hpp"
#include "xziel/nacht_reference.hpp"
#include "xziel/purchase_system.hpp"

#include <cstddef>
#include <cstdint>
#include <optional>

namespace xziel {

struct NachtRuntimeConfig {
    std::uint32_t startingPoints = 500U;
};

class NachtRuntime final {
public:
    explicit NachtRuntime(
        NachtRuntimeConfig config = {});

    void reset() noexcept;

    [[nodiscard]] bool unlockZone(
        NachtZone zone) noexcept;

    void awardPoints(
        std::uint32_t points) noexcept;

    [[nodiscard]] std::optional<PurchaseCandidate>
    queryPurchase(
        Vec3 playerPosition) const noexcept;

    [[nodiscard]] PurchaseResult tryPurchase(
        std::size_t index,
        Vec3 playerPosition) noexcept;

    [[nodiscard]] std::optional<DoorCandidate>
    queryDoor(
        Vec3 playerPosition) const noexcept;

    [[nodiscard]] DoorResult tryOpenDoor(
        std::size_t index,
        Vec3 playerPosition) noexcept;

    [[nodiscard]] HordeDirector& horde() noexcept;
    [[nodiscard]] const HordeDirector& horde() const noexcept;

    [[nodiscard]] const PurchaseSystem&
    purchases() const noexcept;

    [[nodiscard]] const DoorSystem&
    doors() const noexcept;

    [[nodiscard]] std::uint32_t points() const noexcept;
    [[nodiscard]] NachtZoneMask activeZones() const noexcept;

private:
    [[nodiscard]] bool refreshSpawnCatalog() noexcept;

    NachtRuntimeConfig config_{};
    HordeDirector horde_{};
    PurchaseSystem purchases_{};
    DoorSystem doors_{};
    std::uint32_t points_ = 0U;
    NachtZoneMask activeZones_ =
        kNachtStartZoneMask;
};

} // namespace xziel
