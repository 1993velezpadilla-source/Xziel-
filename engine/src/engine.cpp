#include "xziel/engine.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

EngineConfig sanitizeConfig(EngineConfig config) noexcept {
    if (!std::isfinite(config.fixedTickHz) || config.fixedTickHz < 30.0) {
        config.fixedTickHz = 120.0;
    }
    if (!std::isfinite(config.maxFrameDeltaSeconds) ||
        config.maxFrameDeltaSeconds <= 0.0) {
        config.maxFrameDeltaSeconds = 0.100;
    }
    if (config.maxCatchUpTicks == 0) {
        config.maxCatchUpTicks = 1;
    }
    return config;
}

double sanitizeDelta(double dt, double maxDt) noexcept {
    if (!std::isfinite(dt) || dt <= 0.0) {
        return 0.0;
    }
    return std::min(dt, maxDt);
}

} // namespace

Engine::Engine(EngineConfig config)
    : config_(sanitizeConfig(config)) {}

void Engine::reset() noexcept {
    input_ = {};
    accumulatorSeconds_ = 0.0;
    frameIndex_ = 0;
    simulationTick_ = 0;
}

void Engine::submitInput(const InputState& input) noexcept {
    input_ = input;
}

FrameStats Engine::advance(double frameDeltaSeconds) noexcept {
    const double fixedDt = 1.0 / config_.fixedTickHz;
    const double clampedDt =
        sanitizeDelta(frameDeltaSeconds, config_.maxFrameDeltaSeconds);

    accumulatorSeconds_ += clampedDt;

    std::uint32_t ticks = 0;
    while (accumulatorSeconds_ + 1.0e-12 >= fixedDt &&
           ticks < config_.maxCatchUpTicks) {
        fixedTick();
        accumulatorSeconds_ -= fixedDt;
        ++ticks;
    }

    // Avoid a permanent spiral-of-death if a phone resumes after a stall.
    if (ticks == config_.maxCatchUpTicks && accumulatorSeconds_ >= fixedDt) {
        accumulatorSeconds_ = std::fmod(accumulatorSeconds_, fixedDt);
    }

    FrameStats stats{};
    stats.frameIndex = frameIndex_++;
    stats.simulationTick = simulationTick_;
    stats.ticksThisFrame = ticks;
    stats.rawFrameDeltaSeconds = frameDeltaSeconds;
    stats.clampedFrameDeltaSeconds = clampedDt;
    stats.interpolationAlpha =
        fixedDt > 0.0 ? std::clamp(accumulatorSeconds_ / fixedDt, 0.0, 1.0)
                      : 0.0;
    return stats;
}

const InputState& Engine::input() const noexcept {
    return input_;
}

std::uint64_t Engine::simulationTick() const noexcept {
    return simulationTick_;
}

const EngineConfig& Engine::config() const noexcept {
    return config_;
}

void Engine::fixedTick() noexcept {
    // Phase 0 intentionally owns only timing and input sampling.
    // Player movement, weapon state, AI, physics and networking are added in
    // subsequent clean-room modules with tests for deterministic behavior.
    ++simulationTick_;
}

} // namespace xziel
