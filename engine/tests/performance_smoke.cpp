#include "xziel/performance.hpp"

#include <cassert>

int main() {
    xziel::PerformanceConfig config{};
    config.targetFps = 60.0f;
    config.degradeHoldSeconds = 0.20f;
    config.recoverHoldSeconds = 0.50f;
    config.smoothing = 1.0f;

    xziel::PerformanceGovernor governor(config);

    // Sustained overload steps quality down.
    xziel::RenderWorkload workload{};
    for (int i = 0; i < 30; ++i) {
        workload = governor.advance(
            {.cpuFrameMs = 24.0f, .gpuFrameMs = 27.0f},
            1.0f / 60.0f);
    }
    assert(workload.renderScale < 0.92f);
    assert(workload.particleDensityScale < 0.82f);
    assert(workload.maxPlanarReflectionPasses <= 1);
    assert(workload.ssrMaxSteps <= 24);

    // Critical thermal state immediately enforces the low ceiling and turns
    // off the expensive reflection paths before touching gameplay.
    workload = governor.advance(
        {
            .cpuFrameMs = 12.0f,
            .gpuFrameMs = 12.0f,
            .thermal = xziel::ThermalLevel::Critical,
        },
        1.0f / 60.0f);
    assert(workload.quality == xziel::RenderQuality::Low);
    assert(workload.dynamicLightBudget == 4);
    assert(workload.shadowedLightBudget == 1);
    assert(workload.maxPlanarReflectionPasses == 0);
    assert(!workload.ssrEnabled);
    assert(workload.volumetricFogSteps == 8);

    governor.reset();

    // Fast frames sustained for long enough can recover upward.
    for (int i = 0; i < 240; ++i) {
        workload = governor.advance(
            {.cpuFrameMs = 5.0f, .gpuFrameMs = 6.0f},
            1.0f / 60.0f);
    }
    assert(workload.quality == xziel::RenderQuality::Ultra);
    assert(workload.maxPlanarReflectionPasses == 2);
    assert(workload.ssrEnabled);
    assert(workload.ssrMaxSteps == 40);

    governor.reset();

    // GPU-bound classification is stable only after a short hold window.
    for (int i = 0; i < 20; ++i) {
        (void) governor.advance(
            {
                .cpuFrameMs = 5.0f,
                .gpuFrameMs = 17.0f,
                .frameIntervalMs = 17.0f,
            },
            1.0f / 60.0f);
    }
    assert(
        governor.bottleneck() ==
        xziel::PerformanceBottleneck::Gpu);

    governor.reset();

    for (int i = 0; i < 20; ++i) {
        (void) governor.advance(
            {
                .cpuFrameMs = 17.0f,
                .gpuFrameMs = 5.0f,
                .frameIntervalMs = 17.0f,
            },
            1.0f / 60.0f);
    }
    assert(
        governor.bottleneck() ==
        xziel::PerformanceBottleneck::Cpu);

    governor.reset();

    for (int i = 0; i < 20; ++i) {
        (void) governor.advance(
            {
                .cpuFrameMs = 4.0f,
                .gpuFrameMs = 4.0f,
                .frameIntervalMs = 22.0f,
            },
            1.0f / 60.0f);
    }
    assert(
        governor.bottleneck() ==
        xziel::PerformanceBottleneck::FramePaced);

    return 0;
}
