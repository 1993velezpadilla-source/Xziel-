#include "xziel/android_runtime.hpp"

#include <cassert>

int main() {
    xziel::AndroidRuntimeStateMachine runtime;

    auto state = runtime.onEvent(
        xziel::AndroidLifecycleEvent::Create);
    assert(state.created);
    assert(!state.canRender);

    runtime.onEvent(xziel::AndroidLifecycleEvent::Start);
    runtime.onEvent(xziel::AndroidLifecycleEvent::Resume);
    runtime.onEvent(xziel::AndroidLifecycleEvent::FocusGained);

    state = runtime.onEvent(
        xziel::AndroidLifecycleEvent::SurfaceCreated);

    assert(state.canSimulate);
    assert(state.canRender);
    assert(state.requestRendererRecreate);

    const float before =
        state.smoothedGpuHeadroom;

    for (int i = 0; i < 60; ++i) {
        state = runtime.updateTelemetry(
            {
                .cpuHeadroomValid = true,
                .gpuHeadroomValid = true,
                .cpuHeadroom = 0.45f,
                .gpuHeadroom = 0.25f,
                .thermalHeadroom = 0.35f,
                .displayRefreshHz = 120.0f,
            },
            1.0f / 60.0f);
    }

    assert(state.smoothedGpuHeadroom < before);
    assert(state.smoothedGpuHeadroom > 0.25f);
    assert(state.displayRefreshHz == 120.0f);

    state = runtime.onEvent(
        xziel::AndroidLifecycleEvent::Pause);
    assert(!state.canSimulate);
    assert(!state.canRender);
    assert(state.shouldThrottleBackground);

    state = runtime.onEvent(
        xziel::AndroidLifecycleEvent::LowMemory);
    assert(state.requestMemoryTrim);

    return 0;
}
