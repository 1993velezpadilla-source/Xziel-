#pragma once

#include "xziel/environment.hpp"

#include <cstdint>

namespace xziel {

enum class ThermalLevel : std::uint8_t {
    Nominal,
    Light,
    Moderate,
    Severe,
    Critical,
};

struct PerformanceConfig {
    float targetFps = 60.0f;
    float degradeThreshold = 1.08f;
    float recoverThreshold = 0.82f;
    float smoothing = 0.08f;

    float degradeHoldSeconds = 0.75f;
    float recoverHoldSeconds = 4.0f;
};

struct PerformanceSample {
    float cpuFrameMs = 0.0f;
    float gpuFrameMs = 0.0f;
    ThermalLevel thermal = ThermalLevel::Nominal;
};

struct RenderWorkload {
    RenderQuality quality = RenderQuality::High;

    float renderScale = 1.0f;
    float particleDensityScale = 1.0f;
    float shadowDistanceScale = 1.0f;
    float fogQualityScale = 1.0f;

    std::uint32_t dynamicLightBudget = 16;
    std::uint32_t shadowedLightBudget = 4;
    std::uint32_t shadowMapResolution = 1024;

    // Reflection budgets are explicit so mirrors/water cannot accidentally
    // multiply the full scene cost without bounds.
    std::uint32_t maxPlanarReflectionPasses = 1;
    float planarReflectionScale = 0.60f;
    float reflectionDistanceMeters = 35.0f;

    bool ssrEnabled = true;
    float ssrResolutionScale = 0.50f;
    std::uint32_t ssrMaxSteps = 24;

    // Volumetric/post effects are budgeted independently of gameplay.
    std::uint32_t volumetricFogSteps = 24;
    float postProcessScale = 0.75f;
};

class PerformanceGovernor final {
public:
    explicit PerformanceGovernor(PerformanceConfig config = {});

    void reset() noexcept;
    [[nodiscard]] RenderWorkload advance(
        const PerformanceSample& sample,
        float deltaSeconds) noexcept;

    [[nodiscard]] const RenderWorkload& workload() const noexcept;
    [[nodiscard]] float smoothedFrameMs() const noexcept;

private:
    void stepDown() noexcept;
    void stepUp() noexcept;
    void applyThermalCeiling(ThermalLevel thermal) noexcept;
    void rebuildWorkload() noexcept;

    PerformanceConfig config_{};
    RenderWorkload workload_{};

    int qualityIndex_ = 2;
    float smoothedFrameMs_ = 0.0f;
    float overloadSeconds_ = 0.0f;
    float recoverySeconds_ = 0.0f;
};

} // namespace xziel
