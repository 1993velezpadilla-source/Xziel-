#pragma once

#include "xziel/engine.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace xziel {

inline constexpr std::size_t kMaxMapDoors = 16;

using MapZoneMask = std::uint32_t;

struct DoorDefinition {
    std::string_view id{};
    Vec3 position{};
    std::uint32_t price = 0U;
    float interactionRadiusMeters = 1.5f;
    MapZoneMask requiredZoneMask = 0U;
    MapZoneMask unlockZoneMask = 0U;
    bool enabled = true;
};

struct DoorCandidate {
    std::size_t index = 0U;
    float distanceMeters = 0.0f;
    bool affordable = false;
};

enum class DoorResultCode : std::uint8_t {
    Success,
    InvalidIndex,
    Disabled,
    AlreadyOpen,
    LockedByZone,
    OutOfRange,
    InsufficientPoints,
};

struct DoorResult {
    DoorResultCode code = DoorResultCode::InvalidIndex;
    std::size_t index = 0U;
    std::uint32_t price = 0U;
    std::uint32_t remainingPoints = 0U;
    MapZoneMask unlockZoneMask = 0U;
};

class DoorSystem final {
public:
    [[nodiscard]] bool setCatalog(
        std::span<const DoorDefinition> doors) noexcept;

    void reset() noexcept;

    [[nodiscard]] std::optional<DoorCandidate>
    queryNearest(
        Vec3 playerPosition,
        std::uint32_t points,
        MapZoneMask activeZones) const noexcept;

    [[nodiscard]] DoorResult tryOpen(
        std::size_t index,
        Vec3 playerPosition,
        std::uint32_t& points,
        MapZoneMask activeZones) noexcept;

    [[nodiscard]] bool isOpen(
        std::size_t index) const noexcept;

    [[nodiscard]] const DoorDefinition*
    door(std::size_t index) const noexcept;

    [[nodiscard]] std::size_t count() const noexcept;

private:
    [[nodiscard]] static float distance(
        Vec3 a,
        Vec3 b) noexcept;

    std::array<DoorDefinition, kMaxMapDoors>
        doors_{};
    std::array<bool, kMaxMapDoors>
        open_{};

    std::size_t count_ = 0U;
};

} // namespace xziel
