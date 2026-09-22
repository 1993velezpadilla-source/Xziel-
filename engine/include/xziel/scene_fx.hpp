#pragma once

#include "xziel/horror.hpp"
#include "xziel/performance.hpp"
#include "xziel/engine.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace xziel {

enum class DecalKind : std::uint8_t {
    BulletHole,
    Blood,
    Scorch,
    WetFootprint,
    Mud,
    Slime,
};

struct DecalDesc {
    DecalKind kind = DecalKind::BulletHole;
    Vec3 position{};
    Vec3 normal{0.0f, 1.0f, 0.0f};

    float size = 0.15f;
    float opacity = 1.0f;
    float lifetimeSeconds = 30.0f;

    std::uint32_t materialId = 0;
    bool persistent = false;
};

struct DecalItem {
    std::uint64_t id = 0;
    DecalDesc desc{};
    float ageSeconds = 0.0f;
};

class DecalPool final {
public:
    explicit DecalPool(std::uint32_t capacity = 256);

    void reset() noexcept;
    [[nodiscard]] std::uint64_t spawn(
        const DecalDesc& desc) noexcept;

    void advance(float deltaSeconds) noexcept;

    [[nodiscard]] std::size_t buildVisibleList(
        const Vec3& cameraPosition,
        float maxDistanceMeters,
        DecalItem* destination,
        std::size_t destinationCapacity) const noexcept;

    [[nodiscard]] std::uint32_t aliveCount() const noexcept;
    [[nodiscard]] std::uint32_t capacity() const noexcept;

private:
    struct Slot {
        DecalItem item{};
        bool alive = false;
    };

    [[nodiscard]] static float distanceSquared(
        const Vec3& a,
        const Vec3& b) noexcept;

    std::vector<Slot> slots_;
    std::uint64_t nextId_ = 1;
    std::uint32_t overwriteCursor_ = 0;
    std::uint32_t alive_ = 0;
};

struct PostProcessPlan {
    float exposureBiasEv = 0.0f;
    float bloomStrength = 0.0f;
    float bloomResolutionScale = 0.5f;
    float vignetteStrength = 0.0f;
    float filmGrainStrength = 0.0f;
    float chromaticAberrationStrength = 0.0f;
    float colorGradeStrength = 1.0f;
    float sharpenStrength = 0.0f;

    bool ambientOcclusionEnabled = true;
    float ambientOcclusionResolutionScale = 0.5f;
    std::uint32_t ambientOcclusionSampleBudget = 12;

    bool volumetricFogEnabled = true;
    bool temporalHistoryValid = true;
};

class PostProcessPlanner final {
public:
    [[nodiscard]] PostProcessPlan plan(
        const RenderWorkload& workload,
        const HorrorFrame& horror,
        bool cameraCut,
        bool playerUnderwater) const noexcept;
};

} // namespace xziel
