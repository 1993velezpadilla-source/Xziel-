#include "xziel/zombie_window.hpp"

namespace xziel {

void ZombieWindowSystem::reset() noexcept {
    for (auto& slot : windows_) {
        if (!slot.occupied) {
            continue;
        }
        slot.barricade.reset();
        slot.frame = {
            .id = slot.id,
            .barricade = slot.barricade.frame(),
            .navigationBlocked = true,
        };
    }
}

void ZombieWindowSystem::beginRound() noexcept {
    for (auto& slot : windows_) {
        if (slot.occupied) {
            slot.barricade.beginRound();
        }
    }
}

bool ZombieWindowSystem::addWindow(
    const ZombieWindowDefinition& definition,
    HordeDirector& horde) noexcept {
    if (definition.id == 0 || count_ >= windows_.size() ||
        find(definition.id) != nullptr) {
        return false;
    }

    if (!horde.addDynamicBlocker(
            definition.id,
            definition.blocker,
            true)) {
        return false;
    }

    for (auto& slot : windows_) {
        if (slot.occupied) {
            continue;
        }
        slot.id = definition.id;
        slot.barricade = BarricadeSystem(definition.barricade);
        slot.frame = {
            .id = definition.id,
            .barricade = slot.barricade.frame(),
            .navigationBlocked = true,
        };
        slot.occupied = true;
        ++count_;
        return true;
    }

    return false;
}

ZombieWindowFrame ZombieWindowSystem::step(
    std::uint32_t id,
    bool zombieTearing,
    bool playerRebuilding,
    float deltaSeconds,
    HordeDirector& horde,
    ScoreSystem& score) noexcept {
    auto* slot = find(id);
    if (slot == nullptr) {
        return {};
    }

    const auto barricade = slot->barricade.step(
        zombieTearing,
        playerRebuilding,
        deltaSeconds);

    const bool blocked = barricade.blocksZombieTraversal;
    (void) horde.setDynamicBlockerEnabled(id, blocked);

    if (barricade.pointsAwardedThisTick > 0) {
        (void) score.awardUtility(barricade.pointsAwardedThisTick);
    }

    slot->frame = {
        .id = id,
        .barricade = barricade,
        .navigationBlocked = blocked,
    };
    return slot->frame;
}

const ZombieWindowFrame*
ZombieWindowSystem::frame(std::uint32_t id) const noexcept {
    const auto* slot = find(id);
    return slot != nullptr ? &slot->frame : nullptr;
}

std::size_t ZombieWindowSystem::count() const noexcept {
    return count_;
}

ZombieWindowSystem::Slot*
ZombieWindowSystem::find(std::uint32_t id) noexcept {
    for (auto& slot : windows_) {
        if (slot.occupied && slot.id == id) {
            return &slot;
        }
    }
    return nullptr;
}

const ZombieWindowSystem::Slot*
ZombieWindowSystem::find(std::uint32_t id) const noexcept {
    for (const auto& slot : windows_) {
        if (slot.occupied && slot.id == id) {
            return &slot;
        }
    }
    return nullptr;
}

} // namespace xziel
