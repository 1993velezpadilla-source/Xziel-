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

constexpr float kNavigationMaximumStep = 0.46f;
constexpr float kNavigationMaximumGap = 0.52f;
constexpr std::size_t kInvalidNavigationFloor =
    std::numeric_limits<std::size_t>::max();

float intervalGap(
    float minimumA,
    float maximumA,
    float minimumB,
    float maximumB) noexcept {
    if (maximumA < minimumB) {
        return minimumB - maximumA;
    }

    if (maximumB < minimumA) {
        return minimumA - maximumB;
    }

    return 0.0f;
}

bool navigationFloorsAdjacent(
    const Aabb& a,
    const Aabb& b) noexcept {
    const float verticalStep =
        std::fabs(
            a.maximum.y -
            b.maximum.y);

    if (verticalStep >
        kNavigationMaximumStep) {
        return false;
    }

    const float gapX =
        intervalGap(
            a.minimum.x,
            a.maximum.x,
            b.minimum.x,
            b.maximum.x);

    const float gapZ =
        intervalGap(
            a.minimum.z,
            a.maximum.z,
            b.minimum.z,
            b.maximum.z);

    if (gapX > kNavigationMaximumGap ||
        gapZ > kNavigationMaximumGap) {
        return false;
    }

    return
        (gapX * gapX +
         gapZ * gapZ) <=
        kNavigationMaximumGap *
            kNavigationMaximumGap;
}

float navigationDistance(
    Vec3 a,
    Vec3 b) noexcept {
    const float dx = b.x - a.x;
    const float dz = b.z - a.z;
    const float dy = std::fabs(b.y - a.y);

    return
        std::sqrt(
            dx * dx +
            dz * dz) +
        dy * 2.0f;
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
    zombieDynamicBlockerTargets_.fill(0U);
}

bool HordeDirector::setSpawnPoints(
    const Vec3* points,
    std::size_t count) noexcept {
    if (points == nullptr ||
        count == 0 ||
        count > config_.spawnPoints.size()) {
        return false;
    }

    for (std::size_t i = 0; i < count; ++i) {
        if (!std::isfinite(points[i].x) ||
            !std::isfinite(points[i].y) ||
            !std::isfinite(points[i].z)) {
            return false;
        }
    }

    for (std::size_t i = 0;
         i < config_.spawnPoints.size();
         ++i) {
        config_.spawnPoints[i] =
            i < count
            ? points[i]
            : Vec3{};
    }

    config_.spawnPointCount =
        static_cast<std::uint32_t>(
            count);
    nextSpawnPoint_ = 0U;
    return true;
}

bool HordeDirector::setArenaBounds(
    float minimumX,
    float maximumX,
    float minimumZ,
    float maximumZ) noexcept {
    if (!std::isfinite(minimumX) ||
        !std::isfinite(maximumX) ||
        !std::isfinite(minimumZ) ||
        !std::isfinite(maximumZ) ||
        minimumX >= maximumX ||
        minimumZ >= maximumZ) {
        return false;
    }

    config_.arenaMinimumX = minimumX;
    config_.arenaMaximumX = maximumX;
    config_.arenaMinimumZ = minimumZ;
    config_.arenaMaximumZ = maximumZ;
    return true;
}

void HordeDirector::clearNavigationFloors() noexcept {
    navigationFloorCount_ = 0;
    navigationLinkCount_ = 0;
    navigationNeighborCounts_.fill(0U);

    for (auto& neighbors :
         navigationNeighbors_) {
        neighbors.fill(0U);
    }
}

bool HordeDirector::addNavigationFloor(
    const Aabb& floor) noexcept {
    if (navigationFloorCount_ >=
            navigationFloors_.size() ||
        floor.minimum.x > floor.maximum.x ||
        floor.minimum.y > floor.maximum.y ||
        floor.minimum.z > floor.maximum.z ||
        !std::isfinite(floor.minimum.x) ||
        !std::isfinite(floor.minimum.y) ||
        !std::isfinite(floor.minimum.z) ||
        !std::isfinite(floor.maximum.x) ||
        !std::isfinite(floor.maximum.y) ||
        !std::isfinite(floor.maximum.z)) {
        return false;
    }

    std::array<
        std::uint16_t,
        kMaxHordeNavigationLinksPerFloor>
        connected{};

    std::size_t connectedCount = 0U;

    for (std::size_t i = 0;
         i < navigationFloorCount_;
         ++i) {
        if (!navigationFloorsAdjacent(
                navigationFloors_[i],
                floor)) {
            continue;
        }

        // Dense authored floor segmentation can legitimately create
        // more local adjacencies than the bounded graph stores. Do not reject
        // the whole map in that case: retain a bounded subset and let later
        // floors connect through neighbors that still have capacity.
        if (connectedCount >= connected.size() ||
            navigationNeighborCounts_[i] >=
                kMaxHordeNavigationLinksPerFloor) {
            continue;
        }

        connected[connectedCount++] =
            static_cast<std::uint16_t>(i);
    }

    const std::size_t newIndex =
        navigationFloorCount_;

    navigationFloors_[newIndex] =
        floor;

    for (std::size_t i = 0;
         i < connectedCount;
         ++i) {
        const std::size_t neighbor =
            connected[i];

        navigationNeighbors_[newIndex][i] =
            static_cast<std::uint16_t>(
                neighbor);

        auto& neighborCount =
            navigationNeighborCounts_[
                neighbor];

        navigationNeighbors_[
            neighbor][neighborCount++] =
                static_cast<std::uint16_t>(
                    newIndex);

        ++navigationLinkCount_;
    }

    navigationNeighborCounts_[newIndex] =
        static_cast<std::uint8_t>(
            connectedCount);

    ++navigationFloorCount_;
    return true;
}

void HordeDirector::clearNavigationObstacles() noexcept {
    navigationObstacleCount_ = 0;
}

bool HordeDirector::addNavigationObstacle(
    const Aabb& obstacle) noexcept {
    if (navigationObstacleCount_ >=
            navigationObstacles_.size() ||
        obstacle.minimum.x >
            obstacle.maximum.x ||
        obstacle.minimum.y >
            obstacle.maximum.y ||
        obstacle.minimum.z >
            obstacle.maximum.z) {
        return false;
    }

    navigationObstacles_[
        navigationObstacleCount_++] =
        obstacle;

    return true;
}

void HordeDirector::clearDynamicBlockers() noexcept {
    dynamicBlockerCount_ = 0;
}

bool HordeDirector::addDynamicBlocker(
    std::uint32_t id,
    const Aabb& obstacle,
    bool enabled,
    bool breakable) noexcept {
    if (id == 0 ||
        dynamicBlockerCount_ >= dynamicBlockers_.size() ||
        obstacle.minimum.x > obstacle.maximum.x ||
        obstacle.minimum.y > obstacle.maximum.y ||
        obstacle.minimum.z > obstacle.maximum.z) {
        return false;
    }
    for (std::size_t i = 0; i < dynamicBlockerCount_; ++i) {
        if (dynamicBlockers_[i].id == id) {
            return false;
        }
    }
    dynamicBlockers_[dynamicBlockerCount_++] = {
        id,
        obstacle,
        enabled,
        breakable,
    };
    return true;
}

bool HordeDirector::setDynamicBlockerEnabled(
    std::uint32_t id,
    bool enabled) noexcept {
    for (std::size_t i = 0; i < dynamicBlockerCount_; ++i) {
        if (dynamicBlockers_[i].id == id) {
            dynamicBlockers_[i].enabled = enabled;
            return true;
        }
    }
    return false;
}

std::uint32_t HordeDirector::zombieDynamicBlockerTarget(
    std::size_t slot) const noexcept {
    if (slot >= zombieDynamicBlockerTargets_.size()) {
        return 0U;
    }
    return zombieDynamicBlockerTargets_[slot];
}

std::uint32_t HordeDirector::dynamicBlockerAttackCount(
    std::uint32_t id) const noexcept {
    if (id == 0U) {
        return 0U;
    }

    std::uint32_t count = 0U;
    for (std::size_t slot = 0; slot < zombies_.size(); ++slot) {
        if (zombieDynamicBlockerTargets_[slot] != id ||
            !zombies_[slot].has_value() ||
            zombies_[slot]->frame().state == ZombieState::Dead ||
            !zombies_[slot]->frame().attackThisTick) {
            continue;
        }
        ++count;
    }
    return count;
}

std::size_t HordeDirector::navigationFloorCount() const noexcept {
    return navigationFloorCount_;
}

std::size_t HordeDirector::navigationLinkCount() const noexcept {
    return navigationLinkCount_;
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

    for (std::size_t slot = 0; slot < zombies_.size(); ++slot) {
        auto& zombieSlot = zombies_[slot];
        zombieDynamicBlockerTargets_[slot] = 0U;

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

        std::uint32_t dynamicBlockerTarget = 0U;
        const Vec3 steeringTarget =
            steeringTargetFor(
                actor,
                playerFeetPosition,
                dynamicBlockerTarget);

        zombieDynamicBlockerTargets_[slot] =
            dynamicBlockerTarget;

        (void) actor.step(
            steeringTarget,
            dt);

        if (actor.frame().state ==
            ZombieState::Dead) {
            ++frame_.killedThisRound;
            zombieDynamicBlockerTargets_[slot] = 0U;
            zombieSlot.reset();
            continue;
        }

        ++frame_.alive;
    }

    resolveNavigationFloors();
    applyCrowdSeparation();
    resolveNavigationPenetration();
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

std::size_t HordeDirector::eliminateAllActive() noexcept {
    std::size_t eliminated = 0U;

    for (auto& zombieSlot : zombies_) {
        if (!zombieSlot.has_value() ||
            zombieSlot->frame().state ==
                ZombieState::Dead) {
            continue;
        }

        if (zombieSlot->applyDamage(
                std::numeric_limits<float>::max())) {
            ++eliminated;
        }
    }

    frame_.alive =
        frame_.alive > eliminated
        ? frame_.alive -
            static_cast<std::uint32_t>(eliminated)
        : 0U;

    return eliminated;
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

std::size_t HordeDirector::navigationFloorFor(
    Vec3 position) const noexcept {
    if (navigationFloorCount_ == 0U) {
        return kInvalidNavigationFloor;
    }

    std::size_t best =
        kInvalidNavigationFloor;

    float bestScore =
        std::numeric_limits<float>::max();

    for (std::size_t i = 0;
         i < navigationFloorCount_;
         ++i) {
        const auto& floor =
            navigationFloors_[i];

        const float nearestX =
            std::clamp(
                position.x,
                floor.minimum.x,
                floor.maximum.x);

        const float nearestZ =
            std::clamp(
                position.z,
                floor.minimum.z,
                floor.maximum.z);

        const float dx =
            position.x -
            nearestX;

        const float dz =
            position.z -
            nearestZ;

        const float dy =
            std::fabs(
                position.y -
                floor.maximum.y);

        const float score =
            dx * dx +
            dz * dz +
            dy * dy * 4.0f;

        if (score < bestScore) {
            bestScore = score;
            best = i;
        }
    }

    return best;
}

Vec3 HordeDirector::navigationWaypoint(
    std::size_t floorIndex) const noexcept {
    if (floorIndex >=
        navigationFloorCount_) {
        return {};
    }

    const auto& floor =
        navigationFloors_[
            floorIndex];

    return {
        (floor.minimum.x +
         floor.maximum.x) * 0.5f,
        floor.maximum.y,
        (floor.minimum.z +
         floor.maximum.z) * 0.5f,
    };
}

bool HordeDirector::navigationEdgeBlocked(
    std::size_t from,
    std::size_t to) const noexcept {
    if (from >= navigationFloorCount_ ||
        to >= navigationFloorCount_) {
        return true;
    }

    const Vec3 a =
        navigationWaypoint(from);

    const Vec3 b =
        navigationWaypoint(to);

    const float dx = b.x - a.x;
    const float dz = b.z - a.z;
    const float distanceSquared =
        dx * dx + dz * dz;

    if (distanceSquared <=
        1.0e-8f) {
        return false;
    }

    const float distance =
        std::sqrt(
            distanceSquared);

    Ray ray{};
    ray.origin = {
        a.x,
        std::min(a.y, b.y) + 0.55f,
        a.z,
    };
    ray.direction = {
        dx / distance,
        0.0f,
        dz / distance,
    };

    const float minimumBodyY =
        std::min(a.y, b.y) +
        0.04f;

    const float maximumBodyY =
        std::max(a.y, b.y) +
        1.75f;

    auto blocksSegment =
        [&](const Aabb& source) noexcept {
            if (source.maximum.y <
                    minimumBodyY ||
                source.minimum.y >
                    maximumBodyY) {
                return false;
            }

            const Aabb expanded{
                .minimum = {
                    source.minimum.x - 0.18f,
                    source.minimum.y,
                    source.minimum.z - 0.18f,
                },
                .maximum = {
                    source.maximum.x + 0.18f,
                    source.maximum.y,
                    source.maximum.z + 0.18f,
                },
            };

            return raycastAabb(
                ray,
                expanded,
                distance).hit;
        };

    for (std::size_t i = 0;
         i < navigationObstacleCount_;
         ++i) {
        if (blocksSegment(
                navigationObstacles_[i])) {
            return true;
        }
    }

    for (std::size_t i = 0;
         i < dynamicBlockerCount_;
         ++i) {
        const auto& blocker =
            dynamicBlockers_[i];

        if (!blocker.enabled ||
            blocker.breakable) {
            continue;
        }

        if (blocksSegment(
                blocker.obstacle)) {
            return true;
        }
    }

    return false;
}

bool HordeDirector::nextNavigationFloor(
    std::size_t start,
    std::size_t goal,
    std::size_t& outNext) const noexcept {
    outNext =
        kInvalidNavigationFloor;

    if (start >= navigationFloorCount_ ||
        goal >= navigationFloorCount_) {
        return false;
    }

    if (start == goal) {
        outNext = goal;
        return true;
    }

    std::array<float, kMaxHordeNavigationFloors>
        gScore{};

    std::array<float, kMaxHordeNavigationFloors>
        fScore{};

    std::array<std::size_t, kMaxHordeNavigationFloors>
        parent{};

    std::array<bool, kMaxHordeNavigationFloors>
        open{};

    std::array<bool, kMaxHordeNavigationFloors>
        closed{};

    gScore.fill(
        std::numeric_limits<float>::max());

    fScore.fill(
        std::numeric_limits<float>::max());

    parent.fill(
        kInvalidNavigationFloor);

    gScore[start] = 0.0f;
    fScore[start] =
        navigationDistance(
            navigationWaypoint(start),
            navigationWaypoint(goal));

    open[start] = true;

    for (std::size_t iteration = 0;
         iteration < navigationFloorCount_;
         ++iteration) {
        std::size_t current =
            kInvalidNavigationFloor;

        float best =
            std::numeric_limits<float>::max();

        for (std::size_t i = 0;
             i < navigationFloorCount_;
             ++i) {
            if (open[i] &&
                fScore[i] < best) {
                best = fScore[i];
                current = i;
            }
        }

        if (current ==
            kInvalidNavigationFloor) {
            break;
        }

        if (current == goal) {
            break;
        }

        open[current] = false;
        closed[current] = true;

        const std::size_t neighborCount =
            navigationNeighborCounts_[
                current];

        for (std::size_t n = 0;
             n < neighborCount;
             ++n) {
            const std::size_t neighbor =
                navigationNeighbors_[
                    current][n];

            if (neighbor >=
                    navigationFloorCount_ ||
                closed[neighbor] ||
                navigationEdgeBlocked(
                    current,
                    neighbor)) {
                continue;
            }

            const float tentative =
                gScore[current] +
                navigationDistance(
                    navigationWaypoint(
                        current),
                    navigationWaypoint(
                        neighbor));

            if (tentative >=
                gScore[neighbor]) {
                continue;
            }

            parent[neighbor] =
                current;

            gScore[neighbor] =
                tentative;

            fScore[neighbor] =
                tentative +
                navigationDistance(
                    navigationWaypoint(
                        neighbor),
                    navigationWaypoint(
                        goal));

            open[neighbor] = true;
        }
    }

    if (parent[goal] ==
        kInvalidNavigationFloor) {
        return false;
    }

    std::size_t step = goal;

    for (std::size_t guard = 0;
         guard < navigationFloorCount_;
         ++guard) {
        const std::size_t previous =
            parent[step];

        if (previous == start) {
            outNext = step;
            return true;
        }

        if (previous ==
            kInvalidNavigationFloor) {
            return false;
        }

        step = previous;
    }

    return false;
}


Vec3 HordeDirector::steeringTargetFor(
    const ZombieActor& actor,
    Vec3 playerFeetPosition,
    std::uint32_t& outDynamicBlockerId) const noexcept {
    outDynamicBlockerId = 0U;

    const auto& position =
        actor.frame().position;

    if (navigationFloorCount_ > 0U) {
        const std::size_t startFloor =
            navigationFloorFor(
                position);

        const std::size_t goalFloor =
            navigationFloorFor(
                playerFeetPosition);

        if (startFloor !=
                kInvalidNavigationFloor &&
            goalFloor !=
                kInvalidNavigationFloor &&
            startFloor != goalFloor) {
            std::size_t nextFloor =
                kInvalidNavigationFloor;

            if (nextNavigationFloor(
                    startFloor,
                    goalFloor,
                    nextFloor)) {
                playerFeetPosition =
                    navigationWaypoint(
                        nextFloor);
            } else {
                return position;
            }
        }
    }

    if (navigationObstacleCount_ == 0U &&
        dynamicBlockerCount_ == 0U) {
        return playerFeetPosition;
    }

    const float dx =
        playerFeetPosition.x -
        position.x;

    const float dz =
        playerFeetPosition.z -
        position.z;

    const float distanceSquared =
        dx * dx +
        dz * dz;

    if (distanceSquared <= 1.0e-8f) {
        return playerFeetPosition;
    }

    const float distance =
        std::sqrt(
            distanceSquared);

    const float inverseDistance =
        1.0f /
        distance;

    Ray ray{};
    ray.origin = {
        position.x,
        position.y +
            actor.config().bodyHeight *
                0.45f,
        position.z,
    };

    ray.direction = {
        dx * inverseDistance,
        0.0f,
        dz * inverseDistance,
    };

    const std::size_t totalObstacles =
        navigationObstacleCount_ + dynamicBlockerCount_;
    for (std::size_t obstacleIndex = 0;
         obstacleIndex < totalObstacles;
         ++obstacleIndex) {
        const Aabb* sourcePointer = nullptr;
        const DynamicBlocker* dynamicBlocker = nullptr;
        if (obstacleIndex < navigationObstacleCount_) {
            sourcePointer = &navigationObstacles_[obstacleIndex];
        } else {
            const auto& blocker =
                dynamicBlockers_[obstacleIndex - navigationObstacleCount_];
            if (!blocker.enabled) {
                continue;
            }
            dynamicBlocker = &blocker;
            sourcePointer = &blocker.obstacle;
        }
        const auto& source = *sourcePointer;

        const float marginX =
            actor.config().halfWidth +
            0.14f;

        const float marginZ =
            actor.config().halfDepth +
            0.14f;

        const Aabb expanded{
            .minimum = {
                source.minimum.x -
                    marginX,
                source.minimum.y,
                source.minimum.z -
                    marginZ,
            },
            .maximum = {
                source.maximum.x +
                    marginX,
                source.maximum.y,
                source.maximum.z +
                    marginZ,
            },
        };

        const auto obstruction =
            raycastAabb(
                ray,
                expanded,
                distance);

        if (!obstruction.hit) {
            continue;
        }

        if (dynamicBlocker != nullptr &&
            dynamicBlocker->breakable) {
            outDynamicBlockerId = dynamicBlocker->id;
            return {
                std::clamp(
                    playerFeetPosition.x,
                    expanded.minimum.x,
                    expanded.maximum.x),
                playerFeetPosition.y,
                std::clamp(
                    playerFeetPosition.z,
                    expanded.minimum.z,
                    expanded.maximum.z),
            };
        }

        const float cornerMargin = 0.18f;

        const std::array<Vec3, 4> candidates{{
            {
                expanded.minimum.x -
                    cornerMargin,
                playerFeetPosition.y,
                expanded.minimum.z -
                    cornerMargin,
            },
            {
                expanded.minimum.x -
                    cornerMargin,
                playerFeetPosition.y,
                expanded.maximum.z +
                    cornerMargin,
            },
            {
                expanded.maximum.x +
                    cornerMargin,
                playerFeetPosition.y,
                expanded.minimum.z -
                    cornerMargin,
            },
            {
                expanded.maximum.x +
                    cornerMargin,
                playerFeetPosition.y,
                expanded.maximum.z +
                    cornerMargin,
            },
        }};

        Vec3 best =
            playerFeetPosition;

        float bestCost =
            std::numeric_limits<float>::max();

        for (const auto& candidate :
             candidates) {
            const float boundedX =
                std::clamp(
                    candidate.x,
                    config_.arenaMinimumX,
                    config_.arenaMaximumX);

            const float boundedZ =
                std::clamp(
                    candidate.z,
                    config_.arenaMinimumZ,
                    config_.arenaMaximumZ);

            const float fromZombieX =
                boundedX -
                position.x;

            const float fromZombieZ =
                boundedZ -
                position.z;

            const float toPlayerX =
                playerFeetPosition.x -
                boundedX;

            const float toPlayerZ =
                playerFeetPosition.z -
                boundedZ;

            const float cost =
                std::sqrt(
                    fromZombieX *
                        fromZombieX +
                    fromZombieZ *
                        fromZombieZ) +
                std::sqrt(
                    toPlayerX *
                        toPlayerX +
                    toPlayerZ *
                        toPlayerZ);

            if (cost < bestCost) {
                bestCost = cost;
                best = {
                    boundedX,
                    playerFeetPosition.y,
                    boundedZ,
                };
            }
        }

        return best;
    }

    return playerFeetPosition;
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

void HordeDirector::resolveNavigationFloors() noexcept {
    if (navigationFloorCount_ == 0U) {
        return;
    }

    constexpr float kMaximumStep = kNavigationMaximumStep;

    for (auto& zombieSlot : zombies_) {
        if (!zombieSlot.has_value() ||
            zombieSlot->frame().state ==
                ZombieState::Dead) {
            continue;
        }

        const auto position =
            zombieSlot->frame().position;

        bool found = false;
        float bestY = -std::numeric_limits<float>::infinity();

        for (std::size_t i = 0;
             i < navigationFloorCount_;
             ++i) {
            const auto& floor =
                navigationFloors_[i];

            if (position.x < floor.minimum.x ||
                position.x > floor.maximum.x ||
                position.z < floor.minimum.z ||
                position.z > floor.maximum.z) {
                continue;
            }

            const float top =
                floor.maximum.y;

            if (std::fabs(
                    top -
                    position.y) >
                kMaximumStep) {
                continue;
            }

            if (!found || top > bestY) {
                bestY = top;
                found = true;
            }
        }

        if (found) {
            zombieSlot->setFeetY(
                bestY);
        }
    }
}

void HordeDirector::resolveNavigationPenetration() noexcept {
    for (auto& zombieSlot : zombies_) {
        if (!zombieSlot.has_value() ||
            zombieSlot->frame().state ==
                ZombieState::Dead) {
            continue;
        }

        const std::size_t totalObstacles =
            navigationObstacleCount_ + dynamicBlockerCount_;
        for (std::size_t obstacleIndex = 0;
             obstacleIndex < totalObstacles;
             ++obstacleIndex) {
            const Aabb* obstaclePointer = nullptr;
            if (obstacleIndex < navigationObstacleCount_) {
                obstaclePointer = &navigationObstacles_[obstacleIndex];
            } else {
                const auto& blocker =
                    dynamicBlockers_[obstacleIndex - navigationObstacleCount_];
                if (!blocker.enabled) {
                    continue;
                }
                obstaclePointer = &blocker.obstacle;
            }
            const auto& obstacle = *obstaclePointer;

            const auto position =
                zombieSlot->frame().
                    position;

            const float marginX =
                zombieSlot->config().
                    halfWidth +
                0.08f;

            const float marginZ =
                zombieSlot->config().
                    halfDepth +
                0.08f;

            const float minX =
                obstacle.minimum.x -
                marginX;

            const float maxX =
                obstacle.maximum.x +
                marginX;

            const float minZ =
                obstacle.minimum.z -
                marginZ;

            const float maxZ =
                obstacle.maximum.z +
                marginZ;

            const bool inside =
                position.x > minX &&
                position.x < maxX &&
                position.z > minZ &&
                position.z < maxZ;

            if (!inside) {
                continue;
            }

            const float toLeft =
                position.x -
                minX;

            const float toRight =
                maxX -
                position.x;

            const float toNear =
                position.z -
                minZ;

            const float toFar =
                maxZ -
                position.z;

            const float minimum =
                std::min({
                    toLeft,
                    toRight,
                    toNear,
                    toFar,
                });

            float pushX = 0.0f;
            float pushZ = 0.0f;

            if (minimum == toLeft) {
                pushX =
                    -(toLeft + 0.002f);
            } else if (minimum == toRight) {
                pushX =
                    toRight + 0.002f;
            } else if (minimum == toNear) {
                pushZ =
                    -(toNear + 0.002f);
            } else {
                pushZ =
                    toFar + 0.002f;
            }

            zombieSlot->
                translateHorizontal(
                    pushX,
                    pushZ);
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
