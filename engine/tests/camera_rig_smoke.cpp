#include "xziel/camera_rig.hpp"

#include <cassert>

int main() {
    xziel::CameraRig rig;

    xziel::MovementFrame movement{};
    movement.mode = xziel::MovementMode::Sprinting;
    movement.viewmodelLowering = 0.20f;

    xziel::HorrorFrame horror{};
    horror.cameraBreathing = 0.12f;

    auto frame = rig.advance(
        {
            .moveSpeedNormalized = 1.0f,
            .stridePhase = 0.25f,
            .aiming = false,
            .reducedMotion = false,
            .weaponRecoilPitchImpulse = 3.0f,
            .weaponRecoilYawImpulse = 1.0f,
            .landingImpact = 0.0f,
        },
        movement,
        horror,
        1.0f / 120.0f);

    assert(frame.fovAddDegrees > 0.0f);
    assert(frame.viewmodelLowering == 0.20f);
    assert(frame.pitchDegrees <= 8.5f);
    assert(frame.yawDegrees <= 5.0f);

    // Accessibility reduced-motion mode keeps movement present but much smaller.
    auto reduced = rig.advance(
        {
            .moveSpeedNormalized = 1.0f,
            .stridePhase = 0.25f,
            .aiming = true,
            .reducedMotion = true,
        },
        movement,
        horror,
        1.0f / 120.0f);

    assert(reduced.positionBobX < frame.positionBobX);

    movement.mode = xziel::MovementMode::Diving;
    auto dive = rig.advance(
        {},
        movement,
        horror,
        1.0f / 120.0f);
    assert(dive.pitchDegrees < 0.0f);

    return 0;
}
