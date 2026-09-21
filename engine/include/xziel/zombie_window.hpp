#pragma once

#include "xziel/barricade.hpp"
#include "xziel/horde_director.hpp"
#include "xziel/fps_player.hpp"
#include "xziel/score.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

inline constexpr std::size_t kMaxZombieWindows = 8;

struct ZombieWindowDefinition {
    std::uint32_t id = 0;
    Aabb blocker{};
    BarricadeConfig barricade{};
};

struct ZombieWindowFrame {
    std::uint32_t id = 0;
    BarricadeFrame barricade{};
    bool navigationBlocked = true;
};

class ZombieWindowSystem final {
public:
    void reset() noexcept;
    void beginRound() noexcept;

    [[nodiscard]] bool addWindow(
        const ZombieWindowDefinition& definition,
        HordeDirector& horde,
        FpsPlayerController& player) noexcept;

    [[nodiscard]] ZombieWindowFrame step(
        std::uint32_t id,
        bool zombieTearing,
        bool playerRebuilding,
        float deltaSeconds,
        HordeDirector& horde,
        FpsPlayerController& player,
        ScoreSystem& score) noexcept;

    [[nodiscard]] const ZombieWindowFrame*
    frame(std::uint32_t id) const noexcept;

    [[nodiscard]] std::size_t count() const noexcept;

private:
    struct Slot {
        std::uint32_t id = 0;
        BarricadeSystem barricade{};
        ZombieWindowFrame frame{};
        bool occupied = false;
    };

    [[nodiscard]] Slot* find(std::uint32_t id) noexcept;
    [[nodiscard]] const Slot* find(std::uint32_t id) const noexcept;

    std::array<Slot, kMaxZombieWindows> windows_{};
    std::size_t count_ = 0;
};

} // namespace xziel
