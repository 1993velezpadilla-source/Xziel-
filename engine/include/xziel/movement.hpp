#pragma once

#include "xziel/engine.hpp"

#include <cstdint>

namespace xziel {

enum class MovementMode : std::uint8_t {
    Grounded,
    Sprinting,
    Crouched,
    Sliding,
    Diving,
    Airborne,
    WallRunning,
    Mantling,
};

enum class MovementCue : std::uint8_t {
    None,
    Jump,
    DoubleJump,
    SlideStart,
    DiveStart,
    WallRunStart,
    WallJump,
    MantleStart,
    Land,
};

struct MovementCapabilities {
    bool sprint = true;
    bool tacticalSprint = true;
    bool crouch = true;
    bool slide = true;
    bool dolphinDive = true;
    bool slideCancel = true;
    bool mantle = true;

    // Advanced traversal is supported by the engine but can be disabled by a
    // classic Zombies ruleset or by maps that were not authored for it.
    bool doubleJump = false;
    bool wallRun = false;
    bool wallJump = false;
};

struct MovementConfig {
    float walkSpeed = 4.4f;
    float sprintSpeed = 6.4f;
    float tacticalSprintSpeed = 7.2f;
    float crouchSpeed = 2.5f;

    float groundAcceleration = 42.0f;
    float airAcceleration = 8.0f;
    float groundFriction = 36.0f;

    float jumpVelocity = 5.4f;
    float doubleJumpVelocity = 5.0f;
    float gravity = 18.0f;

    // Short forgiveness windows keep touch input responsive without changing
    // the map's actual collision geometry.
    float coyoteTimeSeconds = 0.10f;
    float jumpBufferSeconds = 0.12f;

    float slideEntrySpeed = 6.8f;
    float slideExitSpeed = 3.0f;
    float slideDurationSeconds = 0.78f;

    float diveForwardSpeed = 6.6f;
    float diveVerticalVelocity = 3.4f;
    float diveRecoverySeconds = 0.62f;

    float wallRunSpeed = 6.8f;
    float wallRunGravityScale = 0.28f;
    float wallRunDurationSeconds = 1.35f;
    float wallJumpVerticalVelocity = 5.0f;
    float wallJumpPush = 3.4f;

    float mantleDurationSeconds = 0.36f;
    float mantleForwardSpeed = 2.8f;
    float mantleVerticalSpeed = 2.6f;

    float autoSprintThreshold = 0.88f;
    float tacticalSprintThreshold = 0.97f;
};

struct MovementInput {
    Vec2 move{};

    bool sprintRequested = false;
    bool tacticalSprintRequested = false;

    bool jumpPressed = false;
    bool jumpHeld = false;

    bool crouchPressed = false;
    bool crouchHeld = false;

    bool diveRequested = false;
    bool slideRequested = false;
    bool cancelMovementAction = false;
};

struct TraversalContext {
    bool grounded = true;
    bool mantleAvailable = false;

    bool wallRunnable = false;
    bool wallOnLeft = false;
    bool wallOnRight = false;

    // World-space wall normal projected onto X/Z. Used only for wall-jump push.
    Vec2 wallNormal{};
};

struct MovementFrame {
    MovementMode mode = MovementMode::Grounded;
    MovementCue cue = MovementCue::None;
    Vec3 velocity{};

    bool canAim = true;
    bool canFire = true;
    bool canReload = true;

    // Animation/camera consumers can use these without knowing movement rules.
    float cameraRollHint = 0.0f;
    float cameraHeightBlend = 1.0f;
    float viewmodelLowering = 0.0f;
};

class MovementController final {
public:
    MovementController(
        MovementConfig config = {},
        MovementCapabilities capabilities = {});

    void reset() noexcept;

    [[nodiscard]] MovementFrame step(
        const MovementInput& input,
        const TraversalContext& traversal,
        float deltaSeconds) noexcept;

    [[nodiscard]] const MovementFrame& frame() const noexcept;
    [[nodiscard]] const MovementConfig& config() const noexcept;
    [[nodiscard]] const MovementCapabilities& capabilities() const noexcept;

    void setCapabilities(MovementCapabilities capabilities) noexcept;

private:
    void setMode(MovementMode mode, MovementCue cue) noexcept;
    void accelerateHorizontal(
        const Vec2& move,
        float targetSpeed,
        float acceleration,
        float dt) noexcept;
    void applyHorizontalFriction(float friction, float dt) noexcept;

    MovementConfig config_{};
    MovementCapabilities capabilities_{};
    MovementFrame frame_{};

    float stateSeconds_ = 0.0f;
    float coyoteSecondsRemaining_ = 0.0f;
    float jumpBufferSecondsRemaining_ = 0.0f;

    bool usedDoubleJump_ = false;
    bool wasGrounded_ = true;
};

} // namespace xziel
