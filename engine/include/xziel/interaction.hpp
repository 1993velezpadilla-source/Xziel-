#pragma once

#include "xziel/engine.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

inline constexpr std::size_t kMaxInteractionTargets = 64;

enum class InteractionKind : std::uint8_t {
    Use,
    Door,
    Pickup,
    WeaponBuy,
    Perk,
    Switch,
    QuestItem,
    Revive,
};

struct InteractionTarget {
    std::uint32_t id = 0;
    InteractionKind kind = InteractionKind::Use;

    Vec3 position{};

    float maximumDistance = 1.75f;
    float minimumFacingDot = 0.20f;
    float priority = 1.0f;
    float holdSeconds = 0.0f;

    std::uint32_t cost = 0;
    bool enabled = true;
};

struct InteractionInput {
    bool held = false;
};

struct InteractionFrame {
    bool promptVisible = false;
    bool activatedThisTick = false;

    std::uint32_t targetId = 0;
    InteractionKind kind = InteractionKind::Use;
    std::uint32_t cost = 0;

    Vec3 targetPosition{};

    float distanceMeters = 0.0f;
    float facingDot = 0.0f;
    float holdAlpha = 0.0f;
};

class InteractionSystem final {
public:
    InteractionSystem() = default;

    void reset() noexcept;
    void clearTargets() noexcept;

    [[nodiscard]] bool addTarget(
        const InteractionTarget& target) noexcept;

    [[nodiscard]] bool setTargetEnabled(
        std::uint32_t id,
        bool enabled) noexcept;

    [[nodiscard]] InteractionFrame step(
        Vec3 playerPosition,
        Vec3 viewDirection,
        const InteractionInput& input,
        float deltaSeconds) noexcept;

    [[nodiscard]] const InteractionFrame&
    frame() const noexcept;

    [[nodiscard]] std::size_t targetCount() const noexcept;

private:
    [[nodiscard]] const InteractionTarget*
    chooseTarget(
        Vec3 playerPosition,
        Vec3 viewDirection,
        float& outDistance,
        float& outFacing) const noexcept;

    std::array<InteractionTarget, kMaxInteractionTargets>
        targets_{};

    std::size_t targetCount_ = 0;

    InteractionFrame frame_{};

    std::uint32_t heldTargetId_ = 0;
    float heldSeconds_ = 0.0f;

    bool previousHeld_ = false;
    bool activationLatched_ = false;
};

} // namespace xziel
