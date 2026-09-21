#include "xziel/weapon.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float sanitizeDuration(
    float value,
    float fallback) noexcept {
    if (!std::isfinite(value) ||
        value <= 0.0f) {
        return fallback;
    }

    return value;
}

float moveToward(
    float current,
    float target,
    float amount) noexcept {
    if (current < target) {
        return std::min(
            current + amount,
            target);
    }

    return std::max(
        current - amount,
        target);
}

} // namespace

WeaponController::WeaponController(
    WeaponConfig config)
    : config_(config) {
    config_.magazineSize =
        std::max<std::uint32_t>(
            config_.magazineSize,
            1U);

    config_.fireIntervalSeconds =
        sanitizeDuration(
            config_.fireIntervalSeconds,
            0.095f);

    config_.reloadSeconds =
        sanitizeDuration(
            config_.reloadSeconds,
            1.85f);

    config_.adsInSeconds =
        sanitizeDuration(
            config_.adsInSeconds,
            0.15f);

    config_.adsOutSeconds =
        sanitizeDuration(
            config_.adsOutSeconds,
            0.11f);

    reset();
}

void WeaponController::reset() noexcept {
    frame_ = {};
    frame_.phase =
        WeaponPhase::Ready;
    frame_.magazine =
        config_.magazineSize;
    frame_.reserve =
        config_.startingReserve;

    fireCooldownSeconds_ = 0.0f;
    reloadElapsedSeconds_ = 0.0f;
}

WeaponFrame WeaponController::step(
    const WeaponInput& input,
    float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) ||
         deltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(
              deltaSeconds,
              0.05f);

    frame_.firedThisTick = false;
    frame_.dryFireThisTick = false;
    frame_.reloadStartedThisTick = false;
    frame_.reloadCompletedThisTick = false;
    frame_.recoilPitchImpulse = 0.0f;
    frame_.recoilYawImpulse = 0.0f;

    fireCooldownSeconds_ =
        std::max(
            0.0f,
            fireCooldownSeconds_ - dt);

    const float adsTarget =
        input.aimHeld
        ? 1.0f
        : 0.0f;

    const float adsDuration =
        input.aimHeld
        ? config_.adsInSeconds
        : config_.adsOutSeconds;

    frame_.adsAlpha =
        moveToward(
            frame_.adsAlpha,
            adsTarget,
            dt /
                std::max(
                    adsDuration,
                    0.001f));

    if (frame_.phase ==
        WeaponPhase::Reloading) {
        reloadElapsedSeconds_ += dt;

        frame_.reloadAlpha =
            std::clamp(
                reloadElapsedSeconds_ /
                    config_.reloadSeconds,
                0.0f,
                1.0f);

        if (reloadElapsedSeconds_ +
                1.0e-6f >=
            config_.reloadSeconds) {
            completeReload();
        }

        return frame_;
    }

    frame_.reloadAlpha = 0.0f;

    if (input.reloadPressed &&
        frame_.magazine <
            config_.magazineSize &&
        frame_.reserve > 0) {
        startReload();
        return frame_;
    }

    if (!wantsShot(input) ||
        fireCooldownSeconds_ > 0.0f) {
        return frame_;
    }

    if (frame_.magazine == 0) {
        frame_.dryFireThisTick = true;
        fireCooldownSeconds_ =
            config_.fireIntervalSeconds;
        return frame_;
    }

    --frame_.magazine;
    ++frame_.shotCounter;

    frame_.firedThisTick = true;
    fireCooldownSeconds_ =
        config_.fireIntervalSeconds;

    const float deterministicYawSign =
        (frame_.shotCounter & 1ULL) != 0ULL
        ? 1.0f
        : -1.0f;

    const float deterministicYawScale =
        0.62f +
        static_cast<float>(
            frame_.shotCounter % 5ULL) *
            0.095f;

    frame_.recoilPitchImpulse =
        config_.recoilPitchDegrees;

    frame_.recoilYawImpulse =
        config_.recoilYawDegrees *
        deterministicYawSign *
        deterministicYawScale;

    return frame_;
}

const WeaponFrame&
WeaponController::frame() const noexcept {
    return frame_;
}

const WeaponConfig&
WeaponController::config() const noexcept {
    return config_;
}

void WeaponController::startReload() noexcept {
    frame_.phase =
        WeaponPhase::Reloading;
    frame_.reloadStartedThisTick = true;
    frame_.reloadAlpha = 0.0f;
    reloadElapsedSeconds_ = 0.0f;
}

void WeaponController::completeReload() noexcept {
    const std::uint32_t missing =
        config_.magazineSize -
        frame_.magazine;

    const std::uint32_t transferred =
        std::min(
            missing,
            frame_.reserve);

    frame_.magazine +=
        transferred;
    frame_.reserve -=
        transferred;

    frame_.phase =
        WeaponPhase::Ready;
    frame_.reloadAlpha = 0.0f;
    frame_.reloadCompletedThisTick = true;

    reloadElapsedSeconds_ = 0.0f;
}

bool WeaponController::wantsShot(
    const WeaponInput& input) const noexcept {
    return config_.automatic
        ? input.fireHeld
        : input.firePressed;
}

} // namespace xziel
