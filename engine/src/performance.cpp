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
    overloadSeconds_ = 0.0f;
    recoverySeconds_ = 0.0f;
    rebuildWorkload();
}

RenderWorkload PerformanceGovernor::advance(
    const PerformanceSample& sample,
    float deltaSeconds) noexcept {
    const float dt = std::clamp(deltaSeconds, 0.0f, 0.25f);
    const float frameMs = std::max(sample.cpuFrameMs, sample.gpuFrameMs);

    if (std::isfinite(frameMs) && frameMs > 0.0f) {
        if (smoothedFrameMs_ <= 0.0f) {
            smoothedFrameMs_ = frameMs;
        } else {
            const float alpha = std::clamp(config_.smoothing, 0.001f, 1.0f);
            smoothedFrameMs_ += (frameMs - smoothedFrameMs_) * alpha;
        }
    }

    const float targetMs =
        1000.0f / std::max(config_.targetFps, 1.0f);
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
    return workload_;
}

const RenderWorkload& PerformanceGovernor::workload() const noexcept {
    return workload_;
}

float PerformanceGovernor::smoothedFrameMs() const noexcept {
    return smoothedFrameMs_;
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

void PerformanceGovernor::rebuildWorkload() noexcept {
    switch (qualityIndex_) {
        case 0:
            workload_.quality = RenderQuality::Low;
            workload_.renderScale = 0.70f;
            workload_.particleDensityScale = 0.42f;
            workload_.shadowDistanceScale = 0.40f;
            workload_.fogQualityScale = 0.35f;
            workload_.dynamicLightBudget = 4;
            workload_.shadowedLightBudget = 1;
            workload_.shadowMapResolution = 512;

            workload_.maxPlanarReflectionPasses = 0;
            workload_.planarReflectionScale = 0.0f;
            workload_.reflectionDistanceMeters = 18.0f;
            workload_.ssrEnabled = false;
            workload_.ssrResolutionScale = 0.0f;
            workload_.ssrMaxSteps = 0;

            workload_.volumetricFogSteps = 8;
            workload_.postProcessScale = 0.50f;
            break;

        case 1:
            workload_.quality = RenderQuality::Medium;
            workload_.renderScale = 0.82f;
            workload_.particleDensityScale = 0.62f;
            workload_.shadowDistanceScale = 0.62f;
            workload_.fogQualityScale = 0.58f;
            workload_.dynamicLightBudget = 8;
            workload_.shadowedLightBudget = 2;
            workload_.shadowMapResolution = 768;

            workload_.maxPlanarReflectionPasses = 1;
            workload_.planarReflectionScale = 0.40f;
            workload_.reflectionDistanceMeters = 26.0f;
            workload_.ssrEnabled = false;
            workload_.ssrResolutionScale = 0.0f;
            workload_.ssrMaxSteps = 0;

            workload_.volumetricFogSteps = 12;
            workload_.postProcessScale = 0.60f;
            break;

        case 2:
            workload_.quality = RenderQuality::High;
            workload_.renderScale = 0.92f;
            workload_.particleDensityScale = 0.82f;
            workload_.shadowDistanceScale = 0.82f;
            workload_.fogQualityScale = 0.82f;
            workload_.dynamicLightBudget = 16;
            workload_.shadowedLightBudget = 4;
            workload_.shadowMapResolution = 1024;

            workload_.maxPlanarReflectionPasses = 1;
            workload_.planarReflectionScale = 0.60f;
            workload_.reflectionDistanceMeters = 35.0f;
            workload_.ssrEnabled = true;
            workload_.ssrResolutionScale = 0.50f;
            workload_.ssrMaxSteps = 24;

            workload_.volumetricFogSteps = 24;
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
}

} // namespace xziel
