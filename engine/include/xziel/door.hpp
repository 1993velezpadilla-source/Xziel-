#pragma once

#include "xziel/horde_director.hpp"
#include "xziel/fps_player.hpp"
#include "xziel/score.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

inline constexpr std::size_t kMaxGameplayDoors = 16;

struct DoorDefinition {
    std::uint32_t id = 0;
    Aabb blocker{};
    std::uint32_t cost = 750;
    bool startsOpen = false;
    float openDurationSeconds = 0.90f;
    float collisionReleaseProgress = 0.62f;
};

struct DoorFrame {
    std::uint32_t id = 0;
    std::uint32_t cost = 0;
    bool open = false;
    bool opening = false;
    bool openedThisTick = false;
    bool becameFullyOpenThisTick = false;
    bool collisionReleased = false;
    bool insufficientFundsThisTick = false;
    float openProgress = 0.0f;
};

class DoorSystem final {
public:
    void clear() noexcept;

    [[nodiscard]] bool addDoor(
        const DoorDefinition& definition,
        HordeDirector& horde,
        FpsPlayerController& player) noexcept;

    [[nodiscard]] DoorFrame activate(
        std::uint32_t id,
        HordeDirector& horde,
        FpsPlayerController& player,
        ScoreSystem& score) noexcept;

    void step(
        float deltaSeconds,
        HordeDirector& horde,
        FpsPlayerController& player) noexcept;

    [[nodiscard]] const DoorFrame* frame(std::uint32_t id) const noexcept;
    [[nodiscard]] std::size_t count() const noexcept;

private:
    struct Slot {
        DoorFrame frame{};
        float openDurationSeconds = 0.90f;
        float collisionReleaseProgress = 0.62f;
        bool occupied = false;
    };
    [[nodiscard]] Slot* find(std::uint32_t id) noexcept;
    [[nodiscard]] const Slot* find(std::uint32_t id) const noexcept;

    std::array<Slot, kMaxGameplayDoors> doors_{};
    std::size_t count_ = 0;
};

} // namespace xziel
