#include "xziel/fps_player.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kRadiansToDegrees = 180.0f / kPi;
constexpr float kDegreesToRadians = kPi / 180.0f;

float finiteOrZero(float value) noexcept {
    return std::isfinite(value) ? value : 0.0f;
}

} // namespace

FpsPlayerController::FpsPlayerController(
    FpsPlayerConfig config,
    MobileControlConfig mobileConfig,
    MovementConfig movementConfig,
    MovementCapabilities capabilities)
    : config_(config),
      mobileResolver_(mobileConfig),
      movement_(
          movementConfig,
          capabilities) {
    reset();
}

void FpsPlayerController::reset() noexcept {
    movement_.reset();

    frame_ = {};
    frame_.feetPosition = {
        0.0f,
        config_.floorY,
        -2.55f,
    };
    frame_.yawDegrees = 0.0f;
    frame_.pitchDegrees = 0.0f;
    frame_.movement =
        movement_.frame();

    updateCameraPosition();
}

void FpsPlayerController::sampleViewInput(
    const InputState& input,
    float frameDeltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(frameDeltaSeconds) ||
         frameDeltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(
              frameDeltaSeconds,
              0.100f);

    const float touchX =
        finiteOrZero(input.look.x);

    const float touchY =
        finiteOrZero(input.look.y);

    frame_.yawDegrees +=
        touchX *
        config_.touchYawDegreesPerScreen;

    frame_.pitchDegrees +=
        touchY *
        config_.touchPitchDegreesPerScreen;

    const float gyroYaw =
        finiteOrZero(
            input.gyroRadiansPerSecond.y);

    const float gyroPitch =
        finiteOrZero(
            input.gyroRadiansPerSecond.x);

    frame_.yawDegrees +=
        gyroYaw *
        kRadiansToDegrees *
        config_.gyroSensitivity *
        dt;

    frame_.pitchDegrees +=
        gyroPitch *
        kRadiansToDegrees *
        config_.gyroSensitivity *
        dt;

    if (!std::isfinite(frame_.yawDegrees)) {
        frame_.yawDegrees = 0.0f;
    }

    frame_.yawDegrees =
        std::remainder(
            frame_.yawDegrees,
            360.0f);

    frame_.pitchDegrees =
        std::clamp(
            frame_.pitchDegrees,
            config_.minimumPitchDegrees,
            config_.maximumPitchDegrees);
}

FpsPlayerFrame FpsPlayerController::fixedStep(
    Vec2 localMove,
    const MobileMovementButtons& buttons,
    float fixedDeltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(fixedDeltaSeconds) ||
         fixedDeltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(
              fixedDeltaSeconds,
              0.05f);

    const TraversalContext traversal =
        buildTraversalContext();

    MovementInput movementInput =
        mobileResolver_.resolve(
            localMove,
            buttons,
            traversal,
            movement_.frame().mode);

    movementInput.move =
        localToWorldMove(
            movementInput.move);

    frame_.movement =
        movement_.step(
            movementInput,
            traversal,
            dt);

    frame_.feetPosition.x +=
        frame_.movement.velocity.x *
        dt;

    frame_.feetPosition.y +=
        frame_.movement.velocity.y *
        dt;

    frame_.feetPosition.z +=
        frame_.movement.velocity.z *
        dt;

    frame_.feetPosition.x =
        std::clamp(
            frame_.feetPosition.x,
            config_.minX,
            config_.maxX);

    frame_.feetPosition.z =
        std::clamp(
            frame_.feetPosition.z,
            config_.minZ,
            config_.maxZ);

    if (frame_.feetPosition.y <
        config_.floorY) {
        frame_.feetPosition.y =
            config_.floorY;
    }

    updateCameraPosition();

    return frame_;
}

const FpsPlayerFrame&
FpsPlayerController::frame() const noexcept {
    return frame_;
}

TraversalContext
FpsPlayerController::buildTraversalContext() const noexcept {
    TraversalContext traversal{};

    const auto& movementFrame =
        movement_.frame();

    const bool atFloor =
        frame_.feetPosition.y <=
        config_.floorY + 0.002f;

    const bool movingUp =
        movementFrame.velocity.y >
        0.001f;

    traversal.grounded =
        atFloor &&
        !movingUp;

    traversal.mantleAvailable = false;
    traversal.wallRunnable = false;
    traversal.wallOnLeft = false;
    traversal.wallOnRight = false;
    traversal.wallNormal = {};

    return traversal;
}

Vec2 FpsPlayerController::localToWorldMove(
    Vec2 local) const noexcept {
    local.x =
        std::clamp(
            finiteOrZero(local.x),
            -1.0f,
            1.0f);

    local.y =
        std::clamp(
            finiteOrZero(local.y),
            -1.0f,
            1.0f);

    const float yaw =
        frame_.yawDegrees *
        kDegreesToRadians;

    const float s =
        std::sin(yaw);
    const float c =
        std::cos(yaw);

    const Vec2 right{
        c,
        -s,
    };

    const Vec2 forward{
        s,
        c,
    };

    return {
        right.x * local.x +
            forward.x * local.y,
        right.y * local.x +
            forward.y * local.y,
    };
}

void FpsPlayerController::updateCameraPosition() noexcept {
    const float heightBlend =
        std::clamp(
            frame_.movement.cameraHeightBlend,
            0.35f,
            1.0f);

    frame_.cameraPosition = {
        frame_.feetPosition.x,
        frame_.feetPosition.y +
            config_.standingEyeHeight *
            heightBlend,
        frame_.feetPosition.z,
    };
}

} // namespace xziel
