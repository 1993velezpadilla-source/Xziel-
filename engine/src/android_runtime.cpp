#include "xziel/android_runtime.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float normalized(float value) noexcept {
    if (!std::isfinite(value)) {
        return 1.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

} // namespace

AndroidRuntimeStateMachine::AndroidRuntimeStateMachine() {
    reset();
}

void AndroidRuntimeStateMachine::reset() noexcept {
    state_ = {};
    state_.smoothedCpuHeadroom = 1.0f;
    state_.smoothedGpuHeadroom = 1.0f;
    state_.smoothedThermalHeadroom = 1.0f;
    state_.displayRefreshHz = 60.0f;
}

AndroidRuntimeState AndroidRuntimeStateMachine::onEvent(
    AndroidLifecycleEvent event) noexcept {
    state_.requestRendererRecreate = false;
    state_.requestMemoryTrim = false;

    switch (event) {
        case AndroidLifecycleEvent::Create:
            state_.created = true;
            state_.exiting = false;
            ++state_.generation;
            break;

        case AndroidLifecycleEvent::Start:
            state_.started = true;
            break;

        case AndroidLifecycleEvent::Resume:
            state_.resumed = true;
            break;

        case AndroidLifecycleEvent::Pause:
            state_.resumed = false;
            break;

        case AndroidLifecycleEvent::Stop:
            state_.started = false;
            state_.resumed = false;
            break;

        case AndroidLifecycleEvent::Destroy:
            state_.created = false;
            state_.started = false;
            state_.resumed = false;
            state_.focused = false;
            state_.surfaceAvailable = false;
            state_.exiting = true;
            ++state_.generation;
            break;

        case AndroidLifecycleEvent::SurfaceCreated:
            if (!state_.surfaceAvailable) {
                state_.surfaceAvailable = true;
                state_.requestRendererRecreate = true;
                ++state_.generation;
            }
            break;

        case AndroidLifecycleEvent::SurfaceDestroyed:
            if (state_.surfaceAvailable) {
                state_.surfaceAvailable = false;
                ++state_.generation;
            }
            break;

        case AndroidLifecycleEvent::FocusGained:
            state_.focused = true;
            break;

        case AndroidLifecycleEvent::FocusLost:
            state_.focused = false;
            break;

        case AndroidLifecycleEvent::LowMemory:
            state_.requestMemoryTrim = true;
            break;
    }

    recomputeDerivedState();
    return state_;
}

AndroidRuntimeState AndroidRuntimeStateMachine::updateTelemetry(
    const AndroidRuntimeInput& input,
    float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) || deltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(deltaSeconds, 1.0f);

    if (input.cpuHeadroomValid) {
        state_.smoothedCpuHeadroom = smoothToward(
            state_.smoothedCpuHeadroom,
            normalized(input.cpuHeadroom),
            dt);
    }

    if (input.gpuHeadroomValid) {
        state_.smoothedGpuHeadroom = smoothToward(
            state_.smoothedGpuHeadroom,
            normalized(input.gpuHeadroom),
            dt);
    }

    state_.smoothedThermalHeadroom = smoothToward(
        state_.smoothedThermalHeadroom,
        normalized(input.thermalHeadroom),
        dt);

    if (std::isfinite(input.displayRefreshHz) &&
        input.displayRefreshHz >= 30.0f) {
        state_.displayRefreshHz =
            std::clamp(input.displayRefreshHz, 30.0f, 240.0f);
    }

    return state_;
}

const AndroidRuntimeState&
AndroidRuntimeStateMachine::state() const noexcept {
    return state_;
}

void AndroidRuntimeStateMachine::recomputeDerivedState() noexcept {
    state_.canSimulate =
        state_.created &&
        state_.started &&
        state_.resumed &&
        !state_.exiting;

    state_.canRender =
        state_.canSimulate &&
        state_.surfaceAvailable;

    state_.shouldThrottleBackground =
        !state_.resumed ||
        !state_.focused ||
        !state_.surfaceAvailable;
}

float AndroidRuntimeStateMachine::smoothToward(
    float current,
    float target,
    float deltaSeconds) noexcept {
    // ~2 second time constant. Android headroom guidance warns against
    // over-reacting to each individual sample.
    const float alpha =
        1.0f - std::exp(-deltaSeconds / 2.0f);
    return current + (target - current) * alpha;
}

} // namespace xziel
