#include "xziel/sanctum_immersion.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float safeDt(float value) noexcept {
    if (!std::isfinite(value) || value <= 0.0f) {
        return 0.0f;
    }
    return std::min(value, 0.10f);
}

float magnitude(const Vec3& value) noexcept {
    return std::sqrt(
        value.x * value.x +
        value.y * value.y +
        value.z * value.z);
}

float approach(
    float current,
    float target,
    float maximumStep) noexcept {
    if (current < target) {
        return std::min(current + maximumStep, target);
    }
    return std::max(current - maximumStep, target);
}

SanctumSoundEvent makeEvent(
    SanctumSoundCue cue,
    std::uint32_t emitterId,
    float gain,
    float pitch = 1.0f,
    bool critical = false) noexcept {
    return {
        .cue = cue,
        .emitterId = emitterId,
        .gain = gain,
        .pitch = pitch,
        .spatial = true,
        .critical = critical,
    };
}

} // namespace

WindowAtmosphereSystem::WindowAtmosphereSystem(
    WindowAtmosphereConfig config)
    : config_(config) {
    config_.windStartMetersPerSecond =
        std::max(0.0f, config_.windStartMetersPerSecond);
    config_.strongWindMetersPerSecond =
        std::max(
            config_.windStartMetersPerSecond + 0.1f,
            config_.strongWindMetersPerSecond);
    config_.maximumSwingDegrees =
        std::max(0.0f, config_.maximumSwingDegrees);
    config_.maximumAngularSpeedDegreesPerSecond =
        std::max(1.0f, config_.maximumAngularSpeedDegreesPerSecond);
    config_.oscillationHz =
        std::max(0.01f, config_.oscillationHz);
    config_.rattleIntervalSeconds =
        std::max(0.10f, config_.rattleIntervalSeconds);
    config_.creakIntervalSeconds =
        std::max(0.10f, config_.creakIntervalSeconds);
    config_.slamCooldownSeconds =
        std::max(0.10f, config_.slamCooldownSeconds);
    reset();
}

void WindowAtmosphereSystem::reset() noexcept {
    frame_ = {};
    phaseSeconds_ = 0.0f;
    rattleSeconds_ = 0.0f;
    creakSeconds_ = 0.0f;
    slamSeconds_ = 999.0f;
}

WindowAtmosphereFrame WindowAtmosphereSystem::advance(
    const Vec3& windMetersPerSecond,
    float deltaSeconds) noexcept {
    const float dt = safeDt(deltaSeconds);
    const float speed = magnitude(windMetersPerSecond);

    frame_.rattleThisTick = false;
    frame_.creakThisTick = false;
    frame_.slamThisTick = false;

    phaseSeconds_ += dt;
    rattleSeconds_ += dt;
    creakSeconds_ += dt;
    slamSeconds_ += dt;

    float strength = 0.0f;
    if (speed > config_.windStartMetersPerSecond) {
        strength = std::clamp(
            (speed - config_.windStartMetersPerSecond) /
                (config_.strongWindMetersPerSecond -
                 config_.windStartMetersPerSecond),
            0.0f,
            1.0f);
    }

    constexpr float twoPi = 6.28318530718f;
    const float gust =
        std::sin(
            phaseSeconds_ *
            config_.oscillationHz *
            twoPi);

    const float windDirectionSign =
        windMetersPerSecond.x < 0.0f ? -1.0f : 1.0f;
    const float targetAngle =
        windDirectionSign *
        config_.maximumSwingDegrees *
        strength *
        gust;

    const float previousAngle = frame_.angleDegrees;
    frame_.angleDegrees = approach(
        frame_.angleDegrees,
        targetAngle,
        config_.maximumAngularSpeedDegreesPerSecond * dt);

    const float movement =
        std::fabs(frame_.angleDegrees - previousAngle);
    frame_.moving = movement > 0.001f;

    if (strength > 0.18f &&
        rattleSeconds_ >= config_.rattleIntervalSeconds) {
        frame_.rattleThisTick = true;
        rattleSeconds_ = 0.0f;
    }

    if (frame_.moving &&
        strength > 0.28f &&
        creakSeconds_ >= config_.creakIntervalSeconds) {
        frame_.creakThisTick = true;
        creakSeconds_ = 0.0f;
    }

    const float slamThreshold =
        config_.maximumSwingDegrees * 0.84f;
    if (speed >= config_.strongWindMetersPerSecond &&
        std::fabs(previousAngle) < slamThreshold &&
        std::fabs(frame_.angleDegrees) >= slamThreshold &&
        slamSeconds_ >= config_.slamCooldownSeconds) {
        frame_.slamThisTick = true;
        slamSeconds_ = 0.0f;
    }

    return frame_;
}

void ThunderAudioScheduler::reset() noexcept {
    emitterId_ = 0;
    distanceMeters_ = 0.0f;
    secondsRemaining_ = 0.0f;
    pending_ = false;
}

void ThunderAudioScheduler::schedule(
    std::uint32_t emitterId,
    float strikeDistanceMeters) noexcept {
    emitterId_ = emitterId;
    distanceMeters_ = std::clamp(
        std::isfinite(strikeDistanceMeters)
            ? strikeDistanceMeters
            : 0.0f,
        0.0f,
        1600.0f);

    constexpr float speedOfSoundMetersPerSecond = 343.0f;
    secondsRemaining_ =
        distanceMeters_ / speedOfSoundMetersPerSecond;
    pending_ = true;
}

SanctumSoundEvent ThunderAudioScheduler::advance(
    float deltaSeconds) noexcept {
    if (!pending_) {
        return {};
    }

    secondsRemaining_ -= safeDt(deltaSeconds);
    if (secondsRemaining_ > 0.0f) {
        return {};
    }

    pending_ = false;

    if (distanceMeters_ < 55.0f) {
        return makeEvent(
            SanctumSoundCue::ThunderNear,
            emitterId_,
            1.0f,
            1.0f,
            true);
    }
    if (distanceMeters_ < 180.0f) {
        return makeEvent(
            SanctumSoundCue::ThunderMid,
            emitterId_,
            0.92f);
    }
    return makeEvent(
        SanctumSoundCue::ThunderFar,
        emitterId_,
        0.78f,
        0.96f);
}

bool ThunderAudioScheduler::pending() const noexcept {
    return pending_;
}

SanctumSoundEvent SanctumSoundEventRouter::door(
    const DoorFrame& previous,
    const DoorFrame& current) noexcept {
    if (current.openedThisTick) {
        return makeEvent(
            SanctumSoundCue::DoorWoodOpenStart,
            current.id,
            0.95f,
            1.0f,
            true);
    }

    if (current.becameFullyOpenThisTick) {
        return makeEvent(
            SanctumSoundCue::DoorWoodOpenStop,
            current.id,
            0.90f);
    }

    constexpr float creakPoint = 0.46f;
    if (current.opening &&
        previous.openProgress < creakPoint &&
        current.openProgress >= creakPoint) {
        return makeEvent(
            SanctumSoundCue::DoorWoodCreak,
            current.id,
            0.88f,
            0.97f);
    }

    return {};
}

SanctumSoundEvent SanctumSoundEventRouter::barricade(
    std::uint32_t emitterId,
    const BarricadeFrame& previous,
    const BarricadeFrame& current) noexcept {
    (void) previous;

    if (current.breachedThisTick) {
        return makeEvent(
            SanctumSoundCue::BarricadeBreach,
            emitterId,
            1.0f,
            0.96f,
            true);
    }
    if (current.plankRemovedThisTick) {
        return makeEvent(
            SanctumSoundCue::BarricadePlankRip,
            emitterId,
            0.92f);
    }
    if (current.plankRebuiltThisTick) {
        return makeEvent(
            SanctumSoundCue::BarricadePlankRebuild,
            emitterId,
            0.82f,
            1.02f);
    }

    return {};
}

SanctumSoundEvent SanctumSoundEventRouter::footstep(
    std::uint32_t emitterId,
    SanctumSurface surface,
    bool sprinting) noexcept {
    SanctumSoundCue cue = SanctumSoundCue::FootstepStone;

    switch (surface) {
        case SanctumSurface::Wood:
            cue = SanctumSoundCue::FootstepWood;
            break;
        case SanctumSurface::WetWood:
            cue = SanctumSoundCue::FootstepWetWood;
            break;
        case SanctumSurface::WetStone:
            cue = SanctumSoundCue::FootstepWetStone;
            break;
        case SanctumSurface::Stone:
        case SanctumSurface::Metal:
        case SanctumSurface::Dirt:
            cue = SanctumSoundCue::FootstepStone;
            break;
    }

    return makeEvent(
        cue,
        emitterId,
        sprinting ? 1.0f : 0.82f,
        sprinting ? 1.03f : 0.99f);
}

SanctumSoundEvent SanctumSoundEventRouter::window(
    std::uint32_t emitterId,
    const WindowAtmosphereFrame& frame) noexcept {
    if (frame.slamThisTick) {
        return makeEvent(
            SanctumSoundCue::WindowSlam,
            emitterId,
            1.0f,
            0.96f,
            true);
    }
    if (frame.creakThisTick) {
        return makeEvent(
            SanctumSoundCue::WindowWoodCreak,
            emitterId,
            0.76f,
            0.98f);
    }
    if (frame.rattleThisTick) {
        return makeEvent(
            SanctumSoundCue::WindowRattle,
            emitterId,
            0.68f);
    }
    return {};
}

} // namespace xziel
