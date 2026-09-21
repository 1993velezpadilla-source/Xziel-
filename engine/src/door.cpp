#include "xziel/door.hpp"

namespace xziel {

void DoorSystem::clear() noexcept {
    doors_ = {};
    count_ = 0;
}

bool DoorSystem::addDoor(
    const DoorDefinition& definition,
    HordeDirector& horde) noexcept {
    if (definition.id == 0 || count_ >= doors_.size() ||
        find(definition.id) != nullptr) {
        return false;
    }
    if (!horde.addDynamicBlocker(
            definition.id,
            definition.blocker,
            !definition.startsOpen)) {
        return false;
    }
    for (auto& slot : doors_) {
        if (slot.occupied) {
            continue;
        }
        slot.frame = {
            .id = definition.id,
            .cost = definition.cost,
            .open = definition.startsOpen,
        };
        slot.occupied = true;
        ++count_;
        return true;
    }
    return false;
}

DoorFrame DoorSystem::activate(
    std::uint32_t id,
    HordeDirector& horde,
    ScoreSystem& score) noexcept {
    auto* slot = find(id);
    if (slot == nullptr) {
        return {};
    }
    slot->frame.openedThisTick = false;
    slot->frame.insufficientFundsThisTick = false;
    if (slot->frame.open) {
        return slot->frame;
    }
    if (!score.spend(slot->frame.cost)) {
        slot->frame.insufficientFundsThisTick = true;
        return slot->frame;
    }
    slot->frame.open = true;
    slot->frame.openedThisTick = true;
    (void) horde.setDynamicBlockerEnabled(id, false);
    return slot->frame;
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
