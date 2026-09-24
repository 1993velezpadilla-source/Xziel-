#include "xziel/lighting.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

constexpr float kPi = 3.14159265358979323846f;

float radians(float degrees) noexcept {
    return degrees * (kPi / 180.0f);
}

float sanitizeFinite(float value, float fallback = 0.0f) noexcept {
    return std::isfinite(value) ? value : fallback;
}

float distanceSquared(
    const Vec3& a,
    const Vec3& b) noexcept {
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    const float dz = a.z - b.z;
    return dx * dx + dy * dy + dz * dz;
}

} // namespace

HorrorLightingConfig makeSanctumLightingConfig() noexcept {
    HorrorLightingConfig config{};
    config.mood = HorrorLightingMood::Sanctum;

    // Sanctum deliberately separates a weak warm practical/key from a cold
    // blue-black ambient field. This preserves material readability while
    // leaving large negative-space regions that horror lighting depends on.
    config.keyDirection = {-0.34f, -0.82f, -0.46f};
    config.keyColorLinear = {1.0f, 0.58f, 0.30f};
    config.keyIntensity = 0.78f;

    config.ambientColorLinear = {0.085f, 0.135f, 0.22f};
    config.ambientIntensity = 0.20f;

    config.fogColorLinear = {0.022f, 0.034f, 0.052f};
    config.baseFogDensity = 0.050f;
    config.fogHeightFalloff = 0.12f;
    config.fogTensionBoost = 0.085f;

    config.baseExposureEv = -0.40f;
    config.tensionExposureDropEv = 0.22f;
    config.contrast = 1.10f;
    config.saturation = 0.86f;
    config.tensionDesaturation = 0.07f;

    config.maxFlickerAmount = 0.38f;
    config.maxFlickerHz = 3.0f;
    return config;
}

HorrorLightingDirector::HorrorLightingDirector(
    HorrorLightingConfig config)
    : config_(config) {
    reset();
}

void HorrorLightingDirector::reset() noexcept {
    frame_ = {};
    frame_.exposureScale = 1.0f;
    frame_.contrast = 1.0f;
    frame_.saturation = 1.0f;
}

void HorrorLightingDirector::setConfig(
    HorrorLightingConfig config) noexcept {
    config_ = config;
    reset();
}

HorrorLightingFrame HorrorLightingDirector::advance(
    const HorrorFrame& horror,
    const EnvironmentFrame& environment,
    const Vec3& cameraPosition,
    const LocalLightInput* localLights,
    std::size_t localLightCount,
    RenderQuality quality,
    float timeSeconds) noexcept {
    frame_ = {};

    const float tension = clamp01(horror.tension);
    frame_.tension = tension;

    frame_.keyDirection =
        normalizeOr(
            config_.keyDirection,
            {-0.34f, -0.82f, -0.46f});
    frame_.keyColorLinear = {
        std::max(0.0f, sanitizeFinite(config_.keyColorLinear.x)),
        std::max(0.0f, sanitizeFinite(config_.keyColorLinear.y)),
        std::max(0.0f, sanitizeFinite(config_.keyColorLinear.z)),
    };

    const float lightning =
        std::clamp(
            sanitizeFinite(environment.lightningFlash),
            0.0f,
            2.0f);
    frame_.keyIntensity =
        std::max(
            0.0f,
            sanitizeFinite(config_.keyIntensity)) *
        (1.0f + lightning * 1.35f);

    frame_.ambientColorLinear = {
        std::max(0.0f, sanitizeFinite(config_.ambientColorLinear.x)),
        std::max(0.0f, sanitizeFinite(config_.ambientColorLinear.y)),
        std::max(0.0f, sanitizeFinite(config_.ambientColorLinear.z)),
    };
    frame_.ambientIntensity =
        std::max(
            0.0f,
            sanitizeFinite(config_.ambientIntensity)) *
        (1.0f - 0.12f * tension);

    frame_.fogColorLinear = {
        std::max(0.0f, sanitizeFinite(config_.fogColorLinear.x)),
        std::max(0.0f, sanitizeFinite(config_.fogColorLinear.y)),
        std::max(0.0f, sanitizeFinite(config_.fogColorLinear.z)),
    };
    frame_.fogDensity =
        std::clamp(
            std::max(
                sanitizeFinite(environment.fogDensity),
                sanitizeFinite(config_.baseFogDensity)) +
            std::max(0.0f, config_.fogTensionBoost) * tension,
            0.0f,
            1.0f);
    frame_.fogHeightFalloff =
        std::clamp(
            sanitizeFinite(config_.fogHeightFalloff),
            0.0f,
            2.0f);

    frame_.exposureEv =
        sanitizeFinite(config_.baseExposureEv) +
        std::clamp(
            sanitizeFinite(horror.exposureBiasEv),
            -1.5f,
            1.0f) -
        std::max(
            0.0f,
            sanitizeFinite(config_.tensionExposureDropEv)) *
        tension;
    frame_.exposureEv =
        std::clamp(
            frame_.exposureEv,
            -2.0f,
            1.0f);
    frame_.exposureScale =
        std::exp2(frame_.exposureEv);

    frame_.contrast =
        std::clamp(
            sanitizeFinite(config_.contrast, 1.0f) +
            tension * 0.04f,
            0.75f,
            1.35f);
    frame_.saturation =
        std::clamp(
            sanitizeFinite(config_.saturation, 1.0f) -
            std::max(
                0.0f,
                sanitizeFinite(config_.tensionDesaturation)) *
                tension,
            0.55f,
            1.15f);

    if (localLights == nullptr ||
        localLightCount == 0U) {
        return frame_;
    }

    const std::size_t budget =
        std::min(
            qualityLightBudget(quality),
            kMaxRuntimeLocalLights);

    const float safeTime =
        std::isfinite(timeSeconds)
        ? timeSeconds
        : 0.0f;

    while (frame_.localLightCount < budget) {
        std::size_t bestIndex = localLightCount;
        float bestScore = -1.0f;

        for (std::size_t candidate = 0U;
             candidate < localLightCount;
             ++candidate) {
            const auto& input =
                localLights[candidate];

            if (!input.enabled ||
                input.rangeMeters <= 0.01f ||
                input.intensity <= 0.0001f) {
                continue;
            }

            bool alreadySelected = false;
            for (std::size_t selected = 0U;
                 selected < frame_.localLightCount;
                 ++selected) {
                if (frame_.localLights[selected].id ==
                    input.id) {
                    alreadySelected = true;
                    break;
                }
            }

            if (alreadySelected) {
                continue;
            }

            const float score =
                lightScore(
                    input,
                    cameraPosition);

            if (score > bestScore) {
                bestScore = score;
                bestIndex = candidate;
            }
        }

        if (bestIndex >= localLightCount ||
            bestScore <= 0.0f) {
            break;
        }

        const auto& input =
            localLights[bestIndex];

        auto& output =
            frame_.localLights[
                frame_.localLightCount++];

        output.id = input.id;
        output.type = input.type;
        output.position = input.position;
        output.direction =
            normalizeOr(
                input.direction,
                {0.0f, -1.0f, 0.0f});
        output.colorLinear = {
            std::max(0.0f, sanitizeFinite(input.colorLinear.x)),
            std::max(0.0f, sanitizeFinite(input.colorLinear.y)),
            std::max(0.0f, sanitizeFinite(input.colorLinear.z)),
        };
        output.intensity =
            std::max(
                0.0f,
                sanitizeFinite(input.intensity)) *
            flickerMultiplier(
                input,
                safeTime);
        output.rangeMeters =
            std::clamp(
                sanitizeFinite(input.rangeMeters),
                0.05f,
                100.0f);

        const float inner =
            std::clamp(
                sanitizeFinite(input.innerConeDegrees),
                0.0f,
                89.0f);
        const float outer =
            std::clamp(
                std::max(
                    inner,
                    sanitizeFinite(input.outerConeDegrees)),
                inner,
                89.5f);

        output.innerConeCos =
            std::cos(radians(inner));
        output.outerConeCos =
            std::cos(radians(outer));
        output.castsShadows =
            input.castsShadows;
        output.volumetric =
            input.volumetric;
    }

    return frame_;
}

const HorrorLightingFrame&
HorrorLightingDirector::frame() const noexcept {
    return frame_;
}

const HorrorLightingConfig&
HorrorLightingDirector::config() const noexcept {
    return config_;
}

float HorrorLightingDirector::clamp01(
    float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

Vec3 HorrorLightingDirector::normalizeOr(
    const Vec3& value,
    const Vec3& fallback) noexcept {
    const float lengthSquared =
        value.x * value.x +
        value.y * value.y +
        value.z * value.z;

    if (!std::isfinite(lengthSquared) ||
        lengthSquared <= 1.0e-8f) {
        return fallback;
    }

    const float inverseLength =
        1.0f /
        std::sqrt(lengthSquared);
    return {
        value.x * inverseLength,
        value.y * inverseLength,
        value.z * inverseLength,
    };
}

float HorrorLightingDirector::lightScore(
    const LocalLightInput& light,
    const Vec3& cameraPosition) noexcept {
    if (!light.enabled) {
        return 0.0f;
    }

    const float range =
        std::max(
            sanitizeFinite(light.rangeMeters),
            0.05f);
    const float distance =
        std::sqrt(
            std::max(
                0.0f,
                distanceSquared(
                    light.position,
                    cameraPosition)));
    const float normalizedDistance =
        distance / range;

    if (normalizedDistance >= 1.35f) {
        return 0.0f;
    }

    const float distanceWeight =
        1.0f /
        (1.0f +
         normalizedDistance *
         normalizedDistance *
         3.0f);

    const float intensityWeight =
        std::sqrt(
            std::max(
                0.0f,
                sanitizeFinite(light.intensity)));

    const float importance =
        std::max(
            0.0f,
            sanitizeFinite(light.importance));

    const float volumetricBonus =
        light.volumetric
        ? 1.08f
        : 1.0f;

    return
        importance *
        distanceWeight *
        (0.30f + 0.70f * intensityWeight) *
        volumetricBonus;
}

float HorrorLightingDirector::flickerMultiplier(
    const LocalLightInput& light,
    float timeSeconds) const noexcept {
    const float amount =
        std::clamp(
            sanitizeFinite(light.flickerAmount),
            0.0f,
            std::max(
                0.0f,
                sanitizeFinite(config_.maxFlickerAmount)));

    if (amount <= 0.0001f) {
        return 1.0f;
    }

    const float hz =
        std::clamp(
            sanitizeFinite(light.flickerHz),
            0.0f,
            std::max(
                0.0f,
                sanitizeFinite(config_.maxFlickerHz)));

    if (hz <= 0.0001f) {
        return 1.0f;
    }

    const float seed =
        static_cast<float>(
            (light.id * 1103515245U + 12345U) &
            0xffffU) /
        65535.0f;

    const float phase =
        timeSeconds * hz * 2.0f * kPi +
        seed * 2.0f * kPi;

    // Blend two low-frequency deterministic waves. This reads as unstable
    // ballast/candle power without high-frequency strobing.
    const float wave =
        0.62f * std::sin(phase) +
        0.38f * std::sin(
            phase * 0.43f +
            1.7f);

    const float normalized =
        0.5f + 0.5f * wave;

    return
        std::clamp(
            1.0f -
                amount * 0.45f +
                amount * normalized,
            0.35f,
            1.20f);
}

std::size_t HorrorLightingDirector::qualityLightBudget(
    RenderQuality quality) noexcept {
    switch (quality) {
        case RenderQuality::Low:
            return 2U;
        case RenderQuality::Medium:
            return 4U;
        case RenderQuality::High:
            return 6U;
        case RenderQuality::Ultra:
            return 8U;
    }
    return 4U;
}

} // namespace xziel
