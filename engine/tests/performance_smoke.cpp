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
    assert(workload.renderScale >= 0.90f);
    assert(workload.renderScale < 0.96f);
    assert(workload.particleDensityScale < 0.72f);
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
    assert(workload.renderScale <= 0.78f + 0.0001f);
    assert(workload.dynamicLightBudget == 3);
    assert(workload.shadowedLightBudget == 1);
    assert(workload.maxPlanarReflectionPasses == 0);
    assert(!workload.ssrEnabled);
    assert(workload.volumetricFogSteps == 6);

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

    governor.reset();

    // A GPU-bound frame dominated by the world pass should preserve the
    // current quality tier/render scale while trimming world-specific cost.
    for (int i = 0; i < 20; ++i) {
        workload = governor.advance(
            {
                .cpuFrameMs = 5.0f,
                .gpuFrameMs = 17.0f,
                .gpuPreWorldMs = 1.0f,
                .gpuWorldMs = 13.0f,
                .gpuCompositeUiMs = 3.0f,
                .frameIntervalMs = 17.0f,
                .gpuPassTimingAuthoritative = true,
            },
            1.0f / 60.0f);
    }

    assert(
        governor.bottleneck() ==
        xziel::PerformanceBottleneck::Gpu);
    assert(
        governor.gpuPassBottleneck() ==
        xziel::GpuPassBottleneck::World);
    assert(
        workload.quality ==
        xziel::RenderQuality::High);
    assert(workload.renderScale > 0.91f);
    assert(workload.shadowDistanceScale < 0.82f);
    assert(workload.dynamicLightBudget < 16U);

    governor.reset();

    // Composite/UI pressure should first reduce scene/post resolution, not
    // shadows or reflection quality.
    for (int i = 0; i < 20; ++i) {
        workload = governor.advance(
            {
                .cpuFrameMs = 5.0f,
                .gpuFrameMs = 17.0f,
                .gpuPreWorldMs = 1.0f,
                .gpuWorldMs = 3.0f,
                .gpuCompositeUiMs = 13.0f,
                .frameIntervalMs = 17.0f,
                .gpuPassTimingAuthoritative = true,
            },
            1.0f / 60.0f);
    }

    assert(
        governor.gpuPassBottleneck() ==
        xziel::GpuPassBottleneck::CompositeUi);
    assert(workload.renderScale >= 0.90f);
    assert(workload.renderScale < 0.96f);
    assert(workload.postProcessScale < 0.75f);
    assert(workload.shadowDistanceScale > 0.81f);

    governor.reset();

    // Reflection/pre-world pressure trims planar reflection cost while
    // preserving the scene render scale.
    for (int i = 0; i < 20; ++i) {
        workload = governor.advance(
            {
                .cpuFrameMs = 5.0f,
                .gpuFrameMs = 17.0f,
                .gpuPreWorldMs = 13.0f,
                .gpuWorldMs = 3.0f,
                .gpuCompositeUiMs = 1.0f,
                .frameIntervalMs = 17.0f,
                .gpuPassTimingAuthoritative = true,
            },
            1.0f / 60.0f);
    }

    assert(
        governor.gpuPassBottleneck() ==
        xziel::GpuPassBottleneck::PreWorld);
    assert(workload.renderScale > 0.91f);
    assert(workload.planarReflectionScale < 0.60f);
    assert(workload.reflectionDistanceMeters < 35.0f);

    governor.reset();

    // Pass values from software/CPU Vulkan are telemetry only. They must not
    // trigger targeted quality changes.
    for (int i = 0; i < 20; ++i) {
        workload = governor.advance(
            {
                .cpuFrameMs = 5.0f,
                .gpuFrameMs = 17.0f,
                .gpuPreWorldMs = 15.0f,
                .gpuWorldMs = 1.0f,
                .gpuCompositeUiMs = 1.0f,
                .frameIntervalMs = 17.0f,
                .gpuPassTimingAuthoritative = false,
            },
            1.0f / 60.0f);
    }

    assert(
        governor.bottleneck() ==
        xziel::PerformanceBottleneck::Gpu);
    assert(
        governor.gpuPassBottleneck() ==
        xziel::GpuPassBottleneck::Balanced);
    assert(workload.renderScale > 0.91f);
    assert(workload.planarReflectionScale > 0.59f);
    assert(workload.shadowDistanceScale > 0.81f);

    return 0;
}
