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

void FpsPlayerController::setSpawn(
    Vec3 feetPosition,
    float yawDegrees) noexcept {
    if (!std::isfinite(feetPosition.x) ||
        !std::isfinite(feetPosition.y) ||
        !std::isfinite(feetPosition.z)) {
        return;
    }

    movement_.reset();
    frame_.movement = movement_.frame();
    frame_.feetPosition = feetPosition;
    frame_.yawDegrees =
        std::isfinite(yawDegrees)
        ? std::remainder(yawDegrees, 360.0f)
        : 0.0f;
    frame_.pitchDegrees = 0.0f;

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

    updateCameraPosition();
}

bool FpsPlayerController::setHorizontalBounds(
    float minimumX,
    float maximumX,
    float minimumZ,
    float maximumZ) noexcept {
    if (!std::isfinite(minimumX) ||
        !std::isfinite(maximumX) ||
        !std::isfinite(minimumZ) ||
        !std::isfinite(maximumZ) ||
        minimumX >= maximumX ||
        minimumZ >= maximumZ) {
        return false;
    }

    config_.minX = minimumX;
    config_.maxX = maximumX;
    config_.minZ = minimumZ;
    config_.maxZ = maximumZ;

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

    updateCameraPosition();
    return true;
}

void FpsPlayerController::clearWalkableSurfaces() noexcept {
    walkableSurfaceCount_ = 0;
}

bool FpsPlayerController::addWalkableSurface(
    const Aabb& surface) noexcept {
    if (walkableSurfaceCount_ >=
            walkableSurfaces_.size() ||
        surface.minimum.x > surface.maximum.x ||
        surface.minimum.y > surface.maximum.y ||
        surface.minimum.z > surface.maximum.z ||
        !std::isfinite(surface.minimum.x) ||
        !std::isfinite(surface.minimum.y) ||
        !std::isfinite(surface.minimum.z) ||
        !std::isfinite(surface.maximum.x) ||
        !std::isfinite(surface.maximum.y) ||
        !std::isfinite(surface.maximum.z)) {
        return false;
    }

    walkableSurfaces_[
        walkableSurfaceCount_++] =
        surface;
    return true;
}

void FpsPlayerController::clearStaticObstacles() noexcept {
    staticObstacleCount_ = 0;
}

bool FpsPlayerController::addStaticObstacle(
    const Aabb& obstacle) noexcept {
    if (staticObstacleCount_ >=
        staticObstacles_.size()) {
        return false;
    }

    if (obstacle.minimum.x >
            obstacle.maximum.x ||
        obstacle.minimum.y >
            obstacle.maximum.y ||
        obstacle.minimum.z >
            obstacle.maximum.z) {
        return false;
    }

    staticObstacles_[
        staticObstacleCount_++] =
        obstacle;

    return true;
}

void FpsPlayerController::clearDynamicObstacles() noexcept {
    dynamicObstacleCount_ = 0;
}

bool FpsPlayerController::addDynamicObstacle(
    std::uint32_t id,
    const Aabb& obstacle,
    bool enabled) noexcept {
    if (id == 0 ||
        dynamicObstacleCount_ >= dynamicObstacles_.size() ||
        obstacle.minimum.x > obstacle.maximum.x ||
        obstacle.minimum.y > obstacle.maximum.y ||
        obstacle.minimum.z > obstacle.maximum.z) {
        return false;
    }

    for (std::size_t i = 0; i < dynamicObstacleCount_; ++i) {
        if (dynamicObstacles_[i].id == id) {
            return false;
        }
    }

    dynamicObstacles_[dynamicObstacleCount_++] = {
        id,
        obstacle,
        enabled,
    };
    return true;
}

bool FpsPlayerController::setDynamicObstacleEnabled(
    std::uint32_t id,
    bool enabled) noexcept {
    for (std::size_t i = 0; i < dynamicObstacleCount_; ++i) {
        if (dynamicObstacles_[i].id == id) {
            dynamicObstacles_[i].enabled = enabled;
            return true;
        }
    }
    return false;
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

    const Vec3 previousFeetPosition =
        frame_.feetPosition;

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

    resolveStaticCollision(
        previousFeetPosition);

    resolveWalkableSupport(
        previousFeetPosition);

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

    float supportY = 0.0f;
    const bool onWalkableSurface =
        findWalkableSupport(
            frame_.feetPosition.x,
            frame_.feetPosition.z,
            frame_.feetPosition.y,
            0.065f,
            0.065f,
            supportY) &&
        std::fabs(
            frame_.feetPosition.y -
            supportY) <= 0.065f;

    const bool atFloor =
        frame_.feetPosition.y <=
            config_.floorY + 0.002f ||
        onWalkableSurface;

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

    const float yaw =
        frame_.yawDegrees *
        kDegreesToRadians;

    const Vec2 forward{
        std::sin(yaw),
        std::cos(yaw),
    };

    const Vec2 right{
        std::cos(yaw),
        -std::sin(yaw),
    };

    const float playerX =
        frame_.feetPosition.x;

    const float playerZ =
        frame_.feetPosition.z;

    const float feetY =
        frame_.feetPosition.y;

    const float bodyTop =
        feetY +
        std::max(
            0.1f,
            config_.collisionHeight);

    const float mantleProbe =
        std::max(
            0.0f,
            config_.collisionRadius +
                config_.mantleProbeDistance);

    const float wallProbe =
        std::max(
            0.0f,
            config_.collisionRadius +
                config_.wallRunProbeDistance);

    float bestWallDistance =
        wallProbe +
        1.0f;

    const std::size_t traversalObstacleCount =
        staticObstacleCount_ + dynamicObstacleCount_;
    for (std::size_t i = 0;
         i < traversalObstacleCount;
         ++i) {
        const Aabb* obstaclePointer = nullptr;
        if (i < staticObstacleCount_) {
            obstaclePointer = &staticObstacles_[i];
        } else {
            const auto& dynamic =
                dynamicObstacles_[i - staticObstacleCount_];
            if (!dynamic.enabled) {
                continue;
            }
            obstaclePointer = &dynamic.obstacle;
        }
        const auto& obstacle = *obstaclePointer;

        const float nearestX =
            std::clamp(
                playerX,
                obstacle.minimum.x,
                obstacle.maximum.x);

        const float nearestZ =
            std::clamp(
                playerZ,
                obstacle.minimum.z,
                obstacle.maximum.z);

        const float deltaX =
            playerX -
            nearestX;

        const float deltaZ =
            playerZ -
            nearestZ;

        const float horizontalDistance =
            std::sqrt(
                deltaX * deltaX +
                deltaZ * deltaZ);

        if (traversal.grounded) {
            const float ledgeHeight =
                obstacle.maximum.y -
                feetY;

            if (ledgeHeight >=
                    config_.mantleMinimumHeight &&
                ledgeHeight <=
                    config_.mantleMaximumHeight) {
                const float centerX =
                    (obstacle.minimum.x +
                     obstacle.maximum.x) *
                    0.5f;

                const float centerZ =
                    (obstacle.minimum.z +
                     obstacle.maximum.z) *
                    0.5f;

                const float toObstacleX =
                    centerX -
                    playerX;

                const float toObstacleZ =
                    centerZ -
                    playerZ;

                const float forwardDistance =
                    toObstacleX *
                        forward.x +
                    toObstacleZ *
                        forward.y;

                const float sideDistance =
                    std::fabs(
                        toObstacleX *
                            right.x +
                        toObstacleZ *
                            right.y);

                const float obstacleHalfWidth =
                    std::max(
                        (obstacle.maximum.x -
                         obstacle.minimum.x) *
                            0.5f,
                        (obstacle.maximum.z -
                         obstacle.minimum.z) *
                            0.5f);

                if (forwardDistance > 0.0f &&
                    forwardDistance <=
                        mantleProbe &&
                    sideDistance <=
                        obstacleHalfWidth +
                        config_.collisionRadius) {
                    traversal.mantleAvailable =
                        true;
                }
            }
        }

        const bool verticallyRunnable =
            obstacle.maximum.y -
                obstacle.minimum.y >=
                    config_.
                        wallRunMinimumWallHeight &&
            bodyTop >
                obstacle.minimum.y &&
            feetY <
                obstacle.maximum.y;

        if (traversal.grounded ||
            !verticallyRunnable ||
            horizontalDistance >
                wallProbe ||
            horizontalDistance >=
                bestWallDistance) {
            continue;
        }

        Vec2 normal{};

        if (horizontalDistance >
            1.0e-5f) {
            const float inverseDistance =
                1.0f /
                horizontalDistance;

            normal = {
                deltaX *
                    inverseDistance,
                deltaZ *
                    inverseDistance,
            };
        } else {
            const float leftDistance =
                std::fabs(
                    playerX -
                    obstacle.minimum.x);

            const float rightDistance =
                std::fabs(
                    obstacle.maximum.x -
                    playerX);

            const float frontDistance =
                std::fabs(
                    playerZ -
                    obstacle.minimum.z);

            const float backDistance =
                std::fabs(
                    obstacle.maximum.z -
                    playerZ);

            const float nearestSide =
                std::min(
                    std::min(
                        leftDistance,
                        rightDistance),
                    std::min(
                        frontDistance,
                        backDistance));

            if (nearestSide ==
                leftDistance) {
                normal = {-1.0f, 0.0f};
            } else if (nearestSide ==
                       rightDistance) {
                normal = {1.0f, 0.0f};
            } else if (nearestSide ==
                       frontDistance) {
                normal = {0.0f, -1.0f};
            } else {
                normal = {0.0f, 1.0f};
            }
        }

        const float sideDot =
            normal.x *
                right.x +
            normal.y *
                right.y;

        traversal.wallRunnable = true;
        traversal.wallNormal =
            normal;

        traversal.wallOnLeft =
            sideDot >
            0.15f;

        traversal.wallOnRight =
            sideDot <
            -0.15f;

        bestWallDistance =
            horizontalDistance;
    }

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

bool FpsPlayerController::findWalkableSupport(
    float x,
    float z,
    float referenceFeetY,
    float maximumStepUp,
    float maximumStepDown,
    float& supportY) const noexcept {
    bool found = false;
    float best = -INFINITY;

    for (std::size_t i = 0;
         i < walkableSurfaceCount_;
         ++i) {
        const auto& surface =
            walkableSurfaces_[i];

        if (x < surface.minimum.x ||
            x > surface.maximum.x ||
            z < surface.minimum.z ||
            z > surface.maximum.z) {
            continue;
        }

        const float top =
            surface.maximum.y;

        if (top >
                referenceFeetY +
                    maximumStepUp ||
            top <
                referenceFeetY -
                    maximumStepDown) {
            continue;
        }

        if (!found || top > best) {
            best = top;
            found = true;
        }
    }

    if (found) {
        supportY = best;
    }
    return found;
}

void FpsPlayerController::resolveWalkableSupport(
    const Vec3& previousFeetPosition) noexcept {
    if (walkableSurfaceCount_ == 0U ||
        frame_.movement.velocity.y > 0.001f) {
        return;
    }

    constexpr float kMaximumStepUp = 0.34f;
    constexpr float kMaximumStepDown = 0.34f;

    float supportY = 0.0f;
    if (findWalkableSupport(
            frame_.feetPosition.x,
            frame_.feetPosition.z,
            previousFeetPosition.y,
            kMaximumStepUp,
            kMaximumStepDown,
            supportY)) {
        frame_.feetPosition.y =
            supportY;
        frame_.movement.velocity.y =
            0.0f;
        return;
    }

    // Falling can cross a floor by much more than a normal walking step.
    // Choose the highest authored surface crossed this tick.
    bool landed = false;
    float landingY = -INFINITY;
    for (std::size_t i = 0;
         i < walkableSurfaceCount_;
         ++i) {
        const auto& surface =
            walkableSurfaces_[i];

        if (frame_.feetPosition.x <
                surface.minimum.x ||
            frame_.feetPosition.x >
                surface.maximum.x ||
            frame_.feetPosition.z <
                surface.minimum.z ||
            frame_.feetPosition.z >
                surface.maximum.z) {
            continue;
        }

        const float top =
            surface.maximum.y;

        if (previousFeetPosition.y + 0.002f >= top &&
            frame_.feetPosition.y <= top &&
            (!landed || top > landingY)) {
            landingY = top;
            landed = true;
        }
    }

    if (landed) {
        frame_.feetPosition.y =
            landingY;
        frame_.movement.velocity.y =
            0.0f;
    }
}

bool FpsPlayerController::overlapsObstacle(
    float x,
    float z,
    const Aabb& obstacle) const noexcept {
    const float radius =
        std::max(
            0.0f,
            config_.collisionRadius);

    const float playerBottom =
        frame_.feetPosition.y;

    const float playerTop =
        playerBottom +
        std::max(
            0.1f,
            config_.collisionHeight);

    const bool verticalOverlap =
        playerTop >
            obstacle.minimum.y &&
        playerBottom <
            obstacle.maximum.y;

    if (!verticalOverlap) {
        return false;
    }

    return x >
            obstacle.minimum.x -
                radius &&
        x <
            obstacle.maximum.x +
                radius &&
        z >
            obstacle.minimum.z -
                radius &&
        z <
            obstacle.maximum.z +
                radius;
}

void FpsPlayerController::resolveStaticCollision(
    const Vec3& previousFeetPosition) noexcept {
    if (staticObstacleCount_ == 0 &&
        dynamicObstacleCount_ == 0) {
        return;
    }

    float resolvedX =
        frame_.feetPosition.x;

    const float desiredZ =
        frame_.feetPosition.z;

    const std::size_t totalObstacleCount =
        staticObstacleCount_ + dynamicObstacleCount_;

    for (std::size_t i = 0;
         i < totalObstacleCount;
         ++i) {
        const Aabb* obstacle = nullptr;
        if (i < staticObstacleCount_) {
            obstacle = &staticObstacles_[i];
        } else {
            const auto& dynamic =
                dynamicObstacles_[i - staticObstacleCount_];
            if (!dynamic.enabled) {
                continue;
            }
            obstacle = &dynamic.obstacle;
        }
        if (overlapsObstacle(
                resolvedX,
                previousFeetPosition.z,
                *obstacle)) {
            resolvedX =
                previousFeetPosition.x;
            break;
        }
    }

    float resolvedZ =
        desiredZ;

    for (std::size_t i = 0;
         i < totalObstacleCount;
         ++i) {
        const Aabb* obstacle = nullptr;
        if (i < staticObstacleCount_) {
            obstacle = &staticObstacles_[i];
        } else {
            const auto& dynamic =
                dynamicObstacles_[i - staticObstacleCount_];
            if (!dynamic.enabled) {
                continue;
            }
            obstacle = &dynamic.obstacle;
        }
        if (overlapsObstacle(
                resolvedX,
                resolvedZ,
                *obstacle)) {
            resolvedZ =
                previousFeetPosition.z;
            break;
        }
    }

    frame_.feetPosition.x =
        resolvedX;

    frame_.feetPosition.z =
        resolvedZ;
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
