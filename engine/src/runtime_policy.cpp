#include "xziel/runtime_policy.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

RuntimePolicy RuntimePolicyPlanner::plan(
    const RuntimePolicyInput& input) const noexcept {
    RuntimePolicy out{};

    const float refresh =
        (!std::isfinite(input.displayRefreshHz) ||
         input.displayRefreshHz < 30.0f)
        ? 60.0f
        : std::clamp(input.displayRefreshHz, 30.0f, 240.0f);

    switch (input.gameMode) {
        case UserGameMode::Performance:
            out.preferredFps =
                refresh >= 119.0f ? 120.0f :
                refresh >= 89.0f ? 90.0f :
                60.0f;
            out.maximumQuality = RenderQuality::Ultra;
            out.textureBudgetScale = 1.0f;
            out.meshBudgetScale = 1.0f;
            out.audioBudgetScale = 1.0f;
            out.requestHighRefreshRate =
                refresh >= 89.0f;
            break;

        case UserGameMode::Battery:
            out.preferredFps = 60.0f;
            out.maximumQuality = RenderQuality::Medium;
            out.textureBudgetScale = 0.72f;
            out.meshBudgetScale = 0.78f;
            out.audioBudgetScale = 0.85f;
            out.requestHighRefreshRate = false;
            break;

        case UserGameMode::Standard:
            out.preferredFps =
                refresh >= 89.0f ? 90.0f : 60.0f;
            out.maximumQuality = RenderQuality::High;
            out.textureBudgetScale = 0.90f;
            out.meshBudgetScale = 0.90f;
            out.audioBudgetScale = 0.95f;
            out.requestHighRefreshRate =
                refresh >= 89.0f;
            break;
    }

    if (input.batterySaver && !input.charging) {
        out.preferredFps =
            std::min(out.preferredFps, 60.0f);
        out.maximumQuality =
            qualityRank(out.maximumQuality) >
            qualityRank(RenderQuality::Medium)
            ? RenderQuality::Medium
            : out.maximumQuality;

        out.textureBudgetScale *= 0.82f;
        out.meshBudgetScale *= 0.86f;
        out.audioBudgetScale *= 0.92f;
        out.requestHighRefreshRate = false;
    }

    switch (input.memoryPressure) {
        case MemoryPressure::Normal:
            break;

        case MemoryPressure::Elevated:
            out.textureBudgetScale *= 0.72f;
            out.meshBudgetScale *= 0.78f;
            out.audioBudgetScale *= 0.86f;
            if (qualityRank(out.maximumQuality) >
                qualityRank(RenderQuality::High)) {
                out.maximumQuality = RenderQuality::High;
            }
            break;

        case MemoryPressure::Critical:
            out.textureBudgetScale *= 0.48f;
            out.meshBudgetScale *= 0.58f;
            out.audioBudgetScale *= 0.68f;
            out.maximumQuality = RenderQuality::Low;
            out.preferredFps =
                std::min(out.preferredFps, 60.0f);
            out.requestHighRefreshRate = false;
            break;
    }

    const bool hasThermalHeadroom =
        std::isfinite(input.thermalHeadroom) &&
        input.thermalHeadroom >= 0.0f;

    const bool hasCpuHeadroom =
        std::isfinite(input.cpuHeadroomPercent) &&
        input.cpuHeadroomPercent >= 0.0f;

    const bool hasGpuHeadroom =
        std::isfinite(input.gpuHeadroomPercent) &&
        input.gpuHeadroomPercent >= 0.0f;

    // React before severe thermal throttling instead of after clocks collapse.
    // 1.0 is Android's documented severe-throttling threshold. The softer
    // 0.88 guard leaves recovery margin without turning ordinary warm play
    // into an aggressive quality downgrade.
    if (hasThermalHeadroom &&
        input.thermalHeadroom >= 0.98f) {
        out.preferredFps =
            std::min(out.preferredFps, 60.0f);
        out.maximumQuality =
            RenderQuality::Low;
        out.textureBudgetScale *= 0.72f;
        out.meshBudgetScale *= 0.72f;
        out.audioBudgetScale *= 0.90f;
        out.requestHighRefreshRate = false;
        out.allowRayQueryExperimental = false;
    } else if (hasThermalHeadroom &&
               input.thermalHeadroom >= 0.88f) {
        out.preferredFps =
            std::min(out.preferredFps, 60.0f);
        if (qualityRank(out.maximumQuality) >
            qualityRank(RenderQuality::Medium)) {
            out.maximumQuality =
                RenderQuality::Medium;
        }
        out.textureBudgetScale *= 0.86f;
        out.meshBudgetScale *= 0.86f;
        out.requestHighRefreshRate = false;
        out.allowRayQueryExperimental = false;
    }

    // Android 16 headroom reports available capacity in percent. Keep these
    // guards deliberately conservative; the frame-time governor remains the
    // primary controller, while headroom only prevents obviously saturated
    // devices from requesting a higher tier.
    if (hasGpuHeadroom &&
        input.gpuHeadroomPercent < 8.0f) {
        if (qualityRank(out.maximumQuality) >
            qualityRank(RenderQuality::Medium)) {
            out.maximumQuality =
                RenderQuality::Medium;
        }
        out.requestHighRefreshRate = false;
        out.allowRayQueryExperimental = false;
    }

    if (hasCpuHeadroom &&
        input.cpuHeadroomPercent < 8.0f) {
        out.preferredFps =
            std::min(out.preferredFps, 60.0f);
        out.requestHighRefreshRate = false;
    }

    out.textureBudgetScale =
        std::clamp(out.textureBudgetScale, 0.20f, 1.0f);
    out.meshBudgetScale =
        std::clamp(out.meshBudgetScale, 0.20f, 1.0f);
    out.audioBudgetScale =
        std::clamp(out.audioBudgetScale, 0.20f, 1.0f);

    out.allowRayQueryExperimental =
        input.gameMode == UserGameMode::Performance &&
        input.memoryPressure == MemoryPressure::Normal &&
        !input.batterySaver;

    return out;
}

RenderWorkload RuntimePolicyPlanner::applyCeiling(
    const RenderWorkload& workload,
    const RuntimePolicy& policy) const noexcept {
    RenderWorkload out = workload;

    if (qualityRank(out.quality) <=
        qualityRank(policy.maximumQuality)) {
        return out;
    }

    // Apply conservative presentation-only ceilings. Gameplay simulation rates
    // live elsewhere and are not modified by Game Mode or memory pressure.
    if (policy.maximumQuality == RenderQuality::Low) {
        out.quality = RenderQuality::Low;
        out.renderScale = std::min(out.renderScale, 0.70f);
        out.particleDensityScale =
            std::min(out.particleDensityScale, 0.42f);
        out.shadowDistanceScale =
            std::min(out.shadowDistanceScale, 0.40f);
        out.fogQualityScale =
            std::min(out.fogQualityScale, 0.35f);
        out.dynamicLightBudget =
            std::min<std::uint32_t>(out.dynamicLightBudget, 4);
        out.shadowedLightBudget =
            std::min<std::uint32_t>(out.shadowedLightBudget, 1);
        out.shadowMapResolution =
            std::min<std::uint32_t>(out.shadowMapResolution, 512);
        out.maxPlanarReflectionPasses = 0;
        out.planarReflectionScale = 0.0f;
        out.ssrEnabled = false;
        out.ssrResolutionScale = 0.0f;
        out.ssrMaxSteps = 0;
        out.volumetricFogSteps =
            std::min<std::uint32_t>(out.volumetricFogSteps, 8);
        out.postProcessScale =
            std::min(out.postProcessScale, 0.50f);
    } else if (
        policy.maximumQuality ==
        RenderQuality::Medium) {
        out.quality = RenderQuality::Medium;
        out.renderScale = std::min(out.renderScale, 0.82f);
        out.particleDensityScale =
            std::min(out.particleDensityScale, 0.62f);
        out.shadowDistanceScale =
            std::min(out.shadowDistanceScale, 0.62f);
        out.fogQualityScale =
            std::min(out.fogQualityScale, 0.58f);
        out.dynamicLightBudget =
            std::min<std::uint32_t>(out.dynamicLightBudget, 8);
        out.shadowedLightBudget =
            std::min<std::uint32_t>(out.shadowedLightBudget, 2);
        out.shadowMapResolution =
            std::min<std::uint32_t>(out.shadowMapResolution, 768);
        out.maxPlanarReflectionPasses =
            std::min<std::uint32_t>(
                out.maxPlanarReflectionPasses, 1);
        out.planarReflectionScale =
            std::min(out.planarReflectionScale, 0.40f);
        out.ssrEnabled = false;
        out.ssrResolutionScale = 0.0f;
        out.ssrMaxSteps = 0;
        out.volumetricFogSteps =
            std::min<std::uint32_t>(
                out.volumetricFogSteps, 12);
        out.postProcessScale =
            std::min(out.postProcessScale, 0.60f);
    } else {
        out.quality = RenderQuality::High;
        out.renderScale = std::min(out.renderScale, 0.92f);
        out.maxPlanarReflectionPasses =
            std::min<std::uint32_t>(
                out.maxPlanarReflectionPasses, 1);
        out.planarReflectionScale =
            std::min(out.planarReflectionScale, 0.60f);
        out.ssrResolutionScale =
            std::min(out.ssrResolutionScale, 0.50f);
        out.ssrMaxSteps =
            std::min<std::uint32_t>(out.ssrMaxSteps, 24);
        out.shadowMapResolution =
            std::min<std::uint32_t>(
                out.shadowMapResolution, 1024);
        out.volumetricFogSteps =
            std::min<std::uint32_t>(
                out.volumetricFogSteps, 24);
        out.postProcessScale =
            std::min(out.postProcessScale, 0.75f);
    }

    return out;
}

int RuntimePolicyPlanner::qualityRank(
    RenderQuality quality) noexcept {
    switch (quality) {
        case RenderQuality::Low: return 0;
        case RenderQuality::Medium: return 1;
        case RenderQuality::High: return 2;
        case RenderQuality::Ultra: return 3;
    }
    return 0;
}

} // namespace xziel
