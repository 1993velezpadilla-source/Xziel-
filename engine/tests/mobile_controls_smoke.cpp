#include "xziel/mobile_controls.hpp"

#include <cassert>
#include <cmath>

namespace {

bool near(float a, float b, float epsilon = 0.002f) {
    return std::fabs(a - b) <= epsilon;
}

} // namespace

int main() {
    constexpr float radius = 100.0f;
    constexpr float deadzone = 0.10f;

    const auto center =
        xziel::resolveMobileJoystick(
            500.0f, 500.0f,
            500.0f, 500.0f,
            radius,
            deadzone);

    assert(near(center.x, 0.0f));
    assert(near(center.y, 0.0f));

    const auto insideDeadzone =
        xziel::resolveMobileJoystick(
            509.0f, 500.0f,
            500.0f, 500.0f,
            radius,
            deadzone);

    assert(near(insideDeadzone.x, 0.0f));
    assert(near(insideDeadzone.y, 0.0f));

    const auto justOutside =
        xziel::resolveMobileJoystick(
            511.0f, 500.0f,
            500.0f, 500.0f,
            radius,
            deadzone);

    // Crossing the deadzone must be continuous, not an instant ~11% impulse.
    assert(justOutside.x > 0.0f);
    assert(justOutside.x < 0.02f);
    assert(near(justOutside.y, 0.0f));

    const auto halfRight =
        xziel::resolveMobileJoystick(
            550.0f, 500.0f,
            500.0f, 500.0f,
            radius,
            deadzone);

    assert(near(halfRight.x, (0.50f - deadzone) / (1.0f - deadzone)));
    assert(near(halfRight.y, 0.0f));

    const auto fullForward =
        xziel::resolveMobileJoystick(
            500.0f, 400.0f,
            500.0f, 500.0f,
            radius,
            deadzone);

    assert(near(fullForward.x, 0.0f));
    assert(near(fullForward.y, 1.0f));

    const auto beyondDiagonal =
        xziel::resolveMobileJoystick(
            650.0f, 350.0f,
            500.0f, 500.0f,
            radius,
            deadzone);

    const float diagonalMagnitude =
        std::sqrt(
            beyondDiagonal.x * beyondDiagonal.x +
            beyondDiagonal.y * beyondDiagonal.y);

    assert(near(diagonalMagnitude, 1.0f));
    assert(beyondDiagonal.x > 0.70f);
    assert(beyondDiagonal.y > 0.70f);

    return 0;
}
