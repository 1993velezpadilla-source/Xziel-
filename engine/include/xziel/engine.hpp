#pragma once

#include <cstdint>

namespace xziel {

struct Vec2 {
    float x = 0.0f;
    float y = 0.0f;
};

struct Vec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

struct InputState {
    Vec2 move{};
    Vec2 look{};
    Vec3 gyroRadiansPerSecond{};

    bool fire = false;
    bool aim = false;
    bool sprint = false;
    bool crouch = false;
    bool jump = false;
    bool interact = false;
    bool reload = false;
};

struct EngineConfig {
    double fixedTickHz = 120.0;
    double maxFrameDeltaSeconds = 0.100;
    std::uint32_t maxCatchUpTicks = 8;
};

struct FrameStats {
    std::uint64_t frameIndex = 0;
    std::uint64_t simulationTick = 0;
    std::uint32_t ticksThisFrame = 0;
    double rawFrameDeltaSeconds = 0.0;
    double clampedFrameDeltaSeconds = 0.0;
    double interpolationAlpha = 0.0;
};

class Engine final {
public:
    explicit Engine(EngineConfig config = {});

    void reset() noexcept;

    // Input is sampled once per rendered frame, then consumed by the fixed-rate
    // simulation ticks for that frame. Platform-specific input adapters live
    // outside this clean-room core.
    void submitInput(const InputState& input) noexcept;

    // Advances the deterministic fixed-timestep clock. Rendering, Android
    // lifecycle, audio, physics and networking will be added as independent
    // services rather than being inherited from the legacy Quake runtime.
    [[nodiscard]] FrameStats advance(double frameDeltaSeconds) noexcept;

    [[nodiscard]] const InputState& input() const noexcept;
    [[nodiscard]] std::uint64_t simulationTick() const noexcept;
    [[nodiscard]] const EngineConfig& config() const noexcept;

private:
    void fixedTick() noexcept;

    EngineConfig config_{};
    InputState input_{};
    double accumulatorSeconds_ = 0.0;
    std::uint64_t frameIndex_ = 0;
    std::uint64_t simulationTick_ = 0;
};

} // namespace xziel
