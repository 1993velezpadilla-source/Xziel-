#pragma once

#include "xziel/engine.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace xziel {

inline constexpr std::size_t kMaxMapPurchases = 16;

enum class PurchaseKind : std::uint8_t {
    WallWeapon,
    WeaponCabinet,
    Equipment,
};

struct PurchaseDefinition {
    std::string_view id{};
    std::string_view displayName{};
    std::string_view itemId{};
    PurchaseKind kind = PurchaseKind::WallWeapon;
    std::uint32_t price = 0;
    Vec3 position{};
    float interactionRadiusMeters = 1.5f;
    bool enabled = true;
};

struct PurchaseCandidate {
    std::size_t index = 0;
    float distanceMeters = 0.0f;
    bool affordable = false;
};

enum class PurchaseResultCode : std::uint8_t {
    Success,
    InvalidIndex,
    Disabled,
    OutOfRange,
    InsufficientPoints,
};

struct PurchaseResult {
    PurchaseResultCode code = PurchaseResultCode::InvalidIndex;
    std::size_t index = 0;
    std::string_view itemId{};
    std::uint32_t price = 0;
    std::uint32_t remainingPoints = 0;
};

class PurchaseSystem final {
public:
    [[nodiscard]] bool setCatalog(
        std::span<const PurchaseDefinition> purchases) noexcept;

    [[nodiscard]] std::optional<PurchaseCandidate>
    queryNearest(
        Vec3 playerPosition,
        std::uint32_t points) const noexcept;

    [[nodiscard]] PurchaseResult tryPurchase(
        std::size_t index,
        Vec3 playerPosition,
        std::uint32_t& points) const noexcept;

    [[nodiscard]] const PurchaseDefinition*
    purchase(std::size_t index) const noexcept;

    [[nodiscard]] std::size_t count() const noexcept;

private:
    [[nodiscard]] static float distance(
        Vec3 a,
        Vec3 b) noexcept;

    std::array<PurchaseDefinition, kMaxMapPurchases>
        purchases_{};

    std::size_t count_ = 0;
};

} // namespace xziel
