#include "xziel/render_features.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float clamp01(float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

float wrap01(float value) noexcept {
    value = std::fmod(value, 1.0f);
    return value < 0.0f ? value + 1.0f : value;
}

std::uint32_t planarBudgetFor(const RenderWorkload& workload) noexcept {
    return workload.maxPlanarReflectionPasses;
}

std::uint32_t planarUpdateInterval(
    const RenderWorkload& workload,
    const ReflectionSurface& surface) noexcept {
    if (surface.kind == ReflectionSurfaceKind::Mirror) {
        return workload.quality == RenderQuality::Ultra ? 1U :
               workload.quality == RenderQuality::High ? 2U : 4U;
    }
    if (surface.kind == ReflectionSurfaceKind::Water) {
        return workload.quality == RenderQuality::Ultra ? 1U :
               workload.quality == RenderQuality::High ? 2U : 4U;
    }
    return 4U;
}

} // namespace

WaterSystem::WaterSystem(WaterConfig config)
    : config_(config) {
    reset();
}

void WaterSystem::reset() noexcept {
    state_ = {};
    state_.fresnelBias = config_.fresnelBias;
    state_.roughness = config_.roughness;
}

WaterSurfaceState WaterSystem::advance(
    float windSpeedMetersPerSecond,
    float rainIntensity,
    float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) || deltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(deltaSeconds, 0.10f);
    const float wind =
        std::clamp(std::fabs(windSpeedMetersPerSecond), 0.0f, 30.0f);
    const float rain = clamp01(rainIntensity);

    const float windScale = 1.0f + wind * 0.035f;
    state_.normalScrollU = wrap01(
        state_.normalScrollU +
        config_.normalScrollSpeedU * windScale * dt);
    state_.normalScrollV = wrap01(
        state_.normalScrollV +
        config_.normalScrollSpeedV * windScale * dt);
    state_.wavePhase = wrap01(
        state_.wavePhase + config_.waveSpeed * windScale * dt);

    state_.foamStrength =
        clamp01(config_.foamResponse * (rain * 0.70f + wind / 30.0f * 0.30f));
    state_.reflectionStrength =
        clamp01(config_.baseReflection + rain * 0.12f);
    state_.refractionStrength =
        clamp01(config_.baseRefraction - rain * 0.08f);
    state_.fresnelBias = std::clamp(config_.fresnelBias, 0.0f, 1.0f);
    state_.roughness =
        std::clamp(config_.roughness + wind * 0.004f, 0.02f, 0.65f);

    return state_;
}

ReflectionTargetPlan ReflectionTargetPlanner::plan(
    std::uint32_t mainWidth,
    std::uint32_t mainHeight,
    const ReflectionDecision& decision,
    std::uint32_t maxDimension) const noexcept {
    ReflectionTargetPlan out{};

    if (mainWidth == 0 ||
        mainHeight == 0 ||
        maxDimension < 16 ||
        decision.resolutionScale <= 0.0f ||
        (!decision.needsExtraScenePass &&
         !decision.samplePreviousFrame)) {
        return out;
    }

    const float requestedScale =
        std::clamp(
            decision.resolutionScale,
            0.10f,
            1.0f);

    // Clamp the target with one uniform scale. Independent width/height caps
    // distort the reflected image on wide displays (especially 18:9/20:9
    // phones), which then becomes visible as stretched water/mirror content.
    const float dimensionCapScale =
        std::min(
            static_cast<float>(maxDimension) /
                static_cast<float>(mainWidth),
            static_cast<float>(maxDimension) /
                static_cast<float>(mainHeight));

    const float scale =
        std::min(
            requestedScale,
            dimensionCapScale);

    const auto scaledDimension =
        [scale](
            std::uint32_t value) noexcept {
            const auto scaled =
                static_cast<std::uint32_t>(
                    std::max(
                        16.0f,
                        std::floor(
                            static_cast<float>(value) *
                            scale)));
            return std::max(
                16U,
                scaled & ~15U);
        };

    out.width =
        scaledDimension(mainWidth);
    out.height =
        scaledDimension(mainHeight);

    const std::uint64_t pixels =
        static_cast<std::uint64_t>(out.width) *
        static_cast<std::uint64_t>(out.height);

    // Current Vulkan target design uses one 32-bit color attachment and one
    // 32-bit depth attachment. Keeping this estimate beside the target policy
    // lets mobile memory budgets reject expensive reflection targets early.
    out.estimatedColorBytes = pixels * 4ULL;
    out.estimatedDepthBytes = pixels * 4ULL;
    out.enabled = true;
    return out;
}

std::size_t ReflectionPlanner::plan(
    const ReflectionSurface* surfaces,
    std::size_t surfaceCount,
    const RenderWorkload& workload,
    std::uint64_t frameIndex,
    ReflectionDecision* destination,
    std::size_t destinationCapacity) const noexcept {
    if (surfaces == nullptr ||
        destination == nullptr ||
        destinationCapacity == 0) {
        return 0;
    }

    const std::size_t count =
        std::min(surfaceCount, destinationCapacity);
    const std::uint32_t planarBudget =
        planarBudgetFor(workload);

    const auto isPlanarCandidate =
        [&workload](
            const ReflectionSurface& surface,
            float priority) noexcept {
            return surface.visible &&
                surface.distanceMeters <=
                    workload.reflectionDistanceMeters &&
                surface.screenCoverage > 0.0005f &&
                surface.planarEligible &&
                surface.roughness < 0.42f &&
                priority >= 0.10f &&
                workload.planarReflectionScale > 0.0f &&
                (surface.kind ==
                     ReflectionSurfaceKind::Mirror ||
                 surface.kind ==
                     ReflectionSurfaceKind::Water);
        };

    // Rank planar candidates in caller-owned memory order without allocating
    // or sorting. O(n^2) is deliberate here: reflection surface counts are
    // small, and this makes the scarce extra scene passes independent of
    // content submission order.
    for (std::size_t i = 0; i < count; ++i) {
        const auto& surface = surfaces[i];
        auto& out = destination[i];
        out = {};
        out.surfaceId = surface.id;

        const float planeLength = std::sqrt(
            surface.planeNormalX * surface.planeNormalX +
            surface.planeNormalY * surface.planeNormalY +
            surface.planeNormalZ * surface.planeNormalZ);
        if (std::isfinite(planeLength) && planeLength > 0.0001f) {
            const float inverseLength = 1.0f / planeLength;
            out.planeNormalX = surface.planeNormalX * inverseLength;
            out.planeNormalY = surface.planeNormalY * inverseLength;
            out.planeNormalZ = surface.planeNormalZ * inverseLength;
            out.planeDistance = std::isfinite(surface.planeDistance)
                ? surface.planeDistance * inverseLength
                : 0.0f;
        }

        if (!surface.visible ||
            surface.distanceMeters > workload.reflectionDistanceMeters ||
            surface.screenCoverage <= 0.0005f) {
            out.technique = ReflectionTechnique::Disabled;
            continue;
        }

        const float priority = score(surface);
        const bool lowRoughness = surface.roughness < 0.42f;

        bool wantsPlanar = false;
        if (planarBudget > 0 &&
            isPlanarCandidate(
                surface,
                priority)) {
            std::uint32_t higherPriorityCandidates = 0;

            for (std::size_t otherIndex = 0;
                 otherIndex < count;
                 ++otherIndex) {
                if (otherIndex == i) {
                    continue;
                }

                const auto& other =
                    surfaces[otherIndex];
                const float otherPriority =
                    score(other);

                if (!isPlanarCandidate(
                        other,
                        otherPriority)) {
                    continue;
                }

                // Stable tie-break by authored surface id rather than
                // submission order. Streaming/chunk traversal can reorder
                // otherwise identical surfaces between frames; using index
                // here would make the expensive planar slot flicker.
                const bool outranks =
                    otherPriority > priority ||
                    (otherPriority == priority &&
                     (other.id < surface.id ||
                      (other.id == surface.id &&
                       otherIndex < i)));

                if (outranks) {
                    ++higherPriorityCandidates;
                }
            }

            wantsPlanar =
                higherPriorityCandidates <
                planarBudget;
        }

        if (wantsPlanar) {
            out.technique = surface.hasStaticProbe
                ? ReflectionTechnique::HybridPlanarProbe
                : ReflectionTechnique::Planar;
            out.resolutionScale = workload.planarReflectionScale;
            out.maxDistanceMeters = workload.reflectionDistanceMeters;
            out.updateEveryNFrames =
                planarUpdateInterval(workload, surface);
            out.updateThisFrame =
                frameIndex % out.updateEveryNFrames == 0;
            out.needsExtraScenePass = out.updateThisFrame;
            out.samplePreviousFrame = !out.updateThisFrame;
            continue;
        }

        if (workload.ssrEnabled &&
            lowRoughness &&
            surface.kind != ReflectionSurfaceKind::Mirror) {
            out.technique = surface.hasStaticProbe
                ? ReflectionTechnique::HybridScreenSpaceProbe
                : ReflectionTechnique::ScreenSpace;
            out.resolutionScale = workload.ssrResolutionScale;
            out.maxDistanceMeters = workload.reflectionDistanceMeters;
            out.samplePreviousFrame = true;
            continue;
        }

        if (surface.hasStaticProbe) {
            out.technique = ReflectionTechnique::StaticProbe;
            out.resolutionScale = 1.0f;
            out.maxDistanceMeters = workload.reflectionDistanceMeters;
        }
    }

    return count;
}

float ReflectionPlanner::score(
    const ReflectionSurface& surface) noexcept {
    const float distanceWeight =
        1.0f / (1.0f + std::max(0.0f, surface.distanceMeters) * 0.08f);
    const float coverageWeight =
        std::sqrt(clamp01(surface.screenCoverage));
    const float roughnessWeight =
        1.0f - clamp01(surface.roughness);
    return std::max(0.0f, surface.importance) *
        distanceWeight *
        (0.35f + 0.65f * coverageWeight) *
        (0.45f + 0.55f * roughnessWeight);
}

std::size_t ShadowPlanner::plan(
    const ShadowRequest* requests,
    std::size_t requestCount,
    const RenderWorkload& workload,
    std::uint64_t frameIndex,
    ShadowDecision* destination,
    std::size_t destinationCapacity) const noexcept {
    if (requests == nullptr ||
        destination == nullptr ||
        destinationCapacity == 0) {
        return 0;
    }

    const std::size_t count =
        std::min(requestCount, destinationCapacity);
    std::uint32_t dynamicRemaining = workload.shadowedLightBudget;

    for (std::size_t i = 0; i < count; ++i) {
        const auto& request = requests[i];
        auto& out = destination[i];
        out = {};
        out.lightId = request.lightId;

        if (!request.visible) {
            out.technique = request.hasBakedShadow
                ? ShadowTechnique::BakedOnly
                : ShadowTechnique::Disabled;
            continue;
        }

        const float maxDistance =
            42.0f * std::max(0.25f, workload.shadowDistanceScale);
        const bool inRange =
            request.kind == ShadowLightKind::Directional ||
            request.distanceMeters <= maxDistance;
        const bool worthy =
            score(request) >= 0.055f;

        if (!request.castsDynamicShadow ||
            !inRange ||
            !worthy ||
            dynamicRemaining == 0) {
            out.technique = request.hasBakedShadow
                ? ShadowTechnique::BakedOnly
                : ShadowTechnique::Disabled;
            continue;
        }

        if (request.kind == ShadowLightKind::Directional) {
            out.technique = ShadowTechnique::CascadedShadowMap;
            out.cascadeCount =
                workload.quality == RenderQuality::Ultra ? 4U :
                workload.quality == RenderQuality::High ? 3U : 2U;
            out.resolution = workload.shadowMapResolution;
            out.updateEveryNFrames = 1;
            out.updateThisFrame = true;
            --dynamicRemaining;
            continue;
        }

        // Point-light cubemaps are much more expensive than spot shadow maps.
        // On Low we prefer baked/no point shadows. Medium+ updates them less
        // frequently unless the light is moving.
        if (request.kind == ShadowLightKind::Point &&
            workload.quality == RenderQuality::Low) {
            out.technique = request.hasBakedShadow
                ? ShadowTechnique::BakedOnly
                : ShadowTechnique::Disabled;
            continue;
        }

        out.technique = ShadowTechnique::ShadowMap;
        out.resolution = workload.shadowMapResolution;
        out.updateEveryNFrames =
            request.moving ? 1U :
            request.kind == ShadowLightKind::Point ? 4U : 2U;
        out.updateThisFrame =
            frameIndex % out.updateEveryNFrames == 0;
        --dynamicRemaining;
    }

    return count;
}

float ShadowPlanner::score(
    const ShadowRequest& request) noexcept {
    const float distanceWeight =
        request.kind == ShadowLightKind::Directional
        ? 1.0f
        : 1.0f /
          (1.0f + std::max(0.0f, request.distanceMeters) * 0.10f);
    const float intensityWeight =
        std::sqrt(std::max(0.0f, request.intensity));
    return std::max(0.0f, request.importance) *
        distanceWeight *
        (0.35f + 0.65f * intensityWeight);
}

} // namespace xziel
