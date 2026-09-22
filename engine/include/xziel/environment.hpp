#pragma once

#include "xziel/engine.hpp"

#include <cstdint>

namespace xziel {

enum class LightType : std::uint8_t {
    Directional,
    Point,
    Spot,
};

enum class RenderQuality : std::uint8_t {
    Low,
    Medium,
    High,
    Ultra,
};

struct LightDesc {
    LightType type = LightType::Point;
    Vec3 position{};
    Vec3 direction{0.0f, -1.0f, 0.0f};
    Vec3 colorLinear{1.0f, 1.0f, 1.0f};

    float intensity = 1.0f;
    float rangeMeters = 10.0f;
    float innerConeDegrees = 25.0f;
    float outerConeDegrees = 40.0f;

    bool castsShadows = false;
    bool volumetric = false;
};

struct WeatherConfig {
    float rainIntensity = 0.0f;
    Vec3 windMetersPerSecond{};

    float wetnessRisePerSecond = 0.24f;
    float wetnessDryPerSecond = 0.035f;

    // A deterministic periodic lightning pulse keeps gameplay tests stable.
    // The renderer may later substitute authored/randomized storms while
    // preserving a deterministic gameplay timeline.
    float lightningIntervalSeconds = 0.0f;
    float lightningDurationSeconds = 0.16f;
    float lightningIntensity = 0.0f;

    float fogDensity = 0.0f;
    float fogHeightFalloff = 0.0f;

    bool precipitationOcclusion = true;
    bool splashParticles = true;
    bool wetSurfaceResponse = true;
};

struct EnvironmentFrame {
    float wetness = 0.0f;
    float lightningFlash = 0.0f;
    float rainIntensity = 0.0f;
    float fogDensity = 0.0f;

    Vec3 windMetersPerSecond{};

    std::uint32_t rainParticleBudget = 0;
    std::uint32_t splashParticleBudget = 0;

    bool requirePrecipitationOcclusion = false;
    bool wetSurfaceResponse = false;
};

class EnvironmentSystem final {
public:
    EnvironmentSystem(
        WeatherConfig config = {},
        RenderQuality quality = RenderQuality::High);

    void reset() noexcept;
    void setWeather(WeatherConfig config) noexcept;
    void setQuality(RenderQuality quality) noexcept;

    [[nodiscard]] EnvironmentFrame advance(float deltaSeconds) noexcept;

    [[nodiscard]] const WeatherConfig& weather() const noexcept;
    [[nodiscard]] RenderQuality quality() const noexcept;

private:
    [[nodiscard]] std::uint32_t rainBudget() const noexcept;
    [[nodiscard]] std::uint32_t splashBudget() const noexcept;

    WeatherConfig config_{};
    RenderQuality quality_ = RenderQuality::High;

    float wetness_ = 0.0f;
    float stormClockSeconds_ = 0.0f;
};

} // namespace xziel
