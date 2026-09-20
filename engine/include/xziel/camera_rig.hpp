#pragma once

#include "xziel/horror.hpp"
#include "xziel/movement.hpp"

namespace xziel {

struct CameraRigConfig {
    float bobAmplitude = 0.028f;
    float sprintBobScale = 1.45f;

    float maxRecoilPitchDegrees = 8.0f;
    float maxRecoilYawDegrees = 5.0f;
    float recoilReturnPerSecond = 22.0f;

    float maxLandingKickDegrees = 2.2f;
    float maxSlidePitchDegrees = 5.0f;
    float maxDivePitchDegrees = 11.0f;
    float maxWallRunRollDegrees = 8.0f;

    float adsMotionScale = 0.42f;
    float reducedMotionScale = 0.25f;
};

struct CameraRigInput {
    float moveSpeedNormalized = 0.0f;
    float stridePhase = 0.0f;

    bool aiming = false;
    bool reducedMotion = false;

    float weaponRecoilPitchImpulse = 0.0f;
    float weaponRecoilYawImpulse = 0.0f;
    float landingImpact = 0.0f;
};

struct CameraRigFrame {
    float positionBobX = 0.0f;
    float positionBobY = 0.0f;

    float pitchDegrees = 0.0f;
    float yawDegrees = 0.0f;
    float rollDegrees = 0.0f;

    float fovAddDegrees = 0.0f;
    float viewmodelLowering = 0.0f;
};

class CameraRig final {
public:
    explicit CameraRig(CameraRigConfig config = {});

    void reset() noexcept;

    [[nodiscard]] CameraRigFrame advance(
        const CameraRigInput& input,
        const MovementFrame& movement,
        const HorrorFrame& horror,
        float deltaSeconds) noexcept;

private:
    CameraRigConfig config_{};

    float recoilPitch_ = 0.0f;
    float recoilYaw_ = 0.0f;
    float landingKick_ = 0.0f;
};

} // namespace xziel
