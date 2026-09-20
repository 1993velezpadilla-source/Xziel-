#include "xziel/particles.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float safeDt(float dt) noexcept {
    if (!std::isfinite(dt) || dt <= 0.0f) {
        return 0.0f;
    }
    return std::min(dt, 0.05f);
}

float clamp01(float value) noexcept {
    return std::clamp(value, 0.0f, 1.0f);
}

} // namespace

ParticleEmitter::ParticleEmitter(
    ParticleEmitterConfig config,
    std::uint32_t capacity)
    : config_(config),
      capacity_(std::max<std::uint32_t>(1U, capacity)),
      px_(capacity_),
      py_(capacity_),
      pz_(capacity_),
      vx_(capacity_),
      vy_(capacity_),
      vz_(capacity_),
      age_(capacity_),
      lifetime_(capacity_),
      size_(capacity_),
      rotation_(capacity_) {
    reset();
}

void ParticleEmitter::reset() noexcept {
    alive_ = 0;
    spawnAccumulator_ = 0.0f;
    rngState_ = config_.randomSeed != 0 ? config_.randomSeed : 0x584A4945u;
}

void ParticleEmitter::setConfig(
    const ParticleEmitterConfig& config) noexcept {
    config_ = config;
    if (alive_ > config_.maxAlive) {
        alive_ = std::min(config_.maxAlive, capacity_);
    }
}

ParticleStats ParticleEmitter::advance(
    const ParticleSpawnContext& context,
    float deltaSeconds) noexcept {
    const float dt = safeDt(deltaSeconds);
    ParticleStats stats{};

    // Update existing particles first. Swap-removal keeps the active range
    // packed and prevents holes/branchy free-list traversal.
    std::uint32_t index = 0;
    while (index < alive_) {
        age_[index] += dt;
        if (age_[index] >= lifetime_[index]) {
            removeAt(index);
            ++stats.retiredThisFrame;
            continue;
        }

        const float drag = std::max(0.0f, 1.0f - config_.dragPerSecond * dt);
        vx_[index] = vx_[index] * drag +
            (config_.acceleration.x + context.windVelocity.x) * dt;
        vy_[index] = vy_[index] * drag +
            (config_.acceleration.y + context.windVelocity.y) * dt;
        vz_[index] = vz_[index] * drag +
            (config_.acceleration.z + context.windVelocity.z) * dt;

        px_[index] += vx_[index] * dt;
        py_[index] += vy_[index] * dt;
        pz_[index] += vz_[index] * dt;
        rotation_[index] += 0.35f * dt;
        ++index;
    }

    const float emitterDistanceSq =
        distanceSquared(config_.origin, context.cameraPosition);
    const float maxDistance = std::max(config_.spawnDistanceMeters, 0.1f);
    const bool distanceVisible =
        emitterDistanceSq <= maxDistance * maxDistance;

    if (!context.emitterVisible || !distanceVisible || dt <= 0.0f) {
        stats.culledEmitters = 1;
        stats.alive = alive_;
        return stats;
    }

    const float distance = std::sqrt(emitterDistanceSq);
    const float fadeStart = std::min(
        std::max(0.0f, config_.fadeStartDistanceMeters),
        maxDistance);
    float distanceScale = 1.0f;
    if (distance > fadeStart && maxDistance > fadeStart) {
        distanceScale =
            1.0f - (distance - fadeStart) / (maxDistance - fadeStart);
    }

    const float densityScale =
        clamp01(context.densityScale) * clamp01(distanceScale);
    const float spawnRate =
        std::max(0.0f, config_.particlesPerSecond) * densityScale;

    spawnAccumulator_ += spawnRate * dt;

    // Hard bound prevents a resumed/stalled frame from creating a spawn storm.
    const std::uint32_t requested =
        static_cast<std::uint32_t>(std::floor(spawnAccumulator_));
    const std::uint32_t frameSpawnCap = std::min<std::uint32_t>(
        128U,
        std::max<std::uint32_t>(1U, config_.maxAlive / 4U));
    const std::uint32_t toSpawn = std::min(requested, frameSpawnCap);
    spawnAccumulator_ -= static_cast<float>(toSpawn);

    for (std::uint32_t i = 0; i < toSpawn; ++i) {
        spawnOne(context, stats);
    }

    // Keep fractional debt, but never retain an unbounded backlog.
    spawnAccumulator_ = std::min(spawnAccumulator_, 2.0f);

    stats.alive = alive_;
    return stats;
}

std::size_t ParticleEmitter::buildRenderItems(
    const Vec3& cameraPosition,
    ParticleRenderItem* destination,
    std::size_t destinationCapacity) const noexcept {
    if (destination == nullptr || destinationCapacity == 0) {
        return 0;
    }

    const float maxDistance =
        std::max(config_.spawnDistanceMeters, 0.1f);
    const float maxDistanceSq = maxDistance * maxDistance;
    const float fadeStart =
        std::min(std::max(0.0f, config_.fadeStartDistanceMeters), maxDistance);

    std::size_t written = 0;
    for (std::uint32_t i = 0; i < alive_ && written < destinationCapacity; ++i) {
        const Vec3 position{px_[i], py_[i], pz_[i]};
        const float distSq = distanceSquared(position, cameraPosition);
        if (distSq > maxDistanceSq) {
            continue;
        }

        const float ageAlpha =
            1.0f - clamp01(age_[i] / std::max(lifetime_[i], 0.001f));
        const float distance = std::sqrt(distSq);
        float distanceAlpha = 1.0f;
        if (distance > fadeStart && maxDistance > fadeStart) {
            distanceAlpha =
                1.0f - (distance - fadeStart) / (maxDistance - fadeStart);
        }

        auto& item = destination[written++];
        item.position = position;
        item.size = size_[i];
        item.rotationRadians = rotation_[i];
        item.alpha = clamp01(ageAlpha * distanceAlpha);
        item.materialId = config_.materialId;
        item.kind = config_.kind;
        item.blend = config_.blend;
    }

    return written;
}

std::uint32_t ParticleEmitter::aliveCount() const noexcept {
    return alive_;
}

std::uint32_t ParticleEmitter::capacity() const noexcept {
    return capacity_;
}

const ParticleEmitterConfig& ParticleEmitter::config() const noexcept {
    return config_;
}

float ParticleEmitter::nextUnitRandom() noexcept {
    // xorshift32: tiny deterministic RNG suitable for cosmetic particles.
    std::uint32_t x = rngState_;
    x ^= x << 13U;
    x ^= x >> 17U;
    x ^= x << 5U;
    rngState_ = x == 0 ? 0x584A4945u : x;
    return static_cast<float>(rngState_ & 0x00FFFFFFU) /
        static_cast<float>(0x01000000U);
}

float ParticleEmitter::randomRange(float lo, float hi) noexcept {
    if (hi < lo) {
        std::swap(lo, hi);
    }
    return lo + (hi - lo) * nextUnitRandom();
}

Vec3 ParticleEmitter::randomSpawnPosition() noexcept {
    return {
        config_.origin.x + randomRange(-config_.halfExtents.x, config_.halfExtents.x),
        config_.origin.y + randomRange(-config_.halfExtents.y, config_.halfExtents.y),
        config_.origin.z + randomRange(-config_.halfExtents.z, config_.halfExtents.z),
    };
}

float ParticleEmitter::distanceSquared(
    const Vec3& a,
    const Vec3& b) const noexcept {
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    const float dz = a.z - b.z;
    return dx * dx + dy * dy + dz * dz;
}

void ParticleEmitter::spawnOne(
    const ParticleSpawnContext& context,
    ParticleStats& stats) noexcept {
    const std::uint32_t hardLimit =
        std::min(capacity_, std::max<std::uint32_t>(1U, config_.maxAlive));
    if (alive_ >= hardLimit) {
        ++stats.droppedByCapacity;
        return;
    }

    const std::uint32_t i = alive_++;
    const Vec3 position = randomSpawnPosition();
    px_[i] = position.x;
    py_[i] = position.y;
    pz_[i] = position.z;

    const float jitter = 0.25f;
    vx_[i] = config_.baseVelocity.x + context.windVelocity.x +
        randomRange(-jitter, jitter);
    vy_[i] = config_.baseVelocity.y + context.windVelocity.y +
        randomRange(-jitter, jitter);
    vz_[i] = config_.baseVelocity.z + context.windVelocity.z +
        randomRange(-jitter, jitter);

    age_[i] = 0.0f;
    lifetime_[i] = std::max(
        0.01f,
        randomRange(config_.lifetimeMinSeconds, config_.lifetimeMaxSeconds));
    size_[i] = std::max(
        0.001f,
        randomRange(config_.sizeMin, config_.sizeMax));
    rotation_[i] = randomRange(0.0f, 6.28318530718f);

    ++stats.spawnedThisFrame;
}

void ParticleEmitter::removeAt(std::uint32_t index) noexcept {
    if (index >= alive_) {
        return;
    }

    const std::uint32_t last = alive_ - 1U;
    if (index != last) {
        px_[index] = px_[last];
        py_[index] = py_[last];
        pz_[index] = pz_[last];
        vx_[index] = vx_[last];
        vy_[index] = vy_[last];
        vz_[index] = vz_[last];
        age_[index] = age_[last];
        lifetime_[index] = lifetime_[last];
        size_[index] = size_[last];
        rotation_[index] = rotation_[last];
    }
    --alive_;
}

} // namespace xziel
