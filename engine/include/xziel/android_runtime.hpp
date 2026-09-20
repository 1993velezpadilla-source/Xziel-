#pragma once

#include <cstdint>

namespace xziel {

enum class AndroidLifecycleEvent : std::uint8_t {
    Create,
    Start,
    Resume,
    Pause,
    Stop,
    Destroy,
    SurfaceCreated,
    SurfaceDestroyed,
    FocusGained,
    FocusLost,
    LowMemory,
};

struct AndroidRuntimeInput {
    bool cpuHeadroomValid = false;
    bool gpuHeadroomValid = false;

    // Normalized 0..1 where larger means more spare capacity.
    float cpuHeadroom = 1.0f;
    float gpuHeadroom = 1.0f;

    float thermalHeadroom = 1.0f;
    float displayRefreshHz = 60.0f;
};

struct AndroidRuntimeState {
    bool created = false;
    bool started = false;
    bool resumed = false;
    bool focused = false;
    bool surfaceAvailable = false;

    bool canSimulate = false;
    bool canRender = false;
    bool shouldThrottleBackground = false;
    bool requestRendererRecreate = false;
    bool requestMemoryTrim = false;
    bool exiting = false;

    float smoothedCpuHeadroom = 1.0f;
    float smoothedGpuHeadroom = 1.0f;
    float smoothedThermalHeadroom = 1.0f;
    float displayRefreshHz = 60.0f;

    std::uint64_t generation = 0;
};

class AndroidRuntimeStateMachine final {
public:
    AndroidRuntimeStateMachine();

    void reset() noexcept;

    [[nodiscard]] AndroidRuntimeState onEvent(
        AndroidLifecycleEvent event) noexcept;

    [[nodiscard]] AndroidRuntimeState updateTelemetry(
        const AndroidRuntimeInput& input,
        float deltaSeconds) noexcept;

    [[nodiscard]] const AndroidRuntimeState& state() const noexcept;

private:
    void recomputeDerivedState() noexcept;
    [[nodiscard]] static float smoothToward(
        float current,
        float target,
        float deltaSeconds) noexcept;

    AndroidRuntimeState state_{};
};

} // namespace xziel
