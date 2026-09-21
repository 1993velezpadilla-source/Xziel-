#pragma once

#include "xziel/horde_director.hpp"
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
};

struct DoorFrame {
    std::uint32_t id = 0;
    std::uint32_t cost = 0;
    bool open = false;
    bool openedThisTick = false;
    bool insufficientFundsThisTick = false;
};

class DoorSystem final {
public:
    void clear() noexcept;

    [[nodiscard]] bool addDoor(
        const DoorDefinition& definition,
        HordeDirector& horde) noexcept;

    [[nodiscard]] DoorFrame activate(
        std::uint32_t id,
        HordeDirector& horde,
        ScoreSystem& score) noexcept;

    [[nodiscard]] const DoorFrame* frame(std::uint32_t id) const noexcept;
    [[nodiscard]] std::size_t count() const noexcept;

private:
    struct Slot {
        DoorFrame frame{};
        bool occupied = false;
    };
    [[nodiscard]] Slot* find(std::uint32_t id) noexcept;
    [[nodiscard]] const Slot* find(std::uint32_t id) const noexcept;

    std::array<Slot, kMaxGameplayDoors> doors_{};
    std::size_t count_ = 0;
};

} // namespace xziel
