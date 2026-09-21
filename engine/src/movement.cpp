#include "xziel/movement.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float clampUnit(float value) noexcept {
    return std::clamp(value, -1.0f, 1.0f);
}

float length2(const Vec2& value) noexcept {
    return std::sqrt(value.x * value.x + value.y * value.y);
}

Vec2 normalizedOrZero(Vec2 value) noexcept {
    const float len = length2(value);
    if (len <= 0.0001f) {
        return {};
    }
    value.x /= len;
    value.y /= len;
    return value;
}

float moveToward(float current, float target, float maxDelta) noexcept {
    if (current < target) {
        return std::min(current + maxDelta, target);
    }
    return std::max(current - maxDelta, target);
}

} // namespace

MovementController::MovementController(
    MovementConfig config,
    MovementCapabilities capabilities)
    : config_(config),
      capabilities_(capabilities) {
    reset();
}

void MovementController::reset() noexcept {
    frame_ = {};
    frame_.mode = MovementMode::Grounded;
    stateSeconds_ = 0.0f;
    coyoteSecondsRemaining_ = 0.0f;
    jumpBufferSecondsRemaining_ = 0.0f;
    usedDoubleJump_ = false;
    wasGrounded_ = true;
}

MovementFrame MovementController::step(
    const MovementInput& input,
    const TraversalContext& traversal,
    float deltaSeconds) noexcept {
    const float dt = std::clamp(deltaSeconds, 0.0f, 0.05f);
    frame_.cue = MovementCue::None;
    frame_.cameraRollHint = 0.0f;
    frame_.cameraHeightBlend = 1.0f;
    frame_.viewmodelLowering = 0.0f;
    frame_.canAim = true;
    frame_.canFire = true;
    frame_.canReload = true;
    stateSeconds_ += dt;

    if (traversal.grounded) {
        coyoteSecondsRemaining_ =
            std::max(
                0.0f,
                config_.coyoteTimeSeconds);
    } else {
        coyoteSecondsRemaining_ =
            std::max(
                0.0f,
                coyoteSecondsRemaining_ -
                    dt);
    }

    if (input.jumpPressed) {
        jumpBufferSecondsRemaining_ =
            std::max(
                0.0f,
                config_.jumpBufferSeconds);
    } else {
        jumpBufferSecondsRemaining_ =
            std::max(
                0.0f,
                jumpBufferSecondsRemaining_ -
                    dt);
    }

    const bool jumpRequested =
        input.jumpPressed ||
        jumpBufferSecondsRemaining_ > 0.0f;

    const bool landed = traversal.grounded && !wasGrounded_;
    if (landed) {
        frame_.cue = MovementCue::Land;
        usedDoubleJump_ = false;
        if (frame_.mode == MovementMode::Airborne ||
            frame_.mode == MovementMode::WallRunning ||
            frame_.mode == MovementMode::Diving) {
            setMode(MovementMode::Grounded, MovementCue::Land);
        }
    }

    Vec2 move{clampUnit(input.move.x), clampUnit(input.move.y)};
    const float moveMagnitude = std::min(length2(move), 1.0f);
    const Vec2 direction = normalizedOrZero(move);

    // Mantle wins over jump when the geometry says a ledge is available.
    if (capabilities_.mantle &&
        traversal.mantleAvailable &&
        jumpRequested &&
        frame_.mode != MovementMode::Sliding &&
        frame_.mode != MovementMode::Diving) {
        setMode(MovementMode::Mantling, MovementCue::MantleStart);
    }

    // One stance action can become slide or dive depending on the mobile
    // gesture resolver. No dedicated slide/dive buttons are required.
    const bool movingFast =
        std::sqrt(frame_.velocity.x * frame_.velocity.x +
                  frame_.velocity.z * frame_.velocity.z) >=
        config_.slideExitSpeed;

    if (traversal.grounded &&
        capabilities_.dolphinDive &&
        input.diveRequested &&
        movingFast) {
        setMode(MovementMode::Diving, MovementCue::DiveStart);
        frame_.velocity.x = direction.x * config_.diveForwardSpeed;
        frame_.velocity.z = direction.y * config_.diveForwardSpeed;
        frame_.velocity.y = config_.diveVerticalVelocity;
    } else if (traversal.grounded &&
               capabilities_.slide &&
               input.slideRequested &&
               movingFast) {
        setMode(MovementMode::Sliding, MovementCue::SlideStart);
        const float speed = std::max(
            config_.slideEntrySpeed,
            std::sqrt(frame_.velocity.x * frame_.velocity.x +
                      frame_.velocity.z * frame_.velocity.z));
        frame_.velocity.x = direction.x * speed;
        frame_.velocity.z = direction.y * speed;
    }

    switch (frame_.mode) {
        case MovementMode::Mantling: {
            frame_.canAim = false;
            frame_.canReload = false;
            frame_.viewmodelLowering = 0.65f;
            frame_.velocity.x = direction.x * config_.mantleForwardSpeed;
            frame_.velocity.z = direction.y * config_.mantleForwardSpeed;
            frame_.velocity.y = config_.mantleVerticalSpeed;

            if (stateSeconds_ >= config_.mantleDurationSeconds) {
                setMode(
                    traversal.grounded ? MovementMode::Grounded
                                       : MovementMode::Airborne,
                    MovementCue::None);
            }
            break;
        }

        case MovementMode::Sliding: {
            frame_.cameraHeightBlend = 0.58f;
            frame_.viewmodelLowering = 0.16f;

            const float speed = std::sqrt(
                frame_.velocity.x * frame_.velocity.x +
                frame_.velocity.z * frame_.velocity.z);
            const float nextSpeed = moveToward(
                speed,
                config_.slideExitSpeed,
                (config_.slideEntrySpeed - config_.slideExitSpeed) *
                    dt / std::max(config_.slideDurationSeconds, 0.01f));
            const Vec2 velocityDir = speed > 0.001f
                ? normalizedOrZero({frame_.velocity.x, frame_.velocity.z})
                : direction;
            frame_.velocity.x = velocityDir.x * nextSpeed;
            frame_.velocity.z = velocityDir.y * nextSpeed;

            if ((capabilities_.slideCancel && input.cancelMovementAction) ||
                stateSeconds_ >= config_.slideDurationSeconds ||
                !traversal.grounded) {
                setMode(
                    traversal.grounded ? MovementMode::Crouched
                                       : MovementMode::Airborne,
                    MovementCue::None);
            }
            break;
        }

        case MovementMode::Diving: {
            frame_.cameraHeightBlend = 0.42f;
            frame_.viewmodelLowering = 0.42f;
            frame_.canAim = false;
            frame_.canReload = false;
            frame_.velocity.y -= config_.gravity * dt;

            if (traversal.grounded &&
                stateSeconds_ >= config_.diveRecoverySeconds) {
                setMode(MovementMode::Crouched, MovementCue::None);
            }
            break;
        }

        case MovementMode::WallRunning: {
            frame_.cameraRollHint =
                traversal.wallOnLeft ? -7.0f :
                traversal.wallOnRight ? 7.0f : 0.0f;
            frame_.velocity.y -= config_.gravity *
                config_.wallRunGravityScale * dt;
            accelerateHorizontal(
                move,
                config_.wallRunSpeed,
                config_.airAcceleration,
                dt);

            if (jumpRequested && capabilities_.wallJump) {
                jumpBufferSecondsRemaining_ = 0.0f;
                coyoteSecondsRemaining_ = 0.0f;

                setMode(MovementMode::Airborne, MovementCue::WallJump);
                frame_.velocity.y = config_.wallJumpVerticalVelocity;
                frame_.velocity.x +=
                    traversal.wallNormal.x * config_.wallJumpPush;
                frame_.velocity.z +=
                    traversal.wallNormal.y * config_.wallJumpPush;
            } else if (!traversal.wallRunnable ||
                       traversal.grounded ||
                       stateSeconds_ >= config_.wallRunDurationSeconds) {
                setMode(MovementMode::Airborne, MovementCue::None);
            }
            break;
        }

        case MovementMode::Airborne: {
            accelerateHorizontal(
                move,
                config_.sprintSpeed,
                config_.airAcceleration,
                dt);
            frame_.velocity.y -= config_.gravity * dt;

            if (capabilities_.wallRun &&
                traversal.wallRunnable &&
                moveMagnitude > 0.45f) {
                setMode(MovementMode::WallRunning, MovementCue::WallRunStart);
            } else if (jumpRequested &&
                       coyoteSecondsRemaining_ > 0.0f) {
                jumpBufferSecondsRemaining_ = 0.0f;
                coyoteSecondsRemaining_ = 0.0f;

                frame_.velocity.y =
                    config_.jumpVelocity;
                frame_.cue =
                    MovementCue::Jump;
            } else if (jumpRequested &&
                       capabilities_.doubleJump &&
                       !usedDoubleJump_) {
                jumpBufferSecondsRemaining_ = 0.0f;
                usedDoubleJump_ = true;
                frame_.velocity.y = config_.doubleJumpVelocity;
                frame_.cue = MovementCue::DoubleJump;
            }
            break;
        }

        case MovementMode::Crouched:
        case MovementMode::Grounded:
        case MovementMode::Sprinting: {
            if (!traversal.grounded) {
                if (jumpRequested &&
                    coyoteSecondsRemaining_ > 0.0f) {
                    jumpBufferSecondsRemaining_ = 0.0f;
                    coyoteSecondsRemaining_ = 0.0f;

                    setMode(
                        MovementMode::Airborne,
                        MovementCue::Jump);

                    frame_.velocity.y =
                        config_.jumpVelocity;
                } else {
                    setMode(
                        MovementMode::Airborne,
                        MovementCue::None);
                }

                break;
            }

            if (jumpRequested) {
                jumpBufferSecondsRemaining_ = 0.0f;
                coyoteSecondsRemaining_ = 0.0f;

                setMode(
                    MovementMode::Airborne,
                    MovementCue::Jump);

                frame_.velocity.y =
                    config_.jumpVelocity;

                break;
            }

            const bool wantsCrouch =
                capabilities_.crouch &&
                (input.crouchHeld || input.crouchPressed);
            const bool wantsTacticalSprint =
                capabilities_.tacticalSprint &&
                input.tacticalSprintRequested;
            const bool wantsSprint =
                capabilities_.sprint &&
                (input.sprintRequested ||
                 moveMagnitude >= config_.autoSprintThreshold);

            float speed = config_.walkSpeed;
            if (wantsCrouch) {
                setMode(MovementMode::Crouched, MovementCue::None);
                speed = config_.crouchSpeed;
                frame_.cameraHeightBlend = 0.68f;
            } else if (wantsTacticalSprint &&
                       moveMagnitude >= config_.tacticalSprintThreshold) {
                setMode(MovementMode::Sprinting, MovementCue::None);
                speed = config_.tacticalSprintSpeed;
                frame_.viewmodelLowering = 0.20f;
            } else if (wantsSprint) {
                setMode(MovementMode::Sprinting, MovementCue::None);
                speed = config_.sprintSpeed;
                frame_.viewmodelLowering = 0.10f;
            } else {
                setMode(MovementMode::Grounded, MovementCue::None);
            }

            accelerateHorizontal(
                move,
                speed,
                config_.groundAcceleration,
                dt);
            if (moveMagnitude < 0.05f) {
                applyHorizontalFriction(config_.groundFriction, dt);
            }
            frame_.velocity.y = 0.0f;
            break;
        }
    }

    wasGrounded_ = traversal.grounded;
    return frame_;
}

const MovementFrame& MovementController::frame() const noexcept {
    return frame_;
}

const MovementConfig& MovementController::config() const noexcept {
    return config_;
}

const MovementCapabilities& MovementController::capabilities() const noexcept {
    return capabilities_;
}

void MovementController::setCapabilities(
    MovementCapabilities capabilities) noexcept {
    capabilities_ = capabilities;
}

void MovementController::setMode(
    MovementMode mode,
    MovementCue cue) noexcept {
    if (frame_.mode != mode) {
        stateSeconds_ = 0.0f;
    }
    frame_.mode = mode;
    if (cue != MovementCue::None) {
        frame_.cue = cue;
    }
}

void MovementController::accelerateHorizontal(
    const Vec2& move,
    float targetSpeed,
    float acceleration,
    float dt) noexcept {
    const Vec2 direction = normalizedOrZero(move);
    const float magnitude = std::min(length2(move), 1.0f);
    const float targetX = direction.x * targetSpeed * magnitude;
    const float targetZ = direction.y * targetSpeed * magnitude;

    frame_.velocity.x =
        moveToward(frame_.velocity.x, targetX, acceleration * dt);
    frame_.velocity.z =
        moveToward(frame_.velocity.z, targetZ, acceleration * dt);
}

void MovementController::applyHorizontalFriction(
    float friction,
    float dt) noexcept {
    frame_.velocity.x = moveToward(
        frame_.velocity.x,
        0.0f,
        friction * dt);
    frame_.velocity.z = moveToward(
        frame_.velocity.z,
        0.0f,
        friction * dt);
}

} // namespace xziel
