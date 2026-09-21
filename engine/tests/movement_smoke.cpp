#include "xziel/mobile_controls.hpp"
#include "xziel/movement.hpp"

#include <cassert>

int main() {
    xziel::MovementCapabilities capabilities{};
    capabilities.doubleJump = true;
    capabilities.wallRun = true;
    capabilities.wallJump = true;

    xziel::MovementController movement({}, capabilities);
    xziel::MobileMovementResolver mobile;

    xziel::TraversalContext traversal{};
    traversal.grounded = true;

    // Full-forward joystick auto-sprints without a dedicated sprint button.
    xziel::MobileMovementButtons buttons{};
    auto input = mobile.resolve(
        {0.0f, 1.0f},
        buttons,
        traversal,
        movement.frame().mode);

    auto frame = movement.step(input, traversal, 1.0f / 120.0f);
    assert(frame.mode == xziel::MovementMode::Sprinting);

    // Tap the one stance button while moving fast -> slide.
    for (int i = 0; i < 60; ++i) {
        input = mobile.resolve(
            {0.0f, 1.0f},
            {},
            traversal,
            movement.frame().mode);
        frame = movement.step(input, traversal, 1.0f / 120.0f);
    }

    buttons = {};
    buttons.stancePressed = true;
    input = mobile.resolve(
        {0.0f, 1.0f},
        buttons,
        traversal,
        movement.frame().mode);
    frame = movement.step(input, traversal, 1.0f / 120.0f);
    assert(frame.mode == xziel::MovementMode::Sliding);
    assert(frame.cue == xziel::MovementCue::SlideStart);

    // Jump is also slide-cancel: no extra touchscreen button.
    buttons = {};
    buttons.jumpPressed = true;
    buttons.movementCancelGesture = true;
    input = mobile.resolve(
        {0.0f, 1.0f},
        buttons,
        traversal,
        movement.frame().mode);
    frame = movement.step(input, traversal, 1.0f / 120.0f);
    assert(frame.mode != xziel::MovementMode::Sliding);

    // Hold the same stance button during sprint -> dolphin dive.
    movement.reset();
    for (int i = 0; i < 80; ++i) {
        input = mobile.resolve(
            {0.0f, 1.0f},
            {},
            traversal,
            movement.frame().mode);
        frame = movement.step(input, traversal, 1.0f / 120.0f);
    }

    buttons = {};
    buttons.stanceHeld = true;
    buttons.stanceHeldSeconds = 0.30f;
    input = mobile.resolve(
        {0.0f, 1.0f},
        buttons,
        traversal,
        movement.frame().mode);
    frame = movement.step(input, traversal, 1.0f / 120.0f);
    assert(frame.mode == xziel::MovementMode::Diving);
    assert(frame.cue == xziel::MovementCue::DiveStart);
    assert(!frame.canAim);

    // Jump then jump again in air -> optional double-jump.
    movement.reset();
    buttons = {};
    buttons.jumpPressed = true;
    input = mobile.resolve(
        {0.0f, 0.8f},
        buttons,
        traversal,
        movement.frame().mode);
    frame = movement.step(input, traversal, 1.0f / 120.0f);
    assert(frame.mode == xziel::MovementMode::Airborne);
    assert(frame.cue == xziel::MovementCue::Jump);

    traversal.grounded = false;
    buttons = {};
    buttons.jumpPressed = true;
    input = mobile.resolve(
        {0.0f, 0.8f},
        buttons,
        traversal,
        movement.frame().mode);
    frame = movement.step(input, traversal, 1.0f / 120.0f);
    assert(frame.cue == xziel::MovementCue::DoubleJump);

    // Coyote time accepts a jump a few ticks after ground contact is lost,
    // which matters on touchscreens where a thumb can land slightly late.
    movement.reset();

    traversal = {};
    traversal.grounded = true;

    frame = movement.step(
        {},
        traversal,
        1.0f / 120.0f);

    traversal.grounded = false;

    xziel::MovementInput lateJump{};
    lateJump.jumpPressed = true;

    frame = movement.step(
        lateJump,
        traversal,
        1.0f / 120.0f);

    assert(
        frame.mode ==
        xziel::MovementMode::Airborne);

    assert(
        frame.cue ==
        xziel::MovementCue::Jump);

    // Jump buffering remembers an early press and fires it on the landing
    // tick instead of eating the input.
    movement.reset();

    traversal = {};
    traversal.grounded = false;

    xziel::MovementInput buffered{};
    buffered.jumpPressed = true;

    frame = movement.step(
        buffered,
        traversal,
        1.0f / 120.0f);

    buffered.jumpPressed = false;
    traversal.grounded = true;

    frame = movement.step(
        buffered,
        traversal,
        1.0f / 120.0f);

    assert(
        frame.mode ==
        xziel::MovementMode::Airborne);

    assert(
        frame.cue ==
        xziel::MovementCue::Jump);

    // Approaching a runnable wall needs no wall-run button.
    traversal.wallRunnable = true;
    traversal.wallOnRight = true;
    buttons = {};
    input = mobile.resolve(
        {0.0f, 1.0f},
        buttons,
        traversal,
        movement.frame().mode);
    frame = movement.step(input, traversal, 1.0f / 120.0f);
    assert(frame.mode == xziel::MovementMode::WallRunning);
    assert(frame.cue == xziel::MovementCue::WallRunStart);

    return 0;
}
