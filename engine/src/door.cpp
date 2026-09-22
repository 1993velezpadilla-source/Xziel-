#include "xziel/door.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

void DoorSystem::clear() noexcept {
    doors_ = {};
    count_ = 0;
}

bool DoorSystem::addDoor(
    const DoorDefinition& definition,
    HordeDirector& horde,
    FpsPlayerController& player) noexcept {
    if (definition.id == 0 ||
        count_ >= doors_.size() ||
        find(definition.id) != nullptr ||
        !std::isfinite(definition.openDurationSeconds) ||
        definition.openDurationSeconds <= 0.0f ||
        !std::isfinite(definition.collisionReleaseProgress)) {
        return false;
    }

    if (!horde.addDynamicBlocker(
            definition.id,
            definition.blocker,
            !definition.startsOpen) ||
        !player.addDynamicObstacle(
            definition.id,
            definition.blocker,
            !definition.startsOpen)) {
        return false;
    }

    for (auto& slot : doors_) {
        if (slot.occupied) continue;

        slot.frame = {
            .id = definition.id,
            .cost = definition.cost,
            .open = definition.startsOpen,
            .opening = false,
            .openedThisTick = false,
            .becameFullyOpenThisTick = false,
            .collisionReleased = definition.startsOpen,
            .insufficientFundsThisTick = false,
            .openProgress = definition.startsOpen ? 1.0f : 0.0f,
        };
        slot.openDurationSeconds =
            std::max(definition.openDurationSeconds, 0.05f);
        slot.collisionReleaseProgress =
            std::clamp(definition.collisionReleaseProgress, 0.10f, 1.0f);
        slot.occupied = true;
        ++count_;
        return true;
    }
    return false;
}

DoorFrame DoorSystem::activate(
    std::uint32_t id,
    HordeDirector& horde,
    FpsPlayerController& player,
    ScoreSystem& score) noexcept {
    (void) horde;
    (void) player;

    auto* slot = find(id);
    if (slot == nullptr) return {};

    slot->frame.openedThisTick = false;
    slot->frame.becameFullyOpenThisTick = false;
    slot->frame.insufficientFundsThisTick = false;

    if (slot->frame.open || slot->frame.opening) {
        return slot->frame;
    }

    if (!score.spend(slot->frame.cost)) {
        slot->frame.insufficientFundsThisTick = true;
        return slot->frame;
    }

    slot->frame.opening = true;
    slot->frame.openedThisTick = true;
    return slot->frame;
}

void DoorSystem::step(
    float deltaSeconds,
    HordeDirector& horde,
    FpsPlayerController& player) noexcept {
    const float dt = std::clamp(
        std::isfinite(deltaSeconds) ? deltaSeconds : 0.0f,
        0.0f,
        0.10f);

    for (auto& slot : doors_) {
        if (!slot.occupied) continue;

        slot.frame.openedThisTick = false;
        slot.frame.becameFullyOpenThisTick = false;
        slot.frame.insufficientFundsThisTick = false;

        if (!slot.frame.opening) continue;

        slot.frame.openProgress = std::clamp(
            slot.frame.openProgress + dt / slot.openDurationSeconds,
            0.0f,
            1.0f);

        if (!slot.frame.collisionReleased &&
            slot.frame.openProgress >= slot.collisionReleaseProgress) {
            (void) horde.setDynamicBlockerEnabled(slot.frame.id, false);
            (void) player.setDynamicObstacleEnabled(slot.frame.id, false);
            slot.frame.collisionReleased = true;
        }

        if (slot.frame.openProgress >= 1.0f) {
            slot.frame.openProgress = 1.0f;
            slot.frame.opening = false;
            slot.frame.open = true;
            slot.frame.becameFullyOpenThisTick = true;

            if (!slot.frame.collisionReleased) {
                (void) horde.setDynamicBlockerEnabled(slot.frame.id, false);
                (void) player.setDynamicObstacleEnabled(slot.frame.id, false);
                slot.frame.collisionReleased = true;
            }
        }
    }
}

const DoorFrame* DoorSystem::frame(std::uint32_t id) const noexcept {
    const auto* slot = find(id);
    return slot != nullptr ? &slot->frame : nullptr;
}

std::size_t DoorSystem::count() const noexcept { return count_; }

DoorSystem::Slot* DoorSystem::find(std::uint32_t id) noexcept {
    for (auto& slot : doors_) {
        if (slot.occupied && slot.frame.id == id) return &slot;
    }
    return nullptr;
}

const DoorSystem::Slot* DoorSystem::find(std::uint32_t id) const noexcept {
    for (const auto& slot : doors_) {
        if (slot.occupied && slot.frame.id == id) return &slot;
    }
    return nullptr;
}

} // namespace xziel
