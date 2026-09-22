#pragma once

#include "xziel/engine.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace xziel {

enum class ParticleKind : std::uint8_t {
    Rain,
    Splash,
    Fog,
    Mist,
    Smoke,
    Dust,
    Spark,
    Ember,
    Snow,
    Ash,
    BloodMist,
    Debris,
    Steam,
    Firefly,
};

enum class ParticleBlend : std::uint8_t {
    Opaque,
    Alpha,
    Additive,
    Premultiplied,
};

struct ParticleEmitterConfig {
    ParticleKind kind = ParticleKind::Rain;
    ParticleBlend blend = ParticleBlend::Alpha;

    Vec3 origin{};
    Vec3 halfExtents{1.0f, 1.0f, 1.0f};
    Vec3 baseVelocity{};
    Vec3 acceleration{};

    float particlesPerSecond = 32.0f;
    float lifetimeMinSeconds = 0.5f;
    float lifetimeMaxSeconds = 1.0f;
    float sizeMin = 0.03f;
    float sizeMax = 0.08f;

    float dragPerSecond = 0.0f;
    float spawnDistanceMeters = 35.0f;
    float fadeStartDistanceMeters = 24.0f;

    std::uint32_t materialId = 0;
    std::uint32_t maxAlive = 256;
    std::uint32_t randomSeed = 0x584A4945u; // "XJIE"-style stable seed.
};

struct ParticleSpawnContext {
    Vec3 cameraPosition{};
    Vec3 windVelocity{};
    float densityScale = 1.0f;
    bool emitterVisible = true;
};

struct ParticleRenderItem {
    Vec3 position{};
    float size = 1.0f;
    float rotationRadians = 0.0f;
    float alpha = 1.0f;
    std::uint32_t materialId = 0;
    ParticleKind kind = ParticleKind::Rain;
    ParticleBlend blend = ParticleBlend::Alpha;
};

struct ParticleStats {
    std::uint32_t alive = 0;
    std::uint32_t spawnedThisFrame = 0;
    std::uint32_t retiredThisFrame = 0;
    std::uint32_t droppedByCapacity = 0;
    std::uint32_t culledEmitters = 0;
};

class ParticleEmitter final {
public:
    explicit ParticleEmitter(
        ParticleEmitterConfig config = {},
        std::uint32_t capacity = 1024);

    void reset() noexcept;
    void setConfig(const ParticleEmitterConfig& config) noexcept;

    [[nodiscard]] ParticleStats advance(
        const ParticleSpawnContext& context,
        float deltaSeconds) noexcept;

    // Fills caller-owned memory. No allocation occurs in the update/render path.
    [[nodiscard]] std::size_t buildRenderItems(
        const Vec3& cameraPosition,
        ParticleRenderItem* destination,
        std::size_t destinationCapacity) const noexcept;

    [[nodiscard]] std::uint32_t aliveCount() const noexcept;
    [[nodiscard]] std::uint32_t capacity() const noexcept;
    [[nodiscard]] const ParticleEmitterConfig& config() const noexcept;

private:
    [[nodiscard]] float nextUnitRandom() noexcept;
    [[nodiscard]] float randomRange(float lo, float hi) noexcept;
    [[nodiscard]] Vec3 randomSpawnPosition() noexcept;
    [[nodiscard]] float distanceSquared(const Vec3& a, const Vec3& b) const noexcept;

    void spawnOne(const ParticleSpawnContext& context, ParticleStats& stats) noexcept;
    void removeAt(std::uint32_t index) noexcept;

    ParticleEmitterConfig config_{};
    std::uint32_t capacity_ = 0;

    // Structure-of-arrays: compact sequential passes are friendlier to mobile
    // cache/bandwidth than a large struct per particle.
    std::vector<float> px_;
    std::vector<float> py_;
    std::vector<float> pz_;
    std::vector<float> vx_;
    std::vector<float> vy_;
    std::vector<float> vz_;
    std::vector<float> age_;
    std::vector<float> lifetime_;
    std::vector<float> size_;
    std::vector<float> rotation_;

    std::uint32_t alive_ = 0;
    std::uint32_t rngState_ = 0;
    float spawnAccumulator_ = 0.0f;
};

} // namespace xziel
