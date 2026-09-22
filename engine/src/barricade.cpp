#include "xziel/barricade.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

BarricadeSystem::BarricadeSystem(BarricadeConfig config)
    : config_(config) {
    config_.maximumPlanks = std::max<std::uint8_t>(1, config_.maximumPlanks);
    config_.zombieTearSeconds = std::max(0.05f, config_.zombieTearSeconds);
    config_.rebuildSeconds = std::max(0.05f, config_.rebuildSeconds);
    reset();
}

void BarricadeSystem::reset() noexcept {
    frame_ = {};
    frame_.intactPlanks = config_.maximumPlanks;
    frame_.blocksZombieTraversal = true;
    zombieTearSeconds_ = 0.0f;
    rebuildSeconds_ = 0.0f;
    rebuildPointsThisRound_ = 0;
}

void BarricadeSystem::beginRound() noexcept {
    rebuildPointsThisRound_ = 0;
}

void BarricadeSystem::forceFullRebuild() noexcept {
    const bool changed =
        frame_.intactPlanks <
        config_.maximumPlanks;

    frame_.intactPlanks =
        config_.maximumPlanks;
    frame_.blocksZombieTraversal = true;
    frame_.plankRemovedThisTick = false;
    frame_.plankRebuiltThisTick = changed;
    frame_.breachedThisTick = false;
    frame_.fullyRebuiltThisTick = changed;
    frame_.pointsAwardedThisTick = 0U;
    frame_.zombieTearAlpha = 0.0f;
    frame_.rebuildAlpha = 0.0f;

    zombieTearSeconds_ = 0.0f;
    rebuildSeconds_ = 0.0f;
}

BarricadeFrame BarricadeSystem::step(
    bool zombieTearing,
    bool playerRebuilding,
    float deltaSeconds) noexcept {
    frame_.plankRemovedThisTick = false;
    frame_.plankRebuiltThisTick = false;
    frame_.breachedThisTick = false;
    frame_.fullyRebuiltThisTick = false;
    frame_.pointsAwardedThisTick = 0;

    const float dt = std::isfinite(deltaSeconds)
        ? std::clamp(deltaSeconds, 0.0f, 0.05f)
        : 0.0f;

    // Zombie pressure wins a simultaneous race so a player cannot freeze a
    // window indefinitely by holding rebuild while a zombie is tearing it.
    if (zombieTearing && frame_.intactPlanks > 0) {
        rebuildSeconds_ = 0.0f;
        zombieTearSeconds_ += dt;
        if (zombieTearSeconds_ + 1.0e-6f >= config_.zombieTearSeconds) {
            zombieTearSeconds_ = 0.0f;
            --frame_.intactPlanks;
            frame_.plankRemovedThisTick = true;
            frame_.breachedThisTick = frame_.intactPlanks == 0;
        }
    } else {
        zombieTearSeconds_ = 0.0f;
        if (playerRebuilding && frame_.intactPlanks < config_.maximumPlanks) {
            rebuildSeconds_ += dt;
            if (rebuildSeconds_ + 1.0e-6f >= config_.rebuildSeconds) {
                rebuildSeconds_ = 0.0f;
                ++frame_.intactPlanks;
                frame_.plankRebuiltThisTick = true;
                frame_.fullyRebuiltThisTick =
                    frame_.intactPlanks == config_.maximumPlanks;

                const std::uint32_t remaining =
                    rebuildPointsThisRound_ < config_.maximumRebuildPointsPerRound
                    ? config_.maximumRebuildPointsPerRound - rebuildPointsThisRound_
                    : 0U;
                const std::uint32_t award =
                    std::min(config_.rebuildPointsPerPlank, remaining);
                rebuildPointsThisRound_ += award;
                frame_.pointsAwardedThisTick = award;
            }
        } else {
            rebuildSeconds_ = 0.0f;
        }
    }

    frame_.blocksZombieTraversal = frame_.intactPlanks > 0;
    frame_.zombieTearAlpha = frame_.intactPlanks > 0
        ? std::clamp(zombieTearSeconds_ / config_.zombieTearSeconds, 0.0f, 1.0f)
        : 0.0f;
    frame_.rebuildAlpha = frame_.intactPlanks < config_.maximumPlanks
        ? std::clamp(rebuildSeconds_ / config_.rebuildSeconds, 0.0f, 1.0f)
        : 0.0f;
    return frame_;
}

const BarricadeFrame& BarricadeSystem::frame() const noexcept { return frame_; }
const BarricadeConfig& BarricadeSystem::config() const noexcept { return config_; }

} // namespace xziel
