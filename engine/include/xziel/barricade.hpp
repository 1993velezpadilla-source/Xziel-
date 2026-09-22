#pragma once

#include <cstdint>

namespace xziel {

struct BarricadeConfig {
    std::uint8_t maximumPlanks = 6;
    float zombieTearSeconds = 1.05f;
    float rebuildSeconds = 0.72f;
    std::uint32_t rebuildPointsPerPlank = 10;
    std::uint32_t maximumRebuildPointsPerRound = 60;
};

struct BarricadeFrame {
    std::uint8_t intactPlanks = 0;
    bool blocksZombieTraversal = true;
    bool plankRemovedThisTick = false;
    bool plankRebuiltThisTick = false;
    bool breachedThisTick = false;
    bool fullyRebuiltThisTick = false;
    std::uint32_t pointsAwardedThisTick = 0;
    float zombieTearAlpha = 0.0f;
    float rebuildAlpha = 0.0f;
};

class BarricadeSystem final {
public:
    explicit BarricadeSystem(BarricadeConfig config = {});

    void reset() noexcept;
    void beginRound() noexcept;

    [[nodiscard]] BarricadeFrame step(
        bool zombieTearing,
        bool playerRebuilding,
        float deltaSeconds) noexcept;

    [[nodiscard]] const BarricadeFrame& frame() const noexcept;
    [[nodiscard]] const BarricadeConfig& config() const noexcept;

private:
    BarricadeConfig config_{};
    BarricadeFrame frame_{};
    float zombieTearSeconds_ = 0.0f;
    float rebuildSeconds_ = 0.0f;
    std::uint32_t rebuildPointsThisRound_ = 0;
};

} // namespace xziel
