#pragma once

#include "xziel/movement.hpp"

namespace xziel {

struct MobileControlConfig {
    float autoSprintThreshold = 0.99f;
    float tacticalSprintThreshold = 0.985f;
    float diveHoldSeconds = 0.24f;

    bool autoSprint = true;
    bool autoTacticalSprint = false;
    bool autoWallRun = true;
    bool autoMantle = true;
};

struct MobileMovementButtons {
    // Physical layout target:
    // - left joystick
    // - one Jump/Mantle button
    // - one Stance button
    //
    // The stance button is contextual:
    // tap while sprinting -> slide
    // hold while sprinting -> dolphin dive
    // tap/hold otherwise -> crouch
    bool jumpPressed = false;
    bool jumpHeld = false;

    bool stancePressed = false;
    bool stanceHeld = false;
    float stanceHeldSeconds = 0.0f;

    // A second tap on Jump while sliding can be used as slide cancel without
    // adding a separate cancel button.
    bool movementCancelGesture = false;
};

class MobileMovementResolver final {
public:
    explicit MobileMovementResolver(MobileControlConfig config = {});

    [[nodiscard]] MovementInput resolve(
        Vec2 joystick,
        const MobileMovementButtons& buttons,
        const TraversalContext& traversal,
        MovementMode currentMode) const noexcept;

    [[nodiscard]] const MobileControlConfig& config() const noexcept;

private:
    MobileControlConfig config_{};
};

} // namespace xziel
