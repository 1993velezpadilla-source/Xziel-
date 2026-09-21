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

    // Planar geometry is content data, not a hardcoded renderer assumption.
    // Normalize the plane so downstream camera reflection math is stable.
    std::array<xziel::ReflectionSurface, 1> verticalMirror{{{
        .id = 9,
        .kind = xziel::ReflectionSurfaceKind::Mirror,
        .distanceMeters = 2.0f,
        .screenCoverage = 0.40f,
        .importance = 1.0f,
        .roughness = 0.02f,
        .visible = true,
        .planarEligible = true,
        .hasStaticProbe = true,
        .planeNormalX = 2.0f,
        .planeNormalY = 0.0f,
        .planeNormalZ = 0.0f,
        .planeDistance = -6.0f,
    }}};
    std::array<xziel::ReflectionDecision, 1> verticalDecision{};
    assert(reflectionPlanner.plan(
        verticalMirror.data(), 1, high, 0,
        verticalDecision.data(), 1) == 1);
    assert(verticalDecision[0].planeNormalX == 1.0f);
    assert(verticalDecision[0].planeNormalY == 0.0f);
    assert(verticalDecision[0].planeNormalZ == 0.0f);
    assert(verticalDecision[0].planeDistance == -3.0f);

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

    // Equal-priority surfaces must choose the same authored surface even
    // when a streamed map chunk submits them in the opposite order.
    std::array<xziel::ReflectionSurface, 2> tieA{{
        {.id = 40, .kind = xziel::ReflectionSurfaceKind::Mirror,
         .distanceMeters = 4.0f, .screenCoverage = 0.30f, .importance = 1.0f,
         .roughness = 0.05f, .visible = true, .planarEligible = true,
         .hasStaticProbe = true},
        {.id = 41, .kind = xziel::ReflectionSurfaceKind::Mirror,
         .distanceMeters = 4.0f, .screenCoverage = 0.30f, .importance = 1.0f,
         .roughness = 0.05f, .visible = true, .planarEligible = true,
         .hasStaticProbe = true},
    }};
    std::array<xziel::ReflectionSurface, 2> tieB{{tieA[1], tieA[0]}};
    std::array<xziel::ReflectionDecision, 2> tieDecisionA{};
    std::array<xziel::ReflectionDecision, 2> tieDecisionB{};
    reflectionPlanner.plan(tieA.data(), tieA.size(), high, 2,
                           tieDecisionA.data(), tieDecisionA.size());
    reflectionPlanner.plan(tieB.data(), tieB.size(), high, 2,
                           tieDecisionB.data(), tieDecisionB.size());
    std::uint32_t selectedA = 0;
    std::uint32_t selectedB = 0;
    for (const auto& decision : tieDecisionA)
        if (decision.needsExtraScenePass) selectedA = decision.surfaceId;
    for (const auto& decision : tieDecisionB)
        if (decision.needsExtraScenePass) selectedB = decision.surfaceId;
    assert(selectedA == 40);
    assert(selectedB == 40);

    xziel::ReflectionTargetPlanner targetPlanner;
    const auto target = targetPlanner.plan(
        2400,
        1080,
        unorderedDecisions[1],
        1536);
    assert(target.enabled);
    assert(target.width == 1440);
    assert(target.height == 640);
    assert(target.width % 16 == 0);
    assert(target.height % 16 == 0);
    assert(target.estimatedColorBytes == 1440ULL * 640ULL * 4ULL);
    assert(target.estimatedDepthBytes == target.estimatedColorBytes);

    // Wide/high-resolution mobile displays must preserve aspect ratio when
    // the absolute target cap is reached. A per-axis clamp would incorrectly
    // turn this 16:9 source into a square-ish reflection texture.
    const auto cappedTarget = targetPlanner.plan(
        3840,
        2160,
        unorderedDecisions[1],
        1536);
    assert(cappedTarget.enabled);
    assert(cappedTarget.width == 1536);
    assert(cappedTarget.height == 864);
    assert(
        cappedTarget.width * 2160ULL ==
        cappedTarget.height * 3840ULL);

    xziel::ReflectionDecision previousFrameDecision{};
    previousFrameDecision.resolutionScale = 0.50f;
    previousFrameDecision.samplePreviousFrame = true;
    const auto previousFrameTarget = targetPlanner.plan(
        1920,
        1080,
        previousFrameDecision,
        1536);
    assert(previousFrameTarget.enabled);
    assert(previousFrameTarget.width == 960);
    assert(previousFrameTarget.height == 528);

    xziel::ReflectionDecision zeroScaleDecision{};
    zeroScaleDecision.needsExtraScenePass = true;
    zeroScaleDecision.resolutionScale = 0.0f;
    assert(
        !targetPlanner.plan(
             1920,
             1080,
             zeroScaleDecision,
             1536)
             .enabled);

    xziel::ReflectionDecision disabledTargetDecision{};
    const auto disabledTarget = targetPlanner.plan(
        2400,
        1080,
        disabledTargetDecision,
        1536);
    assert(!disabledTarget.enabled);

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
