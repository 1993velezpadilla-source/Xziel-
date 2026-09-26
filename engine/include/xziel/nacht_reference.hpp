#pragma once

#include "xziel/door_system.hpp"
#include "xziel/horde_director.hpp"
#include "xziel/purchase_system.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace xziel {

enum class NachtZone : std::uint8_t {
    Start = 0,
    Box = 1,
    Upstairs = 2,
};

using NachtZoneMask = std::uint8_t;

inline constexpr NachtZoneMask kNachtStartZoneMask = 1U << 0U;
inline constexpr NachtZoneMask kNachtBoxZoneMask = 1U << 1U;
inline constexpr NachtZoneMask kNachtUpstairsZoneMask = 1U << 2U;
inline constexpr NachtZoneMask kNachtAllZonesMask =
    kNachtStartZoneMask |
    kNachtBoxZoneMask |
    kNachtUpstairsZoneMask;

struct NachtZombieSpawn {
    std::string_view id{};
    Vec3 position{};
    NachtZone zone = NachtZone::Start;
    bool activeDefault = false;
    bool riser = false;
};

struct NachtReferenceProfile {
    std::array<NachtZombieSpawn, 21> zombieSpawns{};
    std::array<PurchaseDefinition, 9> purchases{};
    std::array<DoorDefinition, 3> doors{};
};

[[nodiscard]] const NachtReferenceProfile&
nachtReferenceProfile() noexcept;

[[nodiscard]] std::size_t collectNachtSpawnPoints(
    NachtZoneMask activeZones,
    std::span<Vec3> destination) noexcept;

[[nodiscard]] HordeConfig makeNachtHordeConfig(
    NachtZoneMask activeZones =
        kNachtStartZoneMask) noexcept;

} // namespace xziel
