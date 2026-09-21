#pragma once

#include "xziel/mobile_controls.hpp"
#include "xziel/hitscan.hpp"

#include <array>
#include <cstddef>

namespace xziel {

struct FpsPlayerConfig {
    float touchYawDegreesPerScreen = 245.0f;
    float touchPitchDegreesPerScreen = 190.0f;
    float gyroSensitivity = 1.0f;

    float minimumPitchDegrees = -82.0f;
    float maximumPitchDegrees = 82.0f;

    float floorY = -1.48f;
    float standingEyeHeight = 1.62f;
    float collisionRadius = 0.28f;
    float collisionHeight = 1.78f;

    float minX = -2.78f;
    float maxX = 2.78f;
    float minZ = -3.35f;
    float maxZ = 3.35f;
};

struct FpsPlayerFrame {
    Vec3 feetPosition{
        0.0f,
        -1.48f,
        -2.55f,
    };

    Vec3 cameraPosition{
        0.0f,
        0.14f,
        -2.55f,
    };

    float yawDegrees = 0.0f;
    float pitchDegrees = 0.0f;

    MovementFrame movement{};
};

class FpsPlayerController final {
public:
    explicit FpsPlayerController(
        FpsPlayerConfig config = {},
        MobileControlConfig mobileConfig = {},
        MovementConfig movementConfig = {},
        MovementCapabilities capabilities = {});

    void reset() noexcept;

    void clearStaticObstacles() noexcept;

    [[nodiscard]] bool addStaticObstacle(
        const Aabb& obstacle) noexcept;

    // Touch look is a frame-relative delta and is consumed exactly once here.
    // Gyro is angular velocity and is integrated by frame delta.
    void sampleViewInput(
        const InputState& input,
        float frameDeltaSeconds) noexcept;

    // Movement advances at the engine fixed tick. The mobile resolver keeps
    // the HUD simple: joystick + Jump/Mantle + contextual Stance.
    [[nodiscard]] FpsPlayerFrame fixedStep(
        Vec2 localMove,
        const MobileMovementButtons& buttons,
        float fixedDeltaSeconds) noexcept;

    [[nodiscard]] const FpsPlayerFrame& frame() const noexcept;

private:
    [[nodiscard]] TraversalContext
    buildTraversalContext() const noexcept;

    [[nodiscard]] Vec2 localToWorldMove(
        Vec2 local) const noexcept;

    void updateCameraPosition() noexcept;

    void resolveStaticCollision(
        const Vec3& previousFeetPosition) noexcept;

    [[nodiscard]] bool overlapsObstacle(
        float x,
        float z,
        const Aabb& obstacle) const noexcept;

    static constexpr std::size_t
        kMaximumStaticObstacles = 16;

    FpsPlayerConfig config_{};
    MobileMovementResolver mobileResolver_{};
    MovementController movement_{};
    FpsPlayerFrame frame_{};

    std::array<Aabb, kMaximumStaticObstacles>
        staticObstacles_{};

    std::size_t staticObstacleCount_ = 0;
};

} // namespace xziel
