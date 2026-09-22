#include "xziel/mobile_controls.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float magnitude(Vec2 value) noexcept {
    return std::sqrt(value.x * value.x + value.y * value.y);
}

} // namespace

MobileMovementResolver::MobileMovementResolver(MobileControlConfig config)
    : config_(config) {}

MovementInput MobileMovementResolver::resolve(
    Vec2 joystick,
    const MobileMovementButtons& buttons,
    const TraversalContext& traversal,
    MovementMode currentMode) const noexcept {
    joystick.x = std::clamp(joystick.x, -1.0f, 1.0f);
    joystick.y = std::clamp(joystick.y, -1.0f, 1.0f);

    const float stickMagnitude = std::min(magnitude(joystick), 1.0f);
    const bool forwardIntent = joystick.y > 0.15f;
    const bool fastIntent =
        forwardIntent &&
        stickMagnitude >= config_.autoSprintThreshold;

    MovementInput out{};
    out.move = joystick;
    out.jumpPressed = buttons.jumpPressed;
    out.jumpHeld = buttons.jumpHeld;

    out.sprintRequested = config_.autoSprint && fastIntent;
    out.tacticalSprintRequested =
        config_.autoTacticalSprint &&
        forwardIntent &&
        stickMagnitude >= config_.tacticalSprintThreshold;

    const bool sprintLike =
        currentMode == MovementMode::Sprinting ||
        fastIntent;

    if (buttons.stancePressed || buttons.stanceHeld) {
        if (sprintLike) {
            if (buttons.stanceHeld &&
                buttons.stanceHeldSeconds >= config_.diveHoldSeconds) {
                out.diveRequested = true;
            } else if (buttons.stancePressed) {
                out.slideRequested = true;
            }
        } else {
            out.crouchPressed = buttons.stancePressed;
            out.crouchHeld = buttons.stanceHeld;
        }
    }

    out.cancelMovementAction =
        buttons.movementCancelGesture ||
        (currentMode == MovementMode::Sliding && buttons.jumpPressed);

    // Wall-running is deliberately automatic once the ruleset allows it and
    // the traversal probe confirms a runnable wall. No wall-run touchscreen
    // button is needed. Mantle is similarly mapped onto Jump.
    if (config_.autoWallRun &&
        traversal.wallRunnable &&
        !traversal.grounded &&
        stickMagnitude > 0.45f) {
        out.sprintRequested = true;
    }

    if (config_.autoMantle &&
        traversal.mantleAvailable &&
        buttons.jumpHeld) {
        out.jumpPressed = true;
    }

    return out;
}

const MobileControlConfig& MobileMovementResolver::config() const noexcept {
    return config_;
}

} // namespace xziel
