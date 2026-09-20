#include "xziel/horror.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float sanitizeDt(float dt) noexcept {
    if (!std::isfinite(dt) || dt <= 0.0f) {
        return 0.0f;
    }
    return std::min(dt, 0.10f);
}

} // namespace

HorrorDirector::HorrorDirector(HorrorConfig config)
    : config_(config) {
    reset();
}

void HorrorDirector::reset() noexcept {
    frame_ = {};
    secondsSinceStinger_ = 9999.0f;
    secondsSinceScareWindow_ = 9999.0f;
    scareWindowWasOpen_ = false;
}

HorrorFrame HorrorDirector::advance(
    const HorrorStimulus& stimulus,
    float deltaSeconds) noexcept {
    const float dt = sanitizeDt(deltaSeconds);
    secondsSinceStinger_ += dt;
    secondsSinceScareWindow_ += dt;

    const float threat = clamp01(stimulus.threatProximity);
    const float horde = clamp01(stimulus.hordePressure);
    const float damage = clamp01(stimulus.recentDamage);
    const float darkness = clamp01(stimulus.darkness);
    const float isolation = clamp01(stimulus.isolation);
    const float ammo = clamp01(stimulus.lowAmmoPressure);
    const float health = clamp01(stimulus.lowHealthPressure);

    float tensionTarget =
        0.29f * threat +
        0.24f * horde +
        0.12f * darkness +
        0.10f * isolation +
        0.09f * ammo +
        0.10f * health +
        0.06f * damage;

    float adrenalineTarget =
        0.34f * threat +
        0.28f * horde +
        0.20f * damage +
        0.10f * health +
        0.08f * ammo;

    if (stimulus.beingChased) {
        tensionTarget += 0.18f;
        adrenalineTarget += 0.30f;
    }

    if (stimulus.safeRoom) {
        // Let players emotionally decompress. A horror game that never releases
        // pressure quickly becomes noise instead of fear.
        tensionTarget *= 0.28f;
        adrenalineTarget *= 0.12f;
    }

    tensionTarget = clamp01(tensionTarget);
    adrenalineTarget = clamp01(adrenalineTarget);

    frame_.tension = approach(
        frame_.tension,
        tensionTarget,
        config_.tensionAttackPerSecond,
        config_.tensionReleasePerSecond,
        dt);
    frame_.adrenaline = approach(
        frame_.adrenaline,
        adrenalineTarget,
        config_.adrenalineAttackPerSecond,
        config_.adrenalineReleasePerSecond,
        dt);

    frame_.ambientDroneGain =
        clamp01(0.10f + frame_.tension * 0.82f);
    frame_.heartbeatGain =
        clamp01((frame_.adrenaline - 0.30f) / 0.70f);
    frame_.breathingGain =
        clamp01((frame_.adrenaline - 0.18f) / 0.82f);

    frame_.vignetteStrength =
        config_.maxVignette *
        clamp01(frame_.tension * 0.65f + frame_.adrenaline * 0.35f);
    frame_.exposureBiasEv =
        -config_.maxExposureDropEv * frame_.tension;
    frame_.cameraBreathing =
        config_.maxCameraBreathing *
        clamp01(frame_.tension * 0.35f + frame_.adrenaline * 0.65f);
    frame_.fogDensityBoost =
        config_.maxFogBoost * frame_.tension;

    frame_.lightFlickerAmount =
        config_.maxLightFlicker *
        clamp01((frame_.tension - 0.45f) / 0.55f);
    frame_.lightFlickerHz =
        config_.maxFlickerHz *
        clamp01(0.35f + frame_.tension * 0.65f);

    frame_.requestAudioStinger = false;

    const bool scareWindowOpened =
        stimulus.scriptedScareWindow && !scareWindowWasOpen_;
    if (scareWindowOpened) {
        secondsSinceScareWindow_ = 0.0f;
    }
    scareWindowWasOpen_ = stimulus.scriptedScareWindow;

    const bool enoughIntensity =
        frame_.tension >= config_.stingerThreshold ||
        frame_.adrenaline >= config_.stingerThreshold;
    const bool cooldownReady =
        secondsSinceStinger_ >= config_.stingerCooldownSeconds;
    const bool scareGapReady =
        secondsSinceScareWindow_ <= 0.20f ||
        secondsSinceScareWindow_ >= config_.minimumScareGapSeconds;

    // A stinger requires an authored scare window or a high-intensity chase.
    // The engine never fires random jump scares simply because a meter is high.
    if (enoughIntensity &&
        cooldownReady &&
        scareGapReady &&
        (stimulus.scriptedScareWindow || stimulus.beingChased)) {
        frame_.requestAudioStinger = true;
        secondsSinceStinger_ = 0.0f;
    }

    return frame_;
}

const HorrorFrame& HorrorDirector::frame() const noexcept {
    return frame_;
}

const HorrorConfig& HorrorDirector::config() const noexcept {
    return config_;
}

float HorrorDirector::clamp01(float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

float HorrorDirector::approach(
    float current,
    float target,
    float risePerSecond,
    float fallPerSecond,
    float deltaSeconds) noexcept {
    const float rate = target > current
        ? std::max(0.0f, risePerSecond)
        : std::max(0.0f, fallPerSecond);
    const float maxStep = rate * deltaSeconds;

    if (current < target) {
        return std::min(current + maxStep, target);
    }
    return std::max(current - maxStep, target);
}

} // namespace xziel
