#include "xziel/score.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace xziel {

ScoreSystem::ScoreSystem(
    ScoreConfig config)
    : config_(config) {
    reset();
}

void ScoreSystem::reset() noexcept {
    frame_ = {};
    frame_.total =
        config_.startingPoints;
    awardMultiplier_ = 1.0f;
}

ScoreFrame ScoreSystem::awardHit(
    ZombieHitRegion region,
    bool killed) noexcept {
    frame_.changedThisTick = false;
    frame_.criticalAwardThisTick = false;
    frame_.spentThisTick = false;
    frame_.insufficientFundsThisTick = false;
    frame_.lastAward = 0;
    frame_.lastSpend = 0;

    std::uint64_t points =
        hitPoints(
            region);

    if (killed) {
        points +=
            config_.killPoints;

        if (region ==
            ZombieHitRegion::Head) {
            points +=
                config_.headshotKillBonus;
        }
    }

    add(
        static_cast<std::uint32_t>(
            std::min<std::uint64_t>(
                points,
                std::numeric_limits<
                    std::uint32_t>::max())),
        region ==
            ZombieHitRegion::Head);

    return frame_;
}

ScoreFrame ScoreSystem::awardRoundClear(
    std::uint32_t completedRound) noexcept {
    frame_.changedThisTick = false;
    frame_.criticalAwardThisTick = false;
    frame_.spentThisTick = false;
    frame_.insufficientFundsThisTick = false;
    frame_.lastAward = 0;
    frame_.lastSpend = 0;

    const std::uint64_t points =
        static_cast<std::uint64_t>(
            config_.roundClearBasePoints) +
        static_cast<std::uint64_t>(
            completedRound) *
        static_cast<std::uint64_t>(
            config_.roundClearPerRound);

    add(
        static_cast<std::uint32_t>(
            std::min<std::uint64_t>(
                points,
                std::numeric_limits<
                    std::uint32_t>::max())),
        false);

    return frame_;
}

ScoreFrame ScoreSystem::awardUtility(
    std::uint32_t points) noexcept {
    frame_.changedThisTick = false;
    frame_.criticalAwardThisTick = false;
    frame_.spentThisTick = false;
    frame_.insufficientFundsThisTick = false;
    frame_.lastAward = 0;
    frame_.lastSpend = 0;

    add(points, false);
    return frame_;
}

bool ScoreSystem::trySpend(
    std::uint32_t points) noexcept {
    return spend(points);
}

bool ScoreSystem::canAfford(
    std::uint32_t cost) const noexcept {
    return frame_.total >=
        static_cast<std::uint64_t>(
            cost);
}

bool ScoreSystem::spend(
    std::uint32_t cost) noexcept {
    frame_.changedThisTick = false;
    frame_.criticalAwardThisTick = false;
    frame_.spentThisTick = false;
    frame_.insufficientFundsThisTick = false;
    frame_.lastAward = 0;
    frame_.lastSpend = 0;

    if (cost == 0U) {
        return true;
    }

    if (!canAfford(cost)) {
        frame_.insufficientFundsThisTick =
            true;
        return false;
    }

    frame_.total -=
        static_cast<std::uint64_t>(
            cost);

    const std::uint64_t maximum =
        std::numeric_limits<
            std::uint64_t>::max();

    if (maximum -
            frame_.lifetimeSpent <
        cost) {
        frame_.lifetimeSpent =
            maximum;
    } else {
        frame_.lifetimeSpent +=
            cost;
    }

    frame_.lastSpend = cost;
    frame_.spentThisTick = true;
    frame_.changedThisTick = true;

    return true;
}

void ScoreSystem::setAwardMultiplier(
    float multiplier) noexcept {
    awardMultiplier_ =
        std::clamp(
            std::isfinite(multiplier)
                ? multiplier
                : 1.0f,
            0.0f,
            16.0f);
}

float ScoreSystem::awardMultiplier() const noexcept {
    return awardMultiplier_;
}

const ScoreFrame&
ScoreSystem::frame() const noexcept {
    return frame_;
}

std::uint32_t ScoreSystem::hitPoints(
    ZombieHitRegion region) const noexcept {
    switch (region) {
        case ZombieHitRegion::Head:
            return config_.headHitPoints;

        case ZombieHitRegion::Torso:
            return config_.torsoHitPoints;

        case ZombieHitRegion::Limbs:
            return config_.limbHitPoints;

        case ZombieHitRegion::None:
        default:
            return 0;
    }
}

void ScoreSystem::add(
    std::uint32_t points,
    bool critical) noexcept {
    if (points == 0U ||
        awardMultiplier_ <= 0.0f) {
        return;
    }

    const double scaled =
        static_cast<double>(points) *
        static_cast<double>(awardMultiplier_);

    const std::uint32_t awarded =
        static_cast<std::uint32_t>(
            std::min<double>(
                std::floor(scaled + 0.5),
                static_cast<double>(
                    std::numeric_limits<
                        std::uint32_t>::max())));

    if (awarded == 0U) {
        return;
    }

    const std::uint64_t maximum =
        std::numeric_limits<
            std::uint64_t>::max();

    if (maximum -
            frame_.total <
        awarded) {
        frame_.total = maximum;
    } else {
        frame_.total += awarded;
    }

    if (maximum -
            frame_.lifetimeEarned <
        awarded) {
        frame_.lifetimeEarned =
            maximum;
    } else {
        frame_.lifetimeEarned +=
            awarded;
    }

    frame_.lastAward = awarded;
    frame_.changedThisTick = true;
    frame_.criticalAwardThisTick =
        critical;
}

} // namespace xziel
