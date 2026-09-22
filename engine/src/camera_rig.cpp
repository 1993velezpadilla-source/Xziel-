#include "xziel/camera_rig.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float clamp01(float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

float decayTowardZero(
    float value,
    float amount) noexcept {
    if (value > 0.0f) {
        return std::max(0.0f, value - amount);
    }
    return std::min(0.0f, value + amount);
}

} // namespace

CameraRig::CameraRig(CameraRigConfig config)
    : config_(config) {}

void CameraRig::reset() noexcept {
    recoilPitch_ = 0.0f;
    recoilYaw_ = 0.0f;
    landingKick_ = 0.0f;
}

CameraRigFrame CameraRig::advance(
    const CameraRigInput& input,
    const MovementFrame& movement,
    const HorrorFrame& horror,
    float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) || deltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(deltaSeconds, 0.05f);

    recoilPitch_ = std::clamp(
        recoilPitch_ + input.weaponRecoilPitchImpulse,
        -config_.maxRecoilPitchDegrees,
        config_.maxRecoilPitchDegrees);

    recoilYaw_ = std::clamp(
        recoilYaw_ + input.weaponRecoilYawImpulse,
        -config_.maxRecoilYawDegrees,
        config_.maxRecoilYawDegrees);

    landingKick_ = std::clamp(
        landingKick_ +
            clamp01(input.landingImpact) *
            config_.maxLandingKickDegrees,
        0.0f,
        config_.maxLandingKickDegrees);

    const float recoilDecay =
        config_.recoilReturnPerSecond * dt;

    CameraRigFrame out{};

    float motionScale =
        input.reducedMotion
        ? config_.reducedMotionScale
        : 1.0f;

    if (input.aiming) {
        motionScale *= config_.adsMotionScale;
    }

    const float speed =
        clamp01(input.moveSpeedNormalized);

    float bobScale =
        config_.bobAmplitude *
        speed *
        motionScale;

    if (movement.mode == MovementMode::Sprinting) {
        bobScale *= config_.sprintBobScale;
    }

    const float phase =
        input.stridePhase * 6.28318530718f;

    out.positionBobX =
        std::sin(phase) * bobScale;
    out.positionBobY =
        std::fabs(std::cos(phase)) * bobScale * 0.72f;

    out.pitchDegrees =
        recoilPitch_ -
        landingKick_ * motionScale;

    out.yawDegrees =
        recoilYaw_;

    out.rollDegrees =
        movement.cameraRollHint * motionScale;

    if (movement.mode == MovementMode::Sliding) {
        out.pitchDegrees -=
            config_.maxSlidePitchDegrees *
            0.48f *
            motionScale;
    } else if (movement.mode == MovementMode::Diving) {
        out.pitchDegrees -=
            config_.maxDivePitchDegrees *
            0.72f *
            motionScale;
    }

    // Horror breathing is intentionally tiny and cannot steal aim control.
    out.pitchDegrees +=
        std::sin(phase * 0.23f) *
        horror.cameraBreathing *
        0.55f *
        motionScale;

    if (movement.mode == MovementMode::Sprinting) {
        out.fovAddDegrees = 3.5f * motionScale;
    } else if (movement.mode == MovementMode::WallRunning) {
        out.fovAddDegrees = 2.5f * motionScale;
    }

    out.viewmodelLowering =
        movement.viewmodelLowering;

    recoilPitch_ =
        decayTowardZero(recoilPitch_, recoilDecay);
    recoilYaw_ =
        decayTowardZero(recoilYaw_, recoilDecay);
    landingKick_ =
        decayTowardZero(
            landingKick_,
            config_.maxLandingKickDegrees * 5.0f * dt);

    return out;
}

} // namespace xziel
