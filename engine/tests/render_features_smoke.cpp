#include "xziel/render_features.hpp"

#include <array>
#include <cassert>

int main() {
    xziel::RenderWorkload high{};
    high.quality = xziel::RenderQuality::High;
    high.shadowedLightBudget = 3;
    high.shadowMapResolution = 1024;
    high.shadowDistanceScale = 0.82f;
    high.maxPlanarReflectionPasses = 1;
    high.planarReflectionScale = 0.60f;
    high.reflectionDistanceMeters = 35.0f;
    high.ssrEnabled = true;
    high.ssrResolutionScale = 0.50f;

    std::array<xziel::ReflectionSurface, 3> surfaces{{
        {
            .id = 1,
            .kind = xziel::ReflectionSurfaceKind::Mirror,
            .distanceMeters = 4.0f,
            .screenCoverage = 0.30f,
            .importance = 1.0f,
            .roughness = 0.05f,
            .visible = true,
            .planarEligible = true,
            .hasStaticProbe = true,
        },
        {
            .id = 2,
            .kind = xziel::ReflectionSurfaceKind::Water,
            .distanceMeters = 8.0f,
            .screenCoverage = 0.24f,
            .importance = 0.9f,
            .roughness = 0.12f,
            .visible = true,
            .planarEligible = true,
            .hasStaticProbe = true,
        },
        {
            .id = 3,
            .kind = xziel::ReflectionSurfaceKind::WetFloor,
            .distanceMeters = 5.0f,
            .screenCoverage = 0.45f,
            .importance = 0.7f,
            .roughness = 0.22f,
            .visible = true,
            .planarEligible = false,
            .hasStaticProbe = true,
        },
    }};

    std::array<xziel::ReflectionDecision, 3> reflectionDecisions{};
    xziel::ReflectionPlanner reflectionPlanner;
    const auto reflectionCount = reflectionPlanner.plan(
        surfaces.data(),
        surfaces.size(),
        high,
        2,
        reflectionDecisions.data(),
        reflectionDecisions.size());
    assert(reflectionCount == surfaces.size());

    std::uint32_t extraPasses = 0;
    for (const auto& decision : reflectionDecisions) {
        if (decision.needsExtraScenePass) {
            ++extraPasses;
        }
    }
    assert(extraPasses <= high.maxPlanarReflectionPasses);
    assert(
        reflectionDecisions[0].technique ==
            xziel::ReflectionTechnique::HybridPlanarProbe ||
        reflectionDecisions[0].technique ==
            xziel::ReflectionTechnique::Planar);
    assert(
        reflectionDecisions[2].technique ==
        xziel::ReflectionTechnique::HybridScreenSpaceProbe);

    // Submission order must not steal the single expensive planar slot.
    // A lower-priority water surface is deliberately listed before the mirror.
    std::array<xziel::ReflectionSurface, 2> unorderedSurfaces{{
        {
            .id = 21,
            .kind = xziel::ReflectionSurfaceKind::Water,
            .distanceMeters = 18.0f,
            .screenCoverage = 0.08f,
            .importance = 0.45f,
            .roughness = 0.18f,
            .visible = true,
            .planarEligible = true,
            .hasStaticProbe = true,
        },
        {
            .id = 22,
            .kind = xziel::ReflectionSurfaceKind::Mirror,
            .distanceMeters = 3.0f,
            .screenCoverage = 0.42f,
            .importance = 1.0f,
            .roughness = 0.04f,
            .visible = true,
            .planarEligible = true,
            .hasStaticProbe = true,
        },
    }};

    std::array<xziel::ReflectionDecision, 2> unorderedDecisions{};
    const auto unorderedCount = reflectionPlanner.plan(
        unorderedSurfaces.data(),
        unorderedSurfaces.size(),
        high,
        2,
        unorderedDecisions.data(),
        unorderedDecisions.size());
    assert(unorderedCount == unorderedSurfaces.size());
    assert(
        unorderedDecisions[1].technique ==
            xziel::ReflectionTechnique::HybridPlanarProbe ||
        unorderedDecisions[1].technique ==
            xziel::ReflectionTechnique::Planar);
    assert(!unorderedDecisions[0].needsExtraScenePass);
    assert(unorderedDecisions[1].needsExtraScenePass);

    std::array<xziel::ShadowRequest, 4> lights{{
        {
            .lightId = 10,
            .kind = xziel::ShadowLightKind::Directional,
            .intensity = 1.0f,
            .importance = 1.0f,
        },
        {
            .lightId = 11,
            .kind = xziel::ShadowLightKind::Spot,
            .distanceMeters = 6.0f,
            .intensity = 2.0f,
            .importance = 1.0f,
            .moving = true,
        },
        {
            .lightId = 12,
            .kind = xziel::ShadowLightKind::Point,
            .distanceMeters = 10.0f,
            .intensity = 1.6f,
            .importance = 0.8f,
            .hasBakedShadow = true,
        },
        {
            .lightId = 13,
            .kind = xziel::ShadowLightKind::Point,
            .distanceMeters = 80.0f,
            .intensity = 1.0f,
            .importance = 0.5f,
            .hasBakedShadow = true,
        },
    }};

    std::array<xziel::ShadowDecision, 4> shadowDecisions{};
    xziel::ShadowPlanner shadowPlanner;
    const auto shadowCount = shadowPlanner.plan(
        lights.data(),
        lights.size(),
        high,
        8,
        shadowDecisions.data(),
        shadowDecisions.size());
    assert(shadowCount == lights.size());

    std::uint32_t dynamicShadows = 0;
    for (const auto& decision : shadowDecisions) {
        if (decision.technique == xziel::ShadowTechnique::ShadowMap ||
            decision.technique == xziel::ShadowTechnique::CascadedShadowMap) {
            ++dynamicShadows;
        }
    }
    assert(dynamicShadows <= high.shadowedLightBudget);
    assert(
        shadowDecisions[3].technique ==
        xziel::ShadowTechnique::BakedOnly);

    xziel::WaterSystem water;
    const auto wet = water.advance(8.0f, 1.0f, 1.0f / 60.0f);
    assert(wet.foamStrength > 0.0f);
    assert(wet.reflectionStrength > 0.0f);
    assert(wet.roughness >= 0.02f);

    return 0;
}
