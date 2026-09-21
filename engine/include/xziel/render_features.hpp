#pragma once

#include "xziel/environment.hpp"
#include "xziel/performance.hpp"

#include <cstddef>
#include <cstdint>

namespace xziel {

enum class ReflectionSurfaceKind : std::uint8_t {
    Mirror,
    Water,
    WetFloor,
    Glass,
    PolishedMetal,
};

enum class ReflectionTechnique : std::uint8_t {
    Disabled,
    StaticProbe,
    Planar,
    ScreenSpace,
    HybridPlanarProbe,
    HybridScreenSpaceProbe,
};

struct ReflectionSurface {
    std::uint32_t id = 0;
    ReflectionSurfaceKind kind = ReflectionSurfaceKind::WetFloor;

    float distanceMeters = 0.0f;
    float screenCoverage = 0.0f;
    float importance = 1.0f;
    float roughness = 0.5f;

    bool visible = true;
    bool planarEligible = false;
    bool hasStaticProbe = true;
    bool animated = false;
};

struct ReflectionDecision {
    std::uint32_t surfaceId = 0;
    ReflectionTechnique technique = ReflectionTechnique::Disabled;

    float resolutionScale = 0.0f;
    float maxDistanceMeters = 0.0f;
    std::uint32_t updateEveryNFrames = 1;

    bool updateThisFrame = false;
    bool needsExtraScenePass = false;
    bool samplePreviousFrame = false;
};

struct WaterSurfaceState {
    float normalScrollU = 0.0f;
    float normalScrollV = 0.0f;
    float wavePhase = 0.0f;
    float foamStrength = 0.0f;
    float reflectionStrength = 0.0f;
    float refractionStrength = 0.0f;
    float fresnelBias = 0.02f;
    float roughness = 0.10f;
};

struct WaterConfig {
    float waveSpeed = 0.18f;
    float normalScrollSpeedU = 0.012f;
    float normalScrollSpeedV = -0.019f;
    float foamResponse = 0.55f;
    float baseReflection = 0.72f;
    float baseRefraction = 0.38f;
    float fresnelBias = 0.02f;
    float roughness = 0.10f;
};

class WaterSystem final {
public:
    explicit WaterSystem(WaterConfig config = {});

    void reset() noexcept;
    [[nodiscard]] WaterSurfaceState advance(
        float windSpeedMetersPerSecond,
        float rainIntensity,
        float deltaSeconds) noexcept;

private:
    WaterConfig config_{};
    WaterSurfaceState state_{};
};

struct ReflectionTargetPlan {
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    std::uint64_t estimatedColorBytes = 0;
    std::uint64_t estimatedDepthBytes = 0;
    bool enabled = false;
};

class ReflectionTargetPlanner final {
public:
    // Produces a bounded offscreen target size from a planner decision.
    // Dimensions are aligned down to 16 pixels for predictable tile memory.
    [[nodiscard]] ReflectionTargetPlan plan(
        std::uint32_t mainWidth,
        std::uint32_t mainHeight,
        const ReflectionDecision& decision,
        std::uint32_t maxDimension = 1536) const noexcept;
};

class ReflectionPlanner final {
public:
    // Decisions are written into caller-owned memory. At most the reflection
    // budget's number of extra scene passes will request Planar rendering.
    [[nodiscard]] std::size_t plan(
        const ReflectionSurface* surfaces,
        std::size_t surfaceCount,
        const RenderWorkload& workload,
        std::uint64_t frameIndex,
        ReflectionDecision* destination,
        std::size_t destinationCapacity) const noexcept;

private:
    [[nodiscard]] static float score(
        const ReflectionSurface& surface) noexcept;
};

enum class ShadowLightKind : std::uint8_t {
    Directional,
    Point,
    Spot,
};

enum class ShadowTechnique : std::uint8_t {
    Disabled,
    BakedOnly,
    ShadowMap,
    CascadedShadowMap,
};

struct ShadowRequest {
    std::uint32_t lightId = 0;
    ShadowLightKind kind = ShadowLightKind::Point;

    float distanceMeters = 0.0f;
    float intensity = 1.0f;
    float importance = 1.0f;

    bool visible = true;
    bool moving = false;
    bool hasBakedShadow = false;
    bool castsDynamicShadow = true;
};

struct ShadowDecision {
    std::uint32_t lightId = 0;
    ShadowTechnique technique = ShadowTechnique::Disabled;

    std::uint32_t resolution = 0;
    std::uint32_t cascadeCount = 0;
    std::uint32_t updateEveryNFrames = 1;

    bool updateThisFrame = false;
};

class ShadowPlanner final {
public:
    [[nodiscard]] std::size_t plan(
        const ShadowRequest* requests,
        std::size_t requestCount,
        const RenderWorkload& workload,
        std::uint64_t frameIndex,
        ShadowDecision* destination,
        std::size_t destinationCapacity) const noexcept;

private:
    [[nodiscard]] static float score(
        const ShadowRequest& request) noexcept;
};

} // namespace xziel
