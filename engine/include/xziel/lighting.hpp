#pragma once

#include "xziel/environment.hpp"
#include "xziel/horror.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

inline constexpr std::size_t kMaxRuntimeLocalLights = 8U;

enum class HorrorLightingMood : std::uint8_t {
    Neutral,
    Sanctum,
    Catacomb,
    Emergency,
    MoonlitExterior,
};

struct LocalLightInput {
    std::uint32_t id = 0U;
    LightType type = LightType::Point;
    Vec3 position{};
    Vec3 direction{0.0f, -1.0f, 0.0f};
    Vec3 colorLinear{1.0f, 1.0f, 1.0f};

    float intensity = 1.0f;
    float rangeMeters = 8.0f;
    float innerConeDegrees = 24.0f;
    float outerConeDegrees = 42.0f;
    float importance = 1.0f;

    float flickerAmount = 0.0f;
    float flickerHz = 0.0f;

    bool castsShadows = false;
    bool volumetric = false;
    bool enabled = false;
};

struct RuntimeLocalLight {
    std::uint32_t id = 0U;
    LightType type = LightType::Point;
    Vec3 position{};
    Vec3 direction{0.0f, -1.0f, 0.0f};
    Vec3 colorLinear{1.0f, 1.0f, 1.0f};

    float intensity = 0.0f;
    float rangeMeters = 0.0f;
    float innerConeCos = 1.0f;
    float outerConeCos = 1.0f;

    bool castsShadows = false;
    bool volumetric = false;
};

struct HorrorLightingConfig {
    HorrorLightingMood mood = HorrorLightingMood::Sanctum;

    Vec3 keyDirection{-0.34f, 0.82f, -0.46f};
    Vec3 keyColorLinear{1.0f, 0.62f, 0.34f};
    float keyIntensity = 0.82f;

    Vec3 ambientColorLinear{0.10f, 0.15f, 0.23f};
    float ambientIntensity = 0.22f;

    Vec3 fogColorLinear{0.028f, 0.043f, 0.062f};
    float baseFogDensity = 0.055f;
    float fogHeightFalloff = 0.11f;
    float fogTensionBoost = 0.10f;

    // Exposure is expressed in photographic stops. A -1 EV bias halves
    // scene brightness. The renderer consumes the precomputed linear scale.
    float baseExposureEv = -0.35f;
    float tensionExposureDropEv = 0.24f;

    float contrast = 1.08f;
    float saturation = 0.88f;
    float tensionDesaturation = 0.08f;

    // Protect players from rapid repetitive flashing while retaining broken
    // fluorescent/candle instability as a horror tool.
    float maxFlickerAmount = 0.42f;
    float maxFlickerHz = 3.0f;
};

struct HorrorLightingFrame {
    Vec3 keyDirection{};
    Vec3 keyColorLinear{};
    float keyIntensity = 0.0f;

    Vec3 ambientColorLinear{};
    float ambientIntensity = 0.0f;

    Vec3 fogColorLinear{};
    float fogDensity = 0.0f;
    float fogHeightFalloff = 0.0f;

    float exposureEv = 0.0f;
    float exposureScale = 1.0f;
    float contrast = 1.0f;
    float saturation = 1.0f;
    float tension = 0.0f;

    std::array<RuntimeLocalLight, kMaxRuntimeLocalLights> localLights{};
    std::size_t localLightCount = 0U;
};

[[nodiscard]] HorrorLightingConfig makeSanctumLightingConfig() noexcept;

class HorrorLightingDirector final {
public:
    explicit HorrorLightingDirector(
        HorrorLightingConfig config = makeSanctumLightingConfig());

    void reset() noexcept;
    void setConfig(HorrorLightingConfig config) noexcept;

    [[nodiscard]] HorrorLightingFrame advance(
        const HorrorFrame& horror,
        const EnvironmentFrame& environment,
        const Vec3& cameraPosition,
        const LocalLightInput* localLights,
        std::size_t localLightCount,
        RenderQuality quality,
        float timeSeconds) noexcept;

    [[nodiscard]] const HorrorLightingFrame& frame() const noexcept;
    [[nodiscard]] const HorrorLightingConfig& config() const noexcept;

private:
    [[nodiscard]] static float clamp01(float value) noexcept;
    [[nodiscard]] static Vec3 normalizeOr(
        const Vec3& value,
        const Vec3& fallback) noexcept;
    [[nodiscard]] static float lightScore(
        const LocalLightInput& light,
        const Vec3& cameraPosition) noexcept;
    [[nodiscard]] float flickerMultiplier(
        const LocalLightInput& light,
        float timeSeconds) const noexcept;
    [[nodiscard]] static std::size_t qualityLightBudget(
        RenderQuality quality) noexcept;

    HorrorLightingConfig config_{};
    HorrorLightingFrame frame_{};
};

} // namespace xziel
