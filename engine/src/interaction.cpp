#include "xziel/interaction.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float length3(Vec3 value) noexcept {
    return std::sqrt(
        value.x * value.x +
        value.y * value.y +
        value.z * value.z);
}

Vec3 normalizedOrForward(
    Vec3 value) noexcept {
    const float length =
        length3(value);

    if (!std::isfinite(length) ||
        length <= 1.0e-6f) {
        return {
            0.0f,
            0.0f,
            1.0f,
        };
    }

    const float inverse =
        1.0f / length;

    return {
        value.x * inverse,
        value.y * inverse,
        value.z * inverse,
    };
}

float dot3(
    Vec3 a,
    Vec3 b) noexcept {
    return
        a.x * b.x +
        a.y * b.y +
        a.z * b.z;
}

} // namespace

void InteractionSystem::reset() noexcept {
    frame_ = {};
    heldTargetId_ = 0;
    heldSeconds_ = 0.0f;
    previousHeld_ = false;
    activationLatched_ = false;
}

void InteractionSystem::clearTargets() noexcept {
    targetCount_ = 0;
    reset();
}

bool InteractionSystem::addTarget(
    const InteractionTarget& target) noexcept {
    if (targetCount_ >=
            targets_.size() ||
        target.id == 0 ||
        !std::isfinite(
            target.maximumDistance) ||
        target.maximumDistance <= 0.0f) {
        return false;
    }

    for (std::size_t i = 0;
         i < targetCount_;
         ++i) {
        if (targets_[i].id ==
            target.id) {
            return false;
        }
    }

    targets_[targetCount_++] =
        target;

    return true;
}

bool InteractionSystem::setTargetEnabled(
    std::uint32_t id,
    bool enabled) noexcept {
    for (std::size_t i = 0;
         i < targetCount_;
         ++i) {
        if (targets_[i].id != id) {
            continue;
        }

        targets_[i].enabled =
            enabled;

        if (!enabled &&
            heldTargetId_ == id) {
            heldTargetId_ = 0;
            heldSeconds_ = 0.0f;
            activationLatched_ = false;
        }

        return true;
    }

    return false;
}

InteractionFrame InteractionSystem::step(
    Vec3 playerPosition,
    Vec3 viewDirection,
    const InteractionInput& input,
    float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) ||
         deltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(
              deltaSeconds,
              0.05f);

    frame_ = {};

    float distance = 0.0f;
    float facing = 0.0f;

    const auto* target =
        chooseTarget(
            playerPosition,
            viewDirection,
            distance,
            facing);

    if (target == nullptr) {
        heldTargetId_ = 0;
        heldSeconds_ = 0.0f;
        activationLatched_ = false;
        previousHeld_ = input.held;
        return frame_;
    }

    frame_.promptVisible = true;
    frame_.targetId =
        target->id;
    frame_.kind =
        target->kind;
    frame_.cost =
        target->cost;
    frame_.distanceMeters =
        distance;
    frame_.facingDot =
        facing;

    if (heldTargetId_ !=
        target->id) {
        heldTargetId_ =
            target->id;
        heldSeconds_ = 0.0f;
        activationLatched_ = false;
    }

    const bool pressed =
        input.held &&
        !previousHeld_;

    if (!input.held) {
        heldSeconds_ = 0.0f;
        activationLatched_ = false;
    } else if (
        !activationLatched_) {
        if (target->holdSeconds <=
            0.001f) {
            if (pressed) {
                frame_.activatedThisTick =
                    true;
                activationLatched_ = true;
            }
        } else {
            heldSeconds_ += dt;

            frame_.holdAlpha =
                std::clamp(
                    heldSeconds_ /
                        target->holdSeconds,
                    0.0f,
                    1.0f);

            if (heldSeconds_ +
                    1.0e-6f >=
                target->holdSeconds) {
                frame_.activatedThisTick =
                    true;
                activationLatched_ = true;
                frame_.holdAlpha = 1.0f;
            }
        }
    }

    if (target->holdSeconds > 0.001f &&
        !frame_.activatedThisTick) {
        frame_.holdAlpha =
            std::clamp(
                heldSeconds_ /
                    target->holdSeconds,
                0.0f,
                1.0f);
    }

    previousHeld_ =
        input.held;

    return frame_;
}

const InteractionFrame&
InteractionSystem::frame() const noexcept {
    return frame_;
}

std::size_t InteractionSystem::targetCount() const noexcept {
    return targetCount_;
}

const InteractionTarget*
InteractionSystem::chooseTarget(
    Vec3 playerPosition,
    Vec3 viewDirection,
    float& outDistance,
    float& outFacing) const noexcept {
    const Vec3 view =
        normalizedOrForward(
            viewDirection);

    const InteractionTarget* best =
        nullptr;

    float bestScore =
        -1000000.0f;

    outDistance = 0.0f;
    outFacing = 0.0f;

    for (std::size_t i = 0;
         i < targetCount_;
         ++i) {
        const auto& target =
            targets_[i];

        if (!target.enabled) {
            continue;
        }

        const Vec3 delta{
            target.position.x -
                playerPosition.x,
            target.position.y -
                playerPosition.y,
            target.position.z -
                playerPosition.z,
        };

        const float distance =
            length3(delta);

        if (!std::isfinite(distance) ||
            distance >
                target.maximumDistance) {
            continue;
        }

        const Vec3 direction =
            normalizedOrForward(
                delta);

        const float facing =
            dot3(
                view,
                direction);

        const float minimumFacing =
            std::clamp(
                std::isfinite(
                    target.minimumFacingDot)
                    ? target.minimumFacingDot
                    : 0.20f,
                -1.0f,
                1.0f);

        if (facing <
            minimumFacing) {
            continue;
        }

        const float distanceAlpha =
            std::clamp(
                distance /
                    target.maximumDistance,
                0.0f,
                1.0f);

        const float score =
            std::max(
                0.0f,
                target.priority) *
                2.0f +
            facing *
                0.75f -
            distanceAlpha;

        if (score <=
            bestScore) {
            continue;
        }

        bestScore = score;
        best = &target;
        outDistance = distance;
        outFacing = facing;
    }

    return best;
}

} // namespace xziel
