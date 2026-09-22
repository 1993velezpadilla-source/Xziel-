#pragma once

#include "xziel/zombie_hit_regions.hpp"

#include <cstdint>

namespace xziel {

struct ScoreConfig {
    std::uint32_t startingPoints = 0;

    std::uint32_t limbHitPoints = 5;
    std::uint32_t torsoHitPoints = 10;
    std::uint32_t headHitPoints = 20;

    std::uint32_t killPoints = 60;
    std::uint32_t headshotKillBonus = 40;

    std::uint32_t roundClearBasePoints = 100;
    std::uint32_t roundClearPerRound = 15;
};

struct ScoreFrame {
    std::uint64_t total = 0;
    std::uint64_t lifetimeEarned = 0;
    std::uint64_t lifetimeSpent = 0;

    std::uint32_t lastAward = 0;
    std::uint32_t lastSpend = 0;

    bool changedThisTick = false;
    bool criticalAwardThisTick = false;
    bool spentThisTick = false;
    bool insufficientFundsThisTick = false;
};

class ScoreSystem final {
public:
    explicit ScoreSystem(
        ScoreConfig config = {});

    void reset() noexcept;

    [[nodiscard]] ScoreFrame awardHit(
        ZombieHitRegion region,
        bool killed) noexcept;

    [[nodiscard]] ScoreFrame awardRoundClear(
        std::uint32_t completedRound) noexcept;

    [[nodiscard]] ScoreFrame awardUtility(
        std::uint32_t points) noexcept;

    [[nodiscard]] bool trySpend(
        std::uint32_t points) noexcept;

    [[nodiscard]] bool canAfford(
        std::uint32_t cost) const noexcept;

    [[nodiscard]] bool spend(
        std::uint32_t cost) noexcept;

    [[nodiscard]] const ScoreFrame&
    frame() const noexcept;

private:
    [[nodiscard]] std::uint32_t
    hitPoints(
        ZombieHitRegion region) const noexcept;

    void add(
        std::uint32_t points,
        bool critical) noexcept;

    ScoreConfig config_{};
    ScoreFrame frame_{};
};

} // namespace xziel
