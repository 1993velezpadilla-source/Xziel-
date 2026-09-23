#pragma once

#include "xziel/barricade.hpp"
#include "xziel/door.hpp"
#include "xziel/engine.hpp"

#include <cstdint>

namespace xziel {

enum class SanctumSurface : std::uint8_t {
    Wood,
    Stone,
    WetWood,
    WetStone,
    Metal,
    Dirt,
};

enum class SanctumSoundCue : std::uint8_t {
    None,
    DoorWoodOpenStart,
    DoorWoodCreak,
    DoorWoodOpenStop,
    BarricadeWoodStrain,
    BarricadePlankRip,
    BarricadeBreach,
    BarricadePlankRebuild,
    FootstepWood,
    FootstepStone,
    FootstepWetWood,
    FootstepWetStone,
    WindowRattle,
    WindowWoodCreak,
    WindowSlam,
    GlassCrack,
    GlassBreak,
    RainExteriorLoop,
    RainInteriorLoop,
    WindLoop,
    WindGust,
    LightningCrack,
    ThunderNear,
    ThunderMid,
    ThunderFar,
    SoulWhisper,
    HorrorStinger,
    GrenadePin,
    GrenadeThrow,
    GrenadeExplosion,
};

struct SanctumSoundEvent {
    SanctumSoundCue cue = SanctumSoundCue::None;
    std::uint32_t emitterId = 0;
    float gain = 1.0f;
    float pitch = 1.0f;
    bool spatial = true;
    bool critical = false;

    [[nodiscard]] bool valid() const noexcept {
        return cue != SanctumSoundCue::None;
    }
};

struct WindowAtmosphereConfig {
    float windStartMetersPerSecond = 2.8f;
    float strongWindMetersPerSecond = 8.5f;
    float maximumSwingDegrees = 18.0f;
    float maximumAngularSpeedDegreesPerSecond = 42.0f;
    float oscillationHz = 0.32f;
    float rattleIntervalSeconds = 1.35f;
    float creakIntervalSeconds = 2.40f;
    float slamCooldownSeconds = 3.5f;
};

struct WindowAtmosphereFrame {
    float angleDegrees = 0.0f;
    bool moving = false;
    bool rattleThisTick = false;
    bool creakThisTick = false;
    bool slamThisTick = false;
};

class WindowAtmosphereSystem final {
public:
    explicit WindowAtmosphereSystem(WindowAtmosphereConfig config = {});

    void reset() noexcept;

    [[nodiscard]] WindowAtmosphereFrame advance(
        const Vec3& windMetersPerSecond,
        float deltaSeconds) noexcept;

private:
    WindowAtmosphereConfig config_{};
    WindowAtmosphereFrame frame_{};
    float phaseSeconds_ = 0.0f;
    float rattleSeconds_ = 0.0f;
    float creakSeconds_ = 0.0f;
    float slamSeconds_ = 999.0f;
};

class ThunderAudioScheduler final {
public:
    void reset() noexcept;

    void schedule(
        std::uint32_t emitterId,
        float strikeDistanceMeters) noexcept;

    [[nodiscard]] SanctumSoundEvent advance(float deltaSeconds) noexcept;
    [[nodiscard]] bool pending() const noexcept;

private:
    std::uint32_t emitterId_ = 0;
    float distanceMeters_ = 0.0f;
    float secondsRemaining_ = 0.0f;
    bool pending_ = false;
};

class SanctumSoundEventRouter final {
public:
    [[nodiscard]] static SanctumSoundEvent door(
        const DoorFrame& previous,
        const DoorFrame& current) noexcept;

    [[nodiscard]] static SanctumSoundEvent barricade(
        std::uint32_t emitterId,
        const BarricadeFrame& previous,
        const BarricadeFrame& current) noexcept;

    [[nodiscard]] static SanctumSoundEvent footstep(
        std::uint32_t emitterId,
        SanctumSurface surface,
        bool sprinting) noexcept;

    [[nodiscard]] static SanctumSoundEvent window(
        std::uint32_t emitterId,
        const WindowAtmosphereFrame& frame) noexcept;
};

} // namespace xziel
