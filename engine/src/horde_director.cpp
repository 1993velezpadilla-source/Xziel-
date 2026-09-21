#include "xziel/horde_director.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace xziel {

namespace {

float positiveOr(
    float value,
    float fallback) noexcept {
    return (!std::isfinite(value) ||
            value <= 0.0f)
        ? fallback
        : value;
}

float safeDt(float value) noexcept {
    if (!std::isfinite(value) ||
        value <= 0.0f) {
        return 0.0f;
    }

    return std::min(
        value,
        0.05f);
}

} // namespace

HordeDirector::HordeDirector(
    HordeConfig config)
    : config_(config) {
    config_.startingRound =
        std::max<std::uint32_t>(
            config_.startingRound,
            1U);

    config_.baseZombiesPerRound =
        std::max<std::uint32_t>(
            config_.baseZombiesPerRound,
            1U);

    config_.maxActive =
        std::clamp<std::uint32_t>(
            config_.maxActive,
            1U,
            static_cast<std::uint32_t>(
                kMaxHordeZombies));

    config_.spawnPointCount =
        std::clamp<std::uint32_t>(
            config_.spawnPointCount,
            1U,
            static_cast<std::uint32_t>(
                config_.spawnPoints.size()));

    config_.spawnIntervalSeconds =
        positiveOr(
            config_.spawnIntervalSeconds,
            0.70f);

    config_.interRoundDelaySeconds =
        positiveOr(
            config_.interRoundDelaySeconds,
            2.20f);

    config_.baseHealth =
        positiveOr(
            config_.baseHealth,
            100.0f);

    config_.baseMoveSpeed =
        positiveOr(
            config_.baseMoveSpeed,
            0.70f);

    config_.maximumMoveSpeed =
        std::max(
            config_.baseMoveSpeed,
            positiveOr(
                config_.maximumMoveSpeed,
                1.45f));

    config_.separationRadius =
        positiveOr(
            config_.separationRadius,
            0.72f);

    config_.separationStrength =
        std::clamp(
            std::isfinite(
                config_.separationStrength)
                ? config_.separationStrength
                : 0.62f,
            0.0f,
            2.0f);

    config_.minimumSpawnDistanceFromPlayer =
        std::max(
            0.0f,
            std::isfinite(
                config_.minimumSpawnDistanceFromPlayer)
                ? config_.minimumSpawnDistanceFromPlayer
                : 3.0f);

    if (config_.arenaMinimumX >
        config_.arenaMaximumX) {
        std::swap(
            config_.arenaMinimumX,
            config_.arenaMaximumX);
    }

    if (config_.arenaMinimumZ >
        config_.arenaMaximumZ) {
        std::swap(
            config_.arenaMinimumZ,
            config_.arenaMaximumZ);
    }

    reset();
}

void HordeDirector::reset() noexcept {
    for (auto& zombieSlot : zombies_) {
        zombieSlot.reset();
    }

    frame_ = {};
    frame_.round =
        config_.startingRound;
    frame_.targetThisRound =
        targetForRound(
            frame_.round);
    frame_.roundStartedThisTick = true;

    spawnCooldownSeconds_ = 0.0f;
    interRoundSeconds_ = 0.0f;
    nextSpawnPoint_ = 0;
}

HordeFrame HordeDirector::step(
    Vec3 playerFeetPosition,
    float deltaSeconds) noexcept {
    const float dt =
        safeDt(
            deltaSeconds);

    frame_.spawnedThisTick = false;
    frame_.roundStartedThisTick = false;
    frame_.alive = 0;

    spawnCooldownSeconds_ =
        std::max(
            0.0f,
            spawnCooldownSeconds_ -
                dt);

    for (auto& zombieSlot : zombies_) {
        if (!zombieSlot.has_value()) {
            continue;
        }

        auto& actor =
            *zombieSlot;

        if (actor.frame().state ==
            ZombieState::Dead) {
            ++frame_.killedThisRound;
            zombieSlot.reset();
            continue;
        }

        (void) actor.step(
            playerFeetPosition,
            dt);

        if (actor.frame().state ==
            ZombieState::Dead) {
            ++frame_.killedThisRound;
            zombieSlot.reset();
            continue;
        }

        ++frame_.alive;
    }

    applyCrowdSeparation();
    constrainToArena();

    const bool roundExhausted =
        frame_.spawnedThisRound >=
            frame_.targetThisRound &&
        frame_.killedThisRound >=
            frame_.targetThisRound &&
        frame_.alive == 0;

    if (roundExhausted) {
        frame_.interRound = true;
        interRoundSeconds_ += dt;

        if (interRoundSeconds_ >=
            config_.interRoundDelaySeconds) {
            beginNextRound();
        }

        return frame_;
    }

    frame_.interRound = false;
    interRoundSeconds_ = 0.0f;

    if (frame_.spawnedThisRound <
            frame_.targetThisRound &&
        frame_.alive <
            config_.maxActive &&
        spawnCooldownSeconds_ <= 0.0f &&
        spawnOne(
            playerFeetPosition)) {
        ++frame_.spawnedThisRound;
        ++frame_.alive;
        frame_.spawnedThisTick = true;
        spawnCooldownSeconds_ =
            config_.spawnIntervalSeconds;
    }

    return frame_;
}

bool HordeDirector::damageZombie(
    std::size_t slot,
    float damage) noexcept {
    if (slot >= zombies_.size() ||
        !zombies_[slot].has_value()) {
        return false;
    }

    return zombies_[slot]->
        applyDamage(
            damage);
}

const ZombieActor*
HordeDirector::zombie(
    std::size_t slot) const noexcept {
    if (slot >= zombies_.size() ||
        !zombies_[slot].has_value()) {
        return nullptr;
    }

    return &*zombies_[slot];
}

ZombieActor*
HordeDirector::zombie(
    std::size_t slot) noexcept {
    if (slot >= zombies_.size() ||
        !zombies_[slot].has_value()) {
        return nullptr;
    }

    return &*zombies_[slot];
}

std::size_t HordeDirector::capacity() const noexcept {
    return zombies_.size();
}

const HordeFrame&
HordeDirector::frame() const noexcept {
    return frame_;
}

const HordeConfig&
HordeDirector::config() const noexcept {
    return config_;
}

std::uint32_t HordeDirector::targetForRound(
    std::uint32_t round) const noexcept {
    const std::uint64_t roundIndex =
        round > 0
        ? static_cast<std::uint64_t>(
              round - 1U)
        : 0ULL;

    const std::uint64_t result =
        static_cast<std::uint64_t>(
            config_.baseZombiesPerRound) +
        roundIndex *
        static_cast<std::uint64_t>(
            config_.zombiesAddedPerRound);

    return static_cast<std::uint32_t>(
        std::min<std::uint64_t>(
            result,
            999ULL));
}

bool HordeDirector::spawnOne(
    Vec3 playerFeetPosition) noexcept {
    std::size_t freeSlot =
        zombies_.size();

    for (std::size_t i = 0;
         i < zombies_.size();
         ++i) {
        if (!zombies_[i].has_value()) {
            freeSlot = i;
            break;
        }
    }

    if (freeSlot >=
        zombies_.size()) {
        return false;
    }

    const std::uint32_t roundIndex =
        frame_.round > 0
        ? frame_.round - 1U
        : 0U;

    ZombieConfig config{};

    std::uint32_t chosenSpawn =
        nextSpawnPoint_ %
        config_.spawnPointCount;

    float bestDistanceSquared = -1.0f;

    const float minimumDistanceSquared =
        config_.minimumSpawnDistanceFromPlayer *
        config_.minimumSpawnDistanceFromPlayer;

    for (std::uint32_t offset = 0;
         offset < config_.spawnPointCount;
         ++offset) {
        const std::uint32_t candidateIndex =
            (nextSpawnPoint_ + offset) %
            config_.spawnPointCount;

        const auto& candidate =
            config_.spawnPoints[
                candidateIndex];

        const float dx =
            candidate.x -
            playerFeetPosition.x;

        const float dz =
            candidate.z -
            playerFeetPosition.z;

        const float distanceSquared =
            dx * dx +
            dz * dz;

        if (distanceSquared >=
            minimumDistanceSquared) {
            chosenSpawn =
                candidateIndex;
            bestDistanceSquared =
                distanceSquared;
            break;
        }

        if (distanceSquared >
            bestDistanceSquared) {
            bestDistanceSquared =
                distanceSquared;
            chosenSpawn =
                candidateIndex;
        }
    }

    config.spawnPosition =
        config_.spawnPoints[
            chosenSpawn];

    config.maxHealth =
        config_.baseHealth +
        static_cast<float>(
            roundIndex) *
            config_.healthAddedPerRound;

    config.moveSpeed =
        std::min(
            config_.maximumMoveSpeed,
            config_.baseMoveSpeed +
                static_cast<float>(
                    roundIndex) *
                    config_.moveSpeedAddedPerRound);

    config.autoRespawn = false;

    zombies_[freeSlot].emplace(
        config);

    nextSpawnPoint_ =
        (chosenSpawn + 1U) %
        config_.spawnPointCount;

    return true;
}

void HordeDirector::applyCrowdSeparation() noexcept {
    const float radius =
        config_.separationRadius;

    if (radius <= 0.0f ||
        config_.separationStrength <= 0.0f) {
        return;
    }

    const float radiusSquared =
        radius * radius;

    for (std::size_t a = 0;
         a < zombies_.size();
         ++a) {
        if (!zombies_[a].has_value() ||
            zombies_[a]->frame().state ==
                ZombieState::Dead) {
            continue;
        }

        for (std::size_t b = a + 1;
             b < zombies_.size();
             ++b) {
            if (!zombies_[b].has_value() ||
                zombies_[b]->frame().state ==
                    ZombieState::Dead) {
                continue;
            }

            const auto& aPosition =
                zombies_[a]->frame().
                    position;

            const auto& bPosition =
                zombies_[b]->frame().
                    position;

            float dx =
                aPosition.x -
                bPosition.x;

            float dz =
                aPosition.z -
                bPosition.z;

            float distanceSquared =
                dx * dx +
                dz * dz;

            if (distanceSquared >=
                radiusSquared) {
                continue;
            }

            if (distanceSquared <
                1.0e-8f) {
                dx =
                    ((a + b) & 1U) != 0U
                    ? 1.0f
                    : -1.0f;

                dz = 0.0f;
                distanceSquared = 1.0f;
            }

            const float distance =
                std::sqrt(
                    distanceSquared);

            const float overlap =
                radius -
                distance;

            if (overlap <= 0.0f) {
                continue;
            }

            const float inverseDistance =
                1.0f /
                distance;

            const float push =
                overlap *
                0.5f *
                config_.separationStrength;

            const float pushX =
                dx *
                inverseDistance *
                push;

            const float pushZ =
                dz *
                inverseDistance *
                push;

            zombies_[a]->
                translateHorizontal(
                    pushX,
                    pushZ);

            zombies_[b]->
                translateHorizontal(
                    -pushX,
                    -pushZ);
        }
    }
}

void HordeDirector::constrainToArena() noexcept {
    for (auto& zombieSlot : zombies_) {
        if (!zombieSlot.has_value() ||
            zombieSlot->frame().state ==
                ZombieState::Dead) {
            continue;
        }

        const auto position =
            zombieSlot->frame().
                position;

        const float clampedX =
            std::clamp(
                position.x,
                config_.arenaMinimumX,
                config_.arenaMaximumX);

        const float clampedZ =
            std::clamp(
                position.z,
                config_.arenaMinimumZ,
                config_.arenaMaximumZ);

        zombieSlot->
            translateHorizontal(
                clampedX -
                    position.x,
                clampedZ -
                    position.z);
    }
}

void HordeDirector::beginNextRound() noexcept {
    if (frame_.round <
        std::numeric_limits<
            std::uint32_t>::max()) {
        ++frame_.round;
    }

    frame_.targetThisRound =
        targetForRound(
            frame_.round);
    frame_.spawnedThisRound = 0;
    frame_.killedThisRound = 0;
    frame_.alive = 0;
    frame_.interRound = false;
    frame_.roundStartedThisTick = true;

    spawnCooldownSeconds_ = 0.0f;
    interRoundSeconds_ = 0.0f;
}

} // namespace xziel
