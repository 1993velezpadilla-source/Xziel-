#pragma once

#include <cstdint>

namespace xziel {

enum class HapticEvent : std::uint8_t {
    UiConfirm,
    UiError,
    FireLight,
    FireHeavy,
    ReloadInsert,
    ReloadComplete,
    PlayerHit,
    ZombieGrab,
    ExplosionNear,
    SlideImpact,
    MantleContact,
    Heartbeat,
    HorrorStinger,
};

struct HapticCapabilities {
    bool hasVibrator = true;
    bool hasAmplitudeControl = false;
    bool hasCompositionPrimitives = false;
    bool hasEnvelopeEffects = false;
};

struct HapticConfig {
    bool enabled = true;
    float userStrength = 1.0f;
    float frequentEventStrengthScale = 0.55f;
    float heartbeatStrengthScale = 0.42f;
    float minimumGapSeconds = 0.018f;
};

struct HapticCommand {
    bool play = false;
    HapticEvent event = HapticEvent::UiConfirm;

    float amplitude = 0.0f;
    float sharpness = 0.5f;
    float durationSeconds = 0.0f;

    // Rich-capability backends can translate these into compositions/envelopes.
    bool preferComposition = false;
    bool preferEnvelope = false;
};

class HapticsPlanner final {
public:
    explicit HapticsPlanner(HapticConfig config = {});

    void reset() noexcept;

    [[nodiscard]] HapticCommand request(
        HapticEvent event,
        const HapticCapabilities& capabilities,
        float deltaSincePreviousRequestSeconds) noexcept;

    [[nodiscard]] const HapticConfig& config() const noexcept;

private:
    [[nodiscard]] static float clamp01(float value) noexcept;
    [[nodiscard]] static float baseAmplitude(HapticEvent event) noexcept;
    [[nodiscard]] static float baseDuration(HapticEvent event) noexcept;
    [[nodiscard]] static float baseSharpness(HapticEvent event) noexcept;
    [[nodiscard]] static bool isFrequent(HapticEvent event) noexcept;

    HapticConfig config_{};
    float elapsedSincePlay_ = 999.0f;
};

} // namespace xziel
