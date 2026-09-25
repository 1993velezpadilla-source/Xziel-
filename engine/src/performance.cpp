#include "xziel/performance.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

PerformanceGovernor::PerformanceGovernor(PerformanceConfig config)
    : config_(config) {
    reset();
}

void PerformanceGovernor::reset() noexcept {
    qualityIndex_ = 2;
    smoothedFrameMs_ = 0.0f;
    smoothedCpuMs_ = 0.0f;
    smoothedGpuMs_ = 0.0f;
    smoothedGpuPreWorldMs_ = 0.0f;
    smoothedGpuWorldMs_ = 0.0f;
    smoothedGpuCompositeUiMs_ = 0.0f;
    smoothedIntervalMs_ = 0.0f;
    bottleneck_ =
        PerformanceBottleneck::Balanced;
    pendingBottleneck_ =
        PerformanceBottleneck::Balanced;
    bottleneckHoldSeconds_ = 0.0f;
    gpuPassBottleneck_ =
        GpuPassBottleneck::Balanced;
    pendingGpuPassBottleneck_ =
        GpuPassBottleneck::Balanced;
    gpuPassHoldSeconds_ = 0.0f;
    overloadSeconds_ = 0.0f;
    recoverySeconds_ = 0.0f;
    rebuildWorkload();
}

RenderWorkload PerformanceGovernor::advance(
    const PerformanceSample& sample,
    float deltaSeconds) noexcept {
    const float dt = std::clamp(deltaSeconds, 0.0f, 0.25f);
    const float frameMs = std::max(sample.cpuFrameMs, sample.gpuFrameMs);

    const float alpha =
        std::clamp(
            config_.smoothing,
            0.001f,
            1.0f);

    if (std::isfinite(frameMs) && frameMs > 0.0f) {
        if (smoothedFrameMs_ <= 0.0f) {
            smoothedFrameMs_ = frameMs;
        } else {
            smoothedFrameMs_ +=
                (frameMs - smoothedFrameMs_) *
                alpha;
        }
    }

    const auto smoothMetric =
        [alpha](
            float value,
            float& smoothed) noexcept {
            if (!std::isfinite(value) ||
                value <= 0.0f) {
                return;
            }

            if (smoothed <= 0.0f) {
                smoothed = value;
            } else {
                smoothed +=
                    (value - smoothed) *
                    alpha;
            }
        };

    smoothMetric(
        sample.cpuFrameMs,
        smoothedCpuMs_);

    smoothMetric(
        sample.gpuFrameMs,
        smoothedGpuMs_);

    if (sample.gpuPassTimingAuthoritative) {
        smoothMetric(
            sample.gpuPreWorldMs,
            smoothedGpuPreWorldMs_);
        smoothMetric(
            sample.gpuWorldMs,
            smoothedGpuWorldMs_);
        smoothMetric(
            sample.gpuCompositeUiMs,
            smoothedGpuCompositeUiMs_);
    }

    smoothMetric(
        sample.frameIntervalMs,
        smoothedIntervalMs_);

    const float targetMs =
        1000.0f / std::max(config_.targetFps, 1.0f);

    classifyBottleneck(
        sample,
        targetMs);

    classifyGpuPass(
        sample,
        targetMs);

    const bool overloaded =
        smoothedFrameMs_ > targetMs * config_.degradeThreshold;
    const bool comfortablyUnder =
        smoothedFrameMs_ > 0.0f &&
        smoothedFrameMs_ < targetMs * config_.recoverThreshold;

    if (overloaded) {
        overloadSeconds_ += dt;
        recoverySeconds_ = 0.0f;
    } else if (comfortablyUnder) {
        recoverySeconds_ += dt;
        overloadSeconds_ = 0.0f;
    } else {
        overloadSeconds_ = std::max(0.0f, overloadSeconds_ - dt);
        recoverySeconds_ = std::max(0.0f, recoverySeconds_ - dt);
    }

    if (overloadSeconds_ >= config_.degradeHoldSeconds) {
        stepDown();
        overloadSeconds_ = 0.0f;
        recoverySeconds_ = 0.0f;
    } else if (recoverySeconds_ >= config_.recoverHoldSeconds) {
        stepUp();
        recoverySeconds_ = 0.0f;
    }

    applyThermalCeiling(sample.thermal);
    rebuildWorkload();

    // SOURCE_FIDELITY_RENDER_SCALE_FLOOR_V1
    // Normal performance pressure trims expensive effects before destroying
    // scene resolution. Sub-0.90 rendering is reserved for real thermal
    // protection instead of software-Vulkan/CI pacing noise.
    switch (sample.thermal) {
        case ThermalLevel::Nominal:
        case ThermalLevel::Light:
            workload_.renderScale =
                std::max(
                    workload_.renderScale,
                    0.90f);
            break;

        case ThermalLevel::Moderate:
            workload_.renderScale =
                std::min(
                    workload_.renderScale,
                    0.90f);
            break;

        case ThermalLevel::Severe:
            workload_.renderScale =
                std::min(
                    workload_.renderScale,
                    0.84f);
            break;

        case ThermalLevel::Critical:
            workload_.renderScale =
                std::min(
                    workload_.renderScale,
                    0.78f);
            break;
    }

    return workload_;
}

const RenderWorkload& PerformanceGovernor::workload() const noexcept {
    return workload_;
}

float PerformanceGovernor::smoothedFrameMs() const noexcept {
    return smoothedFrameMs_;
}

float PerformanceGovernor::smoothedCpuMs() const noexcept {
    return smoothedCpuMs_;
}

float PerformanceGovernor::smoothedGpuMs() const noexcept {
    return smoothedGpuMs_;
}

float PerformanceGovernor::smoothedGpuPreWorldMs() const noexcept {
    return smoothedGpuPreWorldMs_;
}

float PerformanceGovernor::smoothedGpuWorldMs() const noexcept {
    return smoothedGpuWorldMs_;
}

float PerformanceGovernor::smoothedGpuCompositeUiMs() const noexcept {
    return smoothedGpuCompositeUiMs_;
}

PerformanceBottleneck
PerformanceGovernor::bottleneck() const noexcept {
    return bottleneck_;
}

GpuPassBottleneck
PerformanceGovernor::gpuPassBottleneck() const noexcept {
    return gpuPassBottleneck_;
}

void PerformanceGovernor::stepDown() noexcept {
    qualityIndex_ = std::max(0, qualityIndex_ - 1);
}

void PerformanceGovernor::stepUp() noexcept {
    qualityIndex_ = std::min(3, qualityIndex_ + 1);
}

void PerformanceGovernor::applyThermalCeiling(
    ThermalLevel thermal) noexcept {
    switch (thermal) {
        case ThermalLevel::Nominal:
        case ThermalLevel::Light:
            break;
        case ThermalLevel::Moderate:
            qualityIndex_ = std::min(qualityIndex_, 2);
            break;
        case ThermalLevel::Severe:
            qualityIndex_ = std::min(qualityIndex_, 1);
            break;
        case ThermalLevel::Critical:
            qualityIndex_ = 0;
            break;
    }
}

void PerformanceGovernor::classifyBottleneck(
    const PerformanceSample& sample,
    float targetMs) noexcept {
    PerformanceBottleneck candidate =
        PerformanceBottleneck::Balanced;

    if (sample.thermal == ThermalLevel::Severe ||
        sample.thermal == ThermalLevel::Critical) {
        candidate =
            PerformanceBottleneck::Thermal;
    } else {
        const bool cpuValid =
            smoothedCpuMs_ > 0.0f;
        const bool gpuValid =
            smoothedGpuMs_ > 0.0f;
        const bool intervalValid =
            smoothedIntervalMs_ > 0.0f;

        const bool cpuPressure =
            cpuValid &&
            smoothedCpuMs_ >
                targetMs * 0.92f;

        const bool gpuPressure =
            gpuValid &&
            smoothedGpuMs_ >
                targetMs * 0.92f;

        if (gpuPressure &&
            (!cpuPressure ||
             smoothedGpuMs_ >
                 smoothedCpuMs_ * 1.10f)) {
            candidate =
                PerformanceBottleneck::Gpu;
        } else if (
            cpuPressure &&
            (!gpuPressure ||
             smoothedCpuMs_ >
                 smoothedGpuMs_ * 1.10f)) {
            candidate =
                PerformanceBottleneck::Cpu;
        } else if (
            intervalValid &&
            smoothedIntervalMs_ >
                targetMs * 1.08f &&
            (!cpuValid ||
             smoothedCpuMs_ <
                 targetMs * 0.82f) &&
            (!gpuValid ||
             smoothedGpuMs_ <
                 targetMs * 0.82f)) {
            // The frame is late but neither measured CPU submission nor GPU
            // execution is saturated. Treat this as pacing/external bound so
            // the renderer does not destroy visual quality unnecessarily.
            candidate =
                PerformanceBottleneck::FramePaced;
        } else if (
            cpuPressure &&
            gpuPressure) {
            // Both sides are close enough that a single "winner" would be
            // unstable. Keep Balanced and let the quality governor respond to
            // sustained total frame cost.
            candidate =
                PerformanceBottleneck::Balanced;
        }
    }

    if (candidate ==
        pendingBottleneck_) {
        bottleneckHoldSeconds_ +=
            1.0f /
            std::max(
                config_.targetFps,
                1.0f);
    } else {
        pendingBottleneck_ =
            candidate;
        bottleneckHoldSeconds_ = 0.0f;
    }

    constexpr float kClassificationHoldSeconds =
        0.20f;

    if (candidate == PerformanceBottleneck::Thermal ||
        bottleneckHoldSeconds_ >=
            kClassificationHoldSeconds) {
        bottleneck_ =
            candidate;
    }
}

void PerformanceGovernor::classifyGpuPass(
    const PerformanceSample& sample,
    float targetMs) noexcept {
    GpuPassBottleneck candidate =
        GpuPassBottleneck::Balanced;

    const bool authoritative =
        sample.gpuPassTimingAuthoritative &&
        smoothedGpuMs_ > 0.0f &&
        smoothedGpuPreWorldMs_ >= 0.0f &&
        smoothedGpuWorldMs_ >= 0.0f &&
        smoothedGpuCompositeUiMs_ >= 0.0f;

    const bool gpuUnderPressure =
        smoothedGpuMs_ >
            targetMs * 0.92f;

    if (authoritative &&
        gpuUnderPressure) {
        const float preWorld =
            smoothedGpuPreWorldMs_;
        const float world =
            smoothedGpuWorldMs_;
        const float composite =
            smoothedGpuCompositeUiMs_;

        const float largest =
            std::max(
                preWorld,
                std::max(
                    world,
                    composite));

        const float secondLargest =
            preWorld == largest
            ? std::max(world, composite)
            : world == largest
              ? std::max(preWorld, composite)
              : std::max(preWorld, world);

        // Do not chase noise when two passes are effectively tied. A pass
        // must be at least 12% more expensive than the runner-up or consume
        // more than half of the measured GPU frame before it earns a
        // targeted-quality response.
        const bool dominant =
            largest >
                secondLargest * 1.12f ||
            largest >
                smoothedGpuMs_ * 0.50f;

        if (dominant) {
            if (largest == preWorld) {
                candidate =
                    GpuPassBottleneck::PreWorld;
            } else if (largest == world) {
                candidate =
                    GpuPassBottleneck::World;
            } else {
                candidate =
                    GpuPassBottleneck::CompositeUi;
            }
        }
    }

    if (candidate ==
        pendingGpuPassBottleneck_) {
        gpuPassHoldSeconds_ +=
            1.0f /
            std::max(
                config_.targetFps,
                1.0f);
    } else {
        pendingGpuPassBottleneck_ =
            candidate;
        gpuPassHoldSeconds_ = 0.0f;
    }

    constexpr float kGpuPassHoldSeconds =
        0.20f;

    if (!authoritative) {
        gpuPassBottleneck_ =
            GpuPassBottleneck::Balanced;
        pendingGpuPassBottleneck_ =
            GpuPassBottleneck::Balanced;
        gpuPassHoldSeconds_ = 0.0f;
    } else if (
        gpuPassHoldSeconds_ >=
            kGpuPassHoldSeconds) {
        gpuPassBottleneck_ =
            candidate;
    }
}

void PerformanceGovernor::rebuildWorkload() noexcept {
    switch (qualityIndex_) {
        case 0:
            workload_.quality = RenderQuality::Low;
            workload_.renderScale = 0.90f;
            workload_.particleDensityScale = 0.30f;
            workload_.shadowDistanceScale = 0.30f;
            workload_.fogQualityScale = 0.25f;
            workload_.dynamicLightBudget = 3;
            workload_.shadowedLightBudget = 1;
            workload_.shadowMapResolution = 512;

            workload_.maxPlanarReflectionPasses = 0;
            workload_.planarReflectionScale = 0.0f;
            workload_.reflectionDistanceMeters = 18.0f;
            workload_.ssrEnabled = false;
            workload_.ssrResolutionScale = 0.0f;
            workload_.ssrMaxSteps = 0;

            workload_.volumetricFogSteps = 6;
            workload_.postProcessScale = 0.50f;
            break;

        case 1:
            workload_.quality = RenderQuality::Medium;
            workload_.renderScale = 0.94f;
            workload_.particleDensityScale = 0.50f;
            workload_.shadowDistanceScale = 0.50f;
            workload_.fogQualityScale = 0.45f;
            workload_.dynamicLightBudget = 6;
            workload_.shadowedLightBudget = 1;
            workload_.shadowMapResolution = 768;

            workload_.maxPlanarReflectionPasses = 1;
            workload_.planarReflectionScale = 0.40f;
            workload_.reflectionDistanceMeters = 26.0f;
            workload_.ssrEnabled = false;
            workload_.ssrResolutionScale = 0.0f;
            workload_.ssrMaxSteps = 0;

            workload_.volumetricFogSteps = 10;
            workload_.postProcessScale = 0.60f;
            break;

        case 2:
            workload_.quality = RenderQuality::High;
            workload_.renderScale = 0.97f;
            workload_.particleDensityScale = 0.72f;
            workload_.shadowDistanceScale = 0.82f;
            workload_.fogQualityScale = 0.70f;
            workload_.dynamicLightBudget = 12;
            workload_.shadowedLightBudget = 3;
            workload_.shadowMapResolution = 1024;

            workload_.maxPlanarReflectionPasses = 1;
            workload_.planarReflectionScale = 0.60f;
            workload_.reflectionDistanceMeters = 35.0f;
            workload_.ssrEnabled = false;
            workload_.ssrResolutionScale = 0.0f;
            workload_.ssrMaxSteps = 0;

            workload_.volumetricFogSteps = 18;
            workload_.postProcessScale = 0.75f;
            break;

        default:
            workload_.quality = RenderQuality::Ultra;
            workload_.renderScale = 1.0f;
            workload_.particleDensityScale = 1.0f;
            workload_.shadowDistanceScale = 1.0f;
            workload_.fogQualityScale = 1.0f;
            workload_.dynamicLightBudget = 24;
            workload_.shadowedLightBudget = 6;
            workload_.shadowMapResolution = 1536;

            workload_.maxPlanarReflectionPasses = 2;
            workload_.planarReflectionScale = 0.75f;
            workload_.reflectionDistanceMeters = 48.0f;
            workload_.ssrEnabled = true;
            workload_.ssrResolutionScale = 0.67f;
            workload_.ssrMaxSteps = 40;

            workload_.volumetricFogSteps = 32;
            workload_.postProcessScale = 1.0f;
            break;
    }

    if (bottleneck_ !=
        PerformanceBottleneck::Gpu) {
        return;
    }

    switch (gpuPassBottleneck_) {
        case GpuPassBottleneck::PreWorld:
            workload_.maxPlanarReflectionPasses =
                std::min<std::uint32_t>(
                    workload_.maxPlanarReflectionPasses,
                    1U);
            workload_.planarReflectionScale *=
                0.72f;
            workload_.reflectionDistanceMeters *=
                0.80f;
            break;

        case GpuPassBottleneck::World:
            workload_.shadowDistanceScale *=
                0.82f;
            workload_.fogQualityScale *=
                0.88f;
            workload_.particleDensityScale *=
                0.90f;
            workload_.dynamicLightBudget =
                std::max<std::uint32_t>(
                    4U,
                    (workload_.dynamicLightBudget * 3U) /
                        4U);
            workload_.shadowedLightBudget =
                std::max<std::uint32_t>(
                    1U,
                    workload_.shadowedLightBudget > 1U
                    ? workload_.shadowedLightBudget - 1U
                    : 1U);
            break;

        case GpuPassBottleneck::CompositeUi:
            workload_.renderScale =
                std::max(
                    0.60f,
                    workload_.renderScale *
                        0.90f);
            workload_.postProcessScale =
                std::max(
                    0.45f,
                    workload_.postProcessScale *
                        0.82f);
            break;

        case GpuPassBottleneck::Balanced:
            break;
    }
}

} // namespace xziel
