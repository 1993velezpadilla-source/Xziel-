#include "xziel/haptics.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

HapticsPlanner::HapticsPlanner(HapticConfig config)
    : config_(config) {}

void HapticsPlanner::reset() noexcept {
    elapsedSincePlay_ = 999.0f;
}

HapticCommand HapticsPlanner::request(
    HapticEvent event,
    const HapticCapabilities& capabilities,
    float deltaSincePreviousRequestSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSincePreviousRequestSeconds) ||
         deltaSincePreviousRequestSeconds < 0.0f)
        ? 0.0f
        : std::min(deltaSincePreviousRequestSeconds, 1.0f);

    elapsedSincePlay_ += dt;

    HapticCommand out{};
    out.event = event;

    if (!config_.enabled ||
        !capabilities.hasVibrator ||
        config_.userStrength <= 0.0f) {
        return out;
    }

    // High-rate events such as automatic weapon fire should not become a
    // continuous buzzy motor. Low-value requests inside the gap are dropped.
    const float requiredGap =
        isFrequent(event)
        ? std::max(config_.minimumGapSeconds, 0.030f)
        : config_.minimumGapSeconds;

    if (elapsedSincePlay_ < requiredGap) {
        return out;
    }

    float strength = baseAmplitude(event);

    if (isFrequent(event)) {
        strength *= config_.frequentEventStrengthScale;
    }
    if (event == HapticEvent::Heartbeat) {
        strength *= config_.heartbeatStrengthScale;
    }

    out.play = true;
    out.amplitude =
        clamp01(strength * config_.userStrength);
    out.durationSeconds = baseDuration(event);
    out.sharpness = baseSharpness(event);

    out.preferComposition =
        capabilities.hasCompositionPrimitives &&
        (event == HapticEvent::ZombieGrab ||
         event == HapticEvent::ExplosionNear ||
         event == HapticEvent::HorrorStinger);

    out.preferEnvelope =
        capabilities.hasEnvelopeEffects &&
        (event == HapticEvent::ZombieGrab ||
         event == HapticEvent::ExplosionNear);

    // If amplitude control is unavailable, the Android backend should prefer a
    // predefined clear effect rather than mapping every non-zero value to a
    // long buzzy on/off waveform.
    if (!capabilities.hasAmplitudeControl) {
        out.amplitude = out.amplitude > 0.0f ? 1.0f : 0.0f;
    }

    elapsedSincePlay_ = 0.0f;
    return out;
}

const HapticConfig& HapticsPlanner::config() const noexcept {
    return config_;
}

float HapticsPlanner::clamp01(float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

float HapticsPlanner::baseAmplitude(HapticEvent event) noexcept {
    switch (event) {
        case HapticEvent::UiConfirm: return 0.18f;
        case HapticEvent::UiError: return 0.28f;
        case HapticEvent::FireLight: return 0.24f;
        case HapticEvent::FireHeavy: return 0.46f;
        case HapticEvent::ReloadInsert: return 0.16f;
        case HapticEvent::ReloadComplete: return 0.25f;
        case HapticEvent::PlayerHit: return 0.58f;
        case HapticEvent::ZombieGrab: return 0.72f;
        case HapticEvent::ExplosionNear: return 0.85f;
        case HapticEvent::SlideImpact: return 0.32f;
        case HapticEvent::MantleContact: return 0.22f;
        case HapticEvent::Heartbeat: return 0.30f;
        case HapticEvent::HorrorStinger: return 0.52f;
    }
    return 0.20f;
}

float HapticsPlanner::baseDuration(HapticEvent event) noexcept {
    switch (event) {
        case HapticEvent::UiConfirm: return 0.012f;
        case HapticEvent::UiError: return 0.020f;
        case HapticEvent::FireLight: return 0.012f;
        case HapticEvent::FireHeavy: return 0.020f;
        case HapticEvent::ReloadInsert: return 0.010f;
        case HapticEvent::ReloadComplete: return 0.016f;
        case HapticEvent::PlayerHit: return 0.030f;
        case HapticEvent::ZombieGrab: return 0.060f;
        case HapticEvent::ExplosionNear: return 0.075f;
        case HapticEvent::SlideImpact: return 0.022f;
        case HapticEvent::MantleContact: return 0.016f;
        case HapticEvent::Heartbeat: return 0.030f;
        case HapticEvent::HorrorStinger: return 0.040f;
    }
    return 0.016f;
}

float HapticsPlanner::baseSharpness(HapticEvent event) noexcept {
    switch (event) {
        case HapticEvent::ExplosionNear: return 0.20f;
        case HapticEvent::ZombieGrab: return 0.36f;
        case HapticEvent::Heartbeat: return 0.28f;
        case HapticEvent::PlayerHit: return 0.55f;
        case HapticEvent::FireHeavy: return 0.70f;
        case HapticEvent::FireLight: return 0.82f;
        case HapticEvent::ReloadInsert: return 0.88f;
        case HapticEvent::ReloadComplete: return 0.80f;
        case HapticEvent::UiConfirm: return 0.90f;
        case HapticEvent::UiError: return 0.72f;
        case HapticEvent::SlideImpact: return 0.48f;
        case HapticEvent::MantleContact: return 0.68f;
        case HapticEvent::HorrorStinger: return 0.52f;
    }
    return 0.60f;
}

bool HapticsPlanner::isFrequent(HapticEvent event) noexcept {
    return event == HapticEvent::FireLight ||
        event == HapticEvent::FireHeavy ||
        event == HapticEvent::ReloadInsert ||
        event == HapticEvent::Heartbeat;
}

} // namespace xziel
