#pragma once

#include <cstdint>

namespace xziel {

struct HorrorStimulus {
    // Normalized gameplay/context signals supplied by game code.
    float threatProximity = 0.0f;
    float hordePressure = 0.0f;
    float recentDamage = 0.0f;
    float darkness = 0.0f;
    float isolation = 0.0f;
    float lowAmmoPressure = 0.0f;
    float lowHealthPressure = 0.0f;

    bool beingChased = false;
    bool safeRoom = false;
    bool scriptedScareWindow = false;
};

struct HorrorConfig {
    float tensionAttackPerSecond = 1.25f;
    float tensionReleasePerSecond = 0.28f;
    float adrenalineAttackPerSecond = 2.20f;
    float adrenalineReleasePerSecond = 0.72f;

    float stingerThreshold = 0.76f;
    float stingerCooldownSeconds = 12.0f;
    float minimumScareGapSeconds = 5.0f;

    // Presentation is intentionally bounded. The director suggests targets,
    // never directly manipulates gameplay rules.
    float maxVignette = 0.28f;
    float maxExposureDropEv = 0.45f;
    float maxCameraBreathing = 0.16f;
    float maxLightFlicker = 0.22f;
    float maxFogBoost = 0.18f;

    // Strong repetitive flashing is avoided by design; authored content may
    // opt into accessibility-reviewed effects separately.
    float maxFlickerHz = 3.0f;
};

struct HorrorFrame {
    float tension = 0.0f;
    float adrenaline = 0.0f;

    float ambientDroneGain = 0.0f;
    float heartbeatGain = 0.0f;
    float breathingGain = 0.0f;

    float vignetteStrength = 0.0f;
    float exposureBiasEv = 0.0f;
    float cameraBreathing = 0.0f;
    float lightFlickerAmount = 0.0f;
    float lightFlickerHz = 0.0f;
    float fogDensityBoost = 0.0f;

    bool requestAudioStinger = false;
};

class HorrorDirector final {
public:
    explicit HorrorDirector(HorrorConfig config = {});

    void reset() noexcept;

    [[nodiscard]] HorrorFrame advance(
        const HorrorStimulus& stimulus,
        float deltaSeconds) noexcept;

    [[nodiscard]] const HorrorFrame& frame() const noexcept;
    [[nodiscard]] const HorrorConfig& config() const noexcept;

private:
    [[nodiscard]] static float clamp01(float value) noexcept;
    [[nodiscard]] static float approach(
        float current,
        float target,
        float risePerSecond,
        float fallPerSecond,
        float deltaSeconds) noexcept;

    HorrorConfig config_{};
    HorrorFrame frame_{};

    float secondsSinceStinger_ = 9999.0f;
    float secondsSinceScareWindow_ = 9999.0f;
    bool scareWindowWasOpen_ = false;
};

} // namespace xziel
