#include "xziel/environment.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

EnvironmentSystem::EnvironmentSystem(
    WeatherConfig config,
    RenderQuality quality)
    : config_(config),
      quality_(quality) {}

void EnvironmentSystem::reset() noexcept {
    wetness_ = 0.0f;
    stormClockSeconds_ = 0.0f;
}

void EnvironmentSystem::setWeather(WeatherConfig config) noexcept {
    config_ = config;
}

void EnvironmentSystem::setQuality(RenderQuality quality) noexcept {
    quality_ = quality;
}

EnvironmentFrame EnvironmentSystem::advance(float deltaSeconds) noexcept {
    const float dt = std::clamp(deltaSeconds, 0.0f, 0.1f);
    const float rain = std::clamp(config_.rainIntensity, 0.0f, 1.0f);

    if (rain > 0.001f) {
        wetness_ += config_.wetnessRisePerSecond * rain * dt;
    } else {
        wetness_ -= config_.wetnessDryPerSecond * dt;
    }
    wetness_ = std::clamp(wetness_, 0.0f, 1.0f);

    float lightningFlash = 0.0f;
    if (config_.lightningIntervalSeconds > 0.01f &&
        config_.lightningDurationSeconds > 0.001f &&
        config_.lightningIntensity > 0.0f) {
        stormClockSeconds_ += dt;
        const float phase = std::fmod(
            stormClockSeconds_,
            config_.lightningIntervalSeconds);
        if (phase < config_.lightningDurationSeconds) {
            const float t = phase / config_.lightningDurationSeconds;
            const float envelope = 1.0f - std::clamp(t, 0.0f, 1.0f);
            lightningFlash =
                config_.lightningIntensity * envelope * envelope;
        }
    } else {
        stormClockSeconds_ = 0.0f;
    }

    EnvironmentFrame frame{};
    frame.wetness = wetness_;
    frame.lightningFlash = lightningFlash;
    frame.rainIntensity = rain;
    frame.fogDensity = std::max(config_.fogDensity, 0.0f);
    frame.windMetersPerSecond = config_.windMetersPerSecond;

    frame.rainParticleBudget =
        static_cast<std::uint32_t>(
            static_cast<float>(rainBudget()) * rain);
    frame.splashParticleBudget =
        config_.splashParticles
            ? static_cast<std::uint32_t>(
                  static_cast<float>(splashBudget()) * rain)
            : 0U;

    frame.requirePrecipitationOcclusion =
        config_.precipitationOcclusion && rain > 0.001f;
    frame.wetSurfaceResponse =
        config_.wetSurfaceResponse && wetness_ > 0.001f;

    return frame;
}

const WeatherConfig& EnvironmentSystem::weather() const noexcept {
    return config_;
}

RenderQuality EnvironmentSystem::quality() const noexcept {
    return quality_;
}

std::uint32_t EnvironmentSystem::rainBudget() const noexcept {
    switch (quality_) {
        case RenderQuality::Low: return 384;
        case RenderQuality::Medium: return 768;
        case RenderQuality::High: return 1536;
        case RenderQuality::Ultra: return 3072;
    }
    return 768;
}

std::uint32_t EnvironmentSystem::splashBudget() const noexcept {
    switch (quality_) {
        case RenderQuality::Low: return 48;
        case RenderQuality::Medium: return 128;
        case RenderQuality::High: return 256;
        case RenderQuality::Ultra: return 512;
    }
    return 128;
}

} // namespace xziel
