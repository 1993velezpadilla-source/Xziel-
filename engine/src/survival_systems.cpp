#include "xziel/survival_systems.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace xziel {

namespace {

constexpr std::size_t powerIndex(
    SurvivalPowerUpKind kind) noexcept {
    return static_cast<std::size_t>(kind);
}

bool finiteVec3(Vec3 value) noexcept {
    return std::isfinite(value.x) &&
        std::isfinite(value.y) &&
        std::isfinite(value.z);
}

std::uint32_t saturatingU32(
    double value) noexcept {
    if (!std::isfinite(value) || value <= 0.0) {
        return 0U;
    }

    const double maximum =
        static_cast<double>(
            std::numeric_limits<std::uint32_t>::max());

    return static_cast<std::uint32_t>(
        std::min(value, maximum));
}

InteractionKind interactionKindFor(
    SurvivalStationKind kind) noexcept {
    switch (kind) {
        case SurvivalStationKind::Perk:
            return InteractionKind::Perk;
        case SurvivalStationKind::RandomWeapon:
        case SurvivalStationKind::WallWeapon:
        case SurvivalStationKind::WeaponUpgrade:
            return InteractionKind::WeaponBuy;
        case SurvivalStationKind::Consumable:
            return InteractionKind::Use;
    }

    return InteractionKind::Use;
}

} // namespace

SurvivalImmediateResult
applySurvivalImmediateEffects(
    const SurvivalFrame& frame,
    const SurvivalImmediateTargets& targets) noexcept {
    SurvivalImmediateResult result{};

    if (targets.score != nullptr) {
        targets.score->setAwardMultiplier(
            frame.scoreMultiplier);
        result.scoreMultiplierApplied = true;
    }

    if (frame.refillAmmoThisTick &&
        targets.weapons != nullptr) {
        constexpr std::size_t kMaxCarriedWeaponBridge = 8U;
        const std::size_t count =
            std::min(
                targets.weaponCount,
                kMaxCarriedWeaponBridge);

        for (std::size_t i = 0; i < count; ++i) {
            targets.weapons[i].refillAmmo(
                targets.refillMagazines);
            ++result.weaponsRefilled;
        }
    }

    if (frame.fullHealThisTick &&
        targets.vitals != nullptr) {
        result.healthRestored =
            targets.vitals->restoreFullHealth();
    }

    if (frame.clearWaveThisTick &&
        targets.horde != nullptr) {
        result.zombiesEliminated =
            targets.horde->eliminateAllActive();
    }

    if (frame.repairAllThisTick &&
        targets.windows != nullptr &&
        targets.horde != nullptr &&
        targets.player != nullptr) {
        result.windowsRepaired =
            targets.windows->repairAll(
                *targets.horde,
                *targets.player);
    }

    return result;
}

bool SurvivalRuntime::load(
    const SurvivalContentDefinition& definition) noexcept {
    if (definition.perkCount > definition.perks.size() ||
        definition.weaponPoolCount > definition.weaponPool.size() ||
        definition.consumableCount > definition.consumables.size() ||
        definition.stationCount > definition.stations.size() ||
        definition.rules.perkLimit > kMaxSurvivalPerks ||
        definition.rules.maxWeaponUpgradeTier == 0U ||
        !std::isfinite(definition.rules.weaponUpgradeCostMultiplier) ||
        definition.rules.weaponUpgradeCostMultiplier < 1.0f ||
        !std::isfinite(definition.rules.powerUpLifetimeSeconds) ||
        definition.rules.powerUpLifetimeSeconds <= 0.0f ||
        !std::isfinite(definition.rules.timedPowerUpSeconds) ||
        definition.rules.timedPowerUpSeconds <= 0.0f ||
        !std::isfinite(definition.rules.dropBaseChance) ||
        definition.rules.dropBaseChance < 0.0f ||
        definition.rules.dropBaseChance > 1.0f ||
        !std::isfinite(definition.rules.dropCooldownSeconds) ||
        definition.rules.dropCooldownSeconds < 0.0f) {
        return false;
    }

    for (std::size_t i = 0; i < definition.perkCount; ++i) {
        const auto& item = definition.perks[i];
        if (item.id == 0U ||
            !std::isfinite(item.magnitude) ||
            item.magnitude <= 0.0f) {
            return false;
        }

        for (std::size_t j = i + 1; j < definition.perkCount; ++j) {
            if (definition.perks[j].id == item.id) {
                return false;
            }
        }
    }

    for (std::size_t i = 0; i < definition.weaponPoolCount; ++i) {
        const auto& item = definition.weaponPool[i];
        if (item.weaponId == 0U || item.weight == 0U ||
            item.minimumRound == 0U ||
            (item.maximumRound != 0U &&
             item.maximumRound < item.minimumRound)) {
            return false;
        }
    }

    for (std::size_t i = 0; i < definition.consumableCount; ++i) {
        const auto& item = definition.consumables[i];
        if (item.id == 0U || item.weight == 0U ||
            !std::isfinite(item.durationSeconds) ||
            item.durationSeconds < 0.0f ||
            item.powerUp == SurvivalPowerUpKind::Count) {
            return false;
        }

        for (std::size_t j = i + 1; j < definition.consumableCount; ++j) {
            if (definition.consumables[j].id == item.id) {
                return false;
            }
        }
    }

    for (std::size_t i = 0; i < definition.stationCount; ++i) {
        const auto& item = definition.stations[i];
        if (item.id == 0U || !finiteVec3(item.position) ||
            !std::isfinite(item.maximumDistance) ||
            item.maximumDistance <= 0.0f ||
            !std::isfinite(item.minimumFacingDot) ||
            !std::isfinite(item.priority) ||
            !std::isfinite(item.holdSeconds) ||
            item.holdSeconds < 0.0f) {
            return false;
        }

        for (std::size_t j = i + 1; j < definition.stationCount; ++j) {
            if (definition.stations[j].id == item.id) {
                return false;
            }
        }

        if (!item.enabled) {
            continue;
        }

        if (item.kind == SurvivalStationKind::Perk) {
            bool found = false;
            for (std::size_t p = 0; p < definition.perkCount; ++p) {
                found = found ||
                    (definition.perks[p].enabled &&
                     definition.perks[p].id == item.contentId);
            }
            if (!found) {
                return false;
            }
        }

        if (item.kind == SurvivalStationKind::WallWeapon &&
            item.contentId == 0U) {
            return false;
        }
    }

    content_ = definition;
    loaded_ = true;
    reset();
    return true;
}

void SurvivalRuntime::reset(
    std::uint32_t seed) noexcept {
    ownedPerks_.fill(0U);
    ownedPerkCount_ = 0U;

    heldConsumables_.fill(0U);
    heldConsumableCount_ = 0U;

    drops_ = {};
    frame_ = {};
    frame_.round = 1U;

    modifiers_ = {};

    randomState_ =
        seed != 0U
        ? seed
        : 0x5A17C7U;

    nextDropId_ = 1U;
    killsSinceDrop_ = 0U;
    consumableDrawsThisRound_ = 0U;
    freeRandomWeaponSpins_ = 0U;
    freeWeaponUpgrades_ = 0U;

    dropCooldownSeconds_ = 0.0f;
    veilSeconds_ = 0.0f;
    freezeHordeSeconds_ = 0.0f;

    updateDerivedFrame();
}

void SurvivalRuntime::beginTick() noexcept {
    frame_.refillAmmoThisTick = false;
    frame_.repairAllThisTick = false;
    frame_.clearWaveThisTick = false;
    frame_.fullHealThisTick = false;
    frame_.heavyWeaponGrantedThisTick = false;
    frame_.powerUpSpawnedThisTick = false;
    frame_.powerUpCollectedThisTick = false;
    frame_.lastDropId = 0U;
}

void SurvivalRuntime::beginRound(
    std::uint32_t round) noexcept {
    frame_.round = std::max(round, 1U);
    consumableDrawsThisRound_ = 0U;
}

bool SurvivalRuntime::registerInteractions(
    InteractionSystem& interactions) const noexcept {
    if (!loaded_) {
        return false;
    }

    for (std::size_t i = 0; i < content_.stationCount; ++i) {
        const auto& item = content_.stations[i];
        if (!item.enabled) {
            continue;
        }

        const InteractionTarget target{
            .id = item.id,
            .kind = interactionKindFor(item.kind),
            .position = item.position,
            .maximumDistance = item.maximumDistance,
            .minimumFacingDot = item.minimumFacingDot,
            .priority = item.priority,
            .holdSeconds = item.holdSeconds,
            .cost = effectiveStationCost(item),
            .enabled = true,
        };

        if (!interactions.addTarget(target)) {
            return false;
        }
    }

    return true;
}

bool SurvivalRuntime::setConsumableDeck(
    const std::uint32_t* ids,
    std::size_t count) noexcept {
    if (!loaded_ || ids == nullptr || count == 0U ||
        count > consumableDeck_.size()) {
        return false;
    }

    for (std::size_t i = 0; i < count; ++i) {
        const auto* item = consumable(ids[i]);
        if (item == nullptr || !item->enabled) {
            return false;
        }
    }

    consumableDeck_.fill(0U);
    for (std::size_t i = 0; i < count; ++i) {
        consumableDeck_[i] = ids[i];
    }
    consumableDeckCount_ = count;
    return true;
}

SurvivalTransaction SurvivalRuntime::purchasePerk(
    std::uint32_t stationId,
    ScoreSystem& score,
    GameplayEventQueue* events) noexcept {
    SurvivalTransaction result{};
    result.stationId = stationId;

    const auto* vendor = station(stationId);
    if (vendor == nullptr ||
        vendor->kind != SurvivalStationKind::Perk ||
        !vendor->enabled) {
        return result;
    }

    const auto* perkItem = perk(vendor->contentId);
    if (perkItem == nullptr || !perkItem->enabled ||
        hasPerk(perkItem->id)) {
        return result;
    }

    if (ownedPerkCount_ >= content_.rules.perkLimit) {
        result.inventoryFull = true;
        return result;
    }

    result.contentId = perkItem->id;
    result.cost = vendor->cost != 0U
        ? effectiveStationCost(*vendor)
        : saturatingU32(
            static_cast<double>(perkItem->cost) *
            (frame_.discountActive ? 0.5 : 1.0));

    if (!score.spend(result.cost)) {
        result.insufficientFunds = true;
        return result;
    }

    result.success = grantPerk(perkItem->id, false);
    if (result.success) {
        emit(
            events,
            GameplayEventType::PerkPurchased,
            stationId,
            perkItem->id,
            result.cost);
    }
    return result;
}

SurvivalTransaction SurvivalRuntime::purchaseWallWeapon(
    std::uint32_t stationId,
    ScoreSystem& score,
    GameplayEventQueue* events) noexcept {
    SurvivalTransaction result{};
    result.stationId = stationId;

    const auto* vendor = station(stationId);
    if (vendor == nullptr ||
        vendor->kind != SurvivalStationKind::WallWeapon ||
        !vendor->enabled ||
        vendor->contentId == 0U) {
        return result;
    }

    result.contentId = vendor->contentId;
    result.cost = effectiveStationCost(*vendor);

    if (!score.spend(result.cost)) {
        result.insufficientFunds = true;
        return result;
    }

    result.success = true;
    emit(
        events,
        GameplayEventType::WallWeaponPurchased,
        stationId,
        result.contentId,
        result.cost);
    return result;
}

SurvivalTransaction SurvivalRuntime::spinRandomWeapon(
    std::uint32_t stationId,
    ScoreSystem& score,
    GameplayEventQueue* events) noexcept {
    SurvivalTransaction result{};
    result.stationId = stationId;

    const auto* vendor = station(stationId);
    if (vendor == nullptr ||
        vendor->kind != SurvivalStationKind::RandomWeapon ||
        !vendor->enabled) {
        return result;
    }

    const std::uint32_t weaponId = chooseWeapon();
    if (weaponId == 0U) {
        return result;
    }

    bool free = freeRandomWeaponSpins_ > 0U;
    result.cost = free
        ? 0U
        : effectiveStationCost(*vendor);

    if (!free && !score.spend(result.cost)) {
        result.insufficientFunds = true;
        return result;
    }

    if (free) {
        --freeRandomWeaponSpins_;
    }

    result.contentId = weaponId;
    result.success = true;

    for (std::size_t i = 0; i < content_.weaponPoolCount; ++i) {
        if (content_.weaponPool[i].weaponId == weaponId &&
            content_.weaponPool[i].wonderWeapon) {
            result.wonderWeapon = true;
            break;
        }
    }

    emit(
        events,
        result.wonderWeapon
            ? GameplayEventType::WonderWeaponAwarded
            : GameplayEventType::RandomWeaponRolled,
        stationId,
        weaponId,
        result.cost);

    return result;
}

SurvivalTransaction SurvivalRuntime::upgradeWeapon(
    std::uint32_t stationId,
    std::uint32_t weaponId,
    std::uint32_t currentTier,
    ScoreSystem& score,
    GameplayEventQueue* events) noexcept {
    SurvivalTransaction result{};
    result.stationId = stationId;
    result.contentId = weaponId;

    const auto* vendor = station(stationId);
    if (vendor == nullptr ||
        vendor->kind != SurvivalStationKind::WeaponUpgrade ||
        !vendor->enabled ||
        weaponId == 0U ||
        currentTier >= content_.rules.maxWeaponUpgradeTier) {
        return result;
    }

    const bool free = freeWeaponUpgrades_ > 0U;
    result.cost = free
        ? 0U
        : upgradeCost(*vendor, currentTier);

    if (!free && !score.spend(result.cost)) {
        result.insufficientFunds = true;
        return result;
    }

    if (free) {
        --freeWeaponUpgrades_;
    }

    result.newTier = currentTier + 1U;
    result.success = true;
    emit(
        events,
        GameplayEventType::WeaponUpgraded,
        stationId,
        weaponId,
        result.newTier,
        static_cast<float>(result.cost));
    return result;
}

SurvivalTransaction SurvivalRuntime::drawConsumable(
    std::uint32_t stationId,
    ScoreSystem& score,
    GameplayEventQueue* events) noexcept {
    SurvivalTransaction result{};
    result.stationId = stationId;

    const auto* vendor = station(stationId);
    if (vendor == nullptr ||
        vendor->kind != SurvivalStationKind::Consumable ||
        !vendor->enabled) {
        return result;
    }

    if (heldConsumableCount_ >= heldConsumables_.size()) {
        result.inventoryFull = true;
        return result;
    }

    const std::uint32_t itemId = chooseConsumable();
    if (itemId == 0U) {
        return result;
    }

    const double baseCost =
        static_cast<double>(
            vendor->cost != 0U
                ? vendor->cost
                : effectiveStationCost(*vendor));
    const double escalator =
        static_cast<double>(content_.rules.consumableDrawCostStep) *
        static_cast<double>(consumableDrawsThisRound_);
    const double discount =
        frame_.discountActive ? 0.5 : 1.0;

    result.cost =
        saturatingU32((baseCost + escalator) * discount);

    if (!score.spend(result.cost)) {
        result.insufficientFunds = true;
        return result;
    }

    heldConsumables_[heldConsumableCount_++] = itemId;
    ++consumableDrawsThisRound_;

    result.contentId = itemId;
    result.success = true;

    emit(
        events,
        GameplayEventType::ConsumableDispensed,
        stationId,
        itemId,
        result.cost);
    return result;
}

bool SurvivalRuntime::activateConsumable(
    std::size_t heldSlot,
    ScoreSystem& score,
    GameplayEventQueue* events) noexcept {
    (void) score;

    if (heldSlot >= heldConsumableCount_) {
        return false;
    }

    const std::uint32_t itemId =
        heldConsumables_[heldSlot];
    const auto* item = consumable(itemId);
    if (item == nullptr || !item->enabled) {
        return false;
    }

    switch (item->effect) {
        case SurvivalConsumableEffect::GrantPowerUp:
            applyPowerUp(item->powerUp);
            break;

        case SurvivalConsumableEffect::GrantRandomPerk:
            (void) grantRandomPerk(false);
            break;

        case SurvivalConsumableEffect::GrantAllPerks:
            for (std::size_t i = 0; i < content_.perkCount; ++i) {
                if (content_.perks[i].enabled) {
                    (void) grantPerk(
                        content_.perks[i].id,
                        true);
                }
            }
            break;

        case SurvivalConsumableEffect::FreeRandomWeapon:
            ++freeRandomWeaponSpins_;
            break;

        case SurvivalConsumableEffect::FreeWeaponUpgrade:
            ++freeWeaponUpgrades_;
            break;

        case SurvivalConsumableEffect::Veil:
            veilSeconds_ = std::max(
                veilSeconds_,
                item->durationSeconds > 0.0f
                    ? item->durationSeconds
                    : content_.rules.timedPowerUpSeconds);
            break;

        case SurvivalConsumableEffect::TimeFreeze:
            freezeHordeSeconds_ = std::max(
                freezeHordeSeconds_,
                item->durationSeconds > 0.0f
                    ? item->durationSeconds
                    : 10.0f);
            break;
    }

    for (std::size_t i = heldSlot + 1U;
         i < heldConsumableCount_;
         ++i) {
        heldConsumables_[i - 1U] =
            heldConsumables_[i];
    }

    --heldConsumableCount_;
    heldConsumables_[heldConsumableCount_] = 0U;

    updateDerivedFrame();
    emit(
        events,
        GameplayEventType::ConsumableActivated,
        itemId);
    return true;
}

std::uint32_t SurvivalRuntime::onZombieKilled(
    Vec3 position,
    bool eligible,
    GameplayEventQueue* events) noexcept {
    if (!loaded_ || !eligible || !finiteVec3(position)) {
        return 0U;
    }

    ++killsSinceDrop_;

    if (dropCooldownSeconds_ > 0.0f) {
        return 0U;
    }

    bool hasSlot = false;
    std::size_t freeSlot = 0U;
    for (std::size_t i = 0; i < drops_.size(); ++i) {
        if (!drops_[i].active) {
            hasSlot = true;
            freeSlot = i;
            break;
        }
    }

    if (!hasSlot) {
        return 0U;
    }

    const float roundBoost =
        std::min(
            static_cast<float>(
                frame_.round > 1U
                    ? frame_.round - 1U
                    : 0U) *
                0.0005f,
            0.015f);

    const bool pity =
        content_.rules.dropPityKills > 0U &&
        killsSinceDrop_ >= content_.rules.dropPityKills;

    if (!pity &&
        random01() >
            std::clamp(
                content_.rules.dropBaseChance +
                    roundBoost,
                0.0f,
                1.0f)) {
        return 0U;
    }

    auto& drop = drops_[freeSlot];
    drop.id = nextDropId_++;
    if (nextDropId_ == 0U) {
        nextDropId_ = 1U;
    }
    drop.kind = choosePowerUp();
    drop.position = position;
    drop.remainingSeconds =
        content_.rules.powerUpLifetimeSeconds;
    drop.active = true;

    killsSinceDrop_ = 0U;
    dropCooldownSeconds_ =
        content_.rules.dropCooldownSeconds;

    frame_.powerUpSpawnedThisTick = true;
    frame_.lastDropId = drop.id;
    frame_.lastPowerUp = drop.kind;

    emit(
        events,
        GameplayEventType::PowerUpSpawned,
        drop.id,
        static_cast<std::uint32_t>(drop.kind));
    return drop.id;
}

bool SurvivalRuntime::collectPowerUp(
    std::uint32_t dropId,
    ScoreSystem& score,
    GameplayEventQueue* events) noexcept {
    (void) score;

    if (dropId == 0U) {
        return false;
    }

    for (auto& drop : drops_) {
        if (!drop.active || drop.id != dropId) {
            continue;
        }

        const SurvivalPowerUpKind kind =
            drop.kind;
        drop.active = false;
        drop.remainingSeconds = 0.0f;

        applyPowerUp(kind);
        updateDerivedFrame();

        frame_.powerUpCollectedThisTick = true;
        frame_.lastDropId = dropId;
        frame_.lastPowerUp = kind;

        emit(
            events,
            GameplayEventType::PowerUpCollected,
            dropId,
            static_cast<std::uint32_t>(kind));
        return true;
    }

    return false;
}

SurvivalFrame SurvivalRuntime::step(
    float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) ||
         deltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(deltaSeconds, 0.25f);

    for (auto& seconds : frame_.powerUpSeconds) {
        seconds =
            std::max(
                0.0f,
                seconds - dt);
    }

    veilSeconds_ =
        std::max(
            0.0f,
            veilSeconds_ - dt);
    freezeHordeSeconds_ =
        std::max(
            0.0f,
            freezeHordeSeconds_ - dt);
    dropCooldownSeconds_ =
        std::max(
            0.0f,
            dropCooldownSeconds_ - dt);

    for (auto& drop : drops_) {
        if (!drop.active) {
            continue;
        }

        drop.remainingSeconds =
            std::max(
                0.0f,
                drop.remainingSeconds - dt);

        if (drop.remainingSeconds <= 0.0f) {
            drop.active = false;
        }
    }

    updateDerivedFrame();
    return frame_;
}

bool SurvivalRuntime::hasPerk(
    std::uint32_t perkId) const noexcept {
    if (perkId == 0U) {
        return false;
    }

    for (std::size_t i = 0; i < ownedPerkCount_; ++i) {
        if (ownedPerks_[i] == perkId) {
            return true;
        }
    }
    return false;
}

std::size_t SurvivalRuntime::perkCount() const noexcept {
    return ownedPerkCount_;
}

std::size_t SurvivalRuntime::heldConsumableCount() const noexcept {
    return heldConsumableCount_;
}

std::uint32_t SurvivalRuntime::heldConsumable(
    std::size_t slot) const noexcept {
    return slot < heldConsumableCount_
        ? heldConsumables_[slot]
        : 0U;
}

std::uint32_t SurvivalRuntime::scaledScoreAward(
    std::uint32_t baseAward) const noexcept {
    return saturatingU32(
        static_cast<double>(baseAward) *
        static_cast<double>(frame_.scoreMultiplier));
}

const SurvivalModifiers&
SurvivalRuntime::modifiers() const noexcept {
    return modifiers_;
}

const SurvivalFrame&
SurvivalRuntime::frame() const noexcept {
    return frame_;
}

const SurvivalContentDefinition&
SurvivalRuntime::content() const noexcept {
    return content_;
}

const std::array<
    SurvivalPowerUpDrop,
    kMaxSurvivalPowerUpDrops>&
SurvivalRuntime::drops() const noexcept {
    return drops_;
}

const SurvivalStationDefinition*
SurvivalRuntime::station(
    std::uint32_t id) const noexcept {
    for (std::size_t i = 0; i < content_.stationCount; ++i) {
        if (content_.stations[i].id == id) {
            return &content_.stations[i];
        }
    }
    return nullptr;
}

const SurvivalPerkDefinition*
SurvivalRuntime::perk(
    std::uint32_t id) const noexcept {
    for (std::size_t i = 0; i < content_.perkCount; ++i) {
        if (content_.perks[i].id == id) {
            return &content_.perks[i];
        }
    }
    return nullptr;
}

const SurvivalConsumableDefinition*
SurvivalRuntime::consumable(
    std::uint32_t id) const noexcept {
    for (std::size_t i = 0; i < content_.consumableCount; ++i) {
        if (content_.consumables[i].id == id) {
            return &content_.consumables[i];
        }
    }
    return nullptr;
}

std::uint32_t SurvivalRuntime::effectiveStationCost(
    const SurvivalStationDefinition& item) const noexcept {
    std::uint32_t base = item.cost;

    if (base == 0U) {
        switch (item.kind) {
            case SurvivalStationKind::RandomWeapon:
                base = content_.rules.randomWeaponBaseCost;
                break;
            case SurvivalStationKind::WeaponUpgrade:
                base = content_.rules.weaponUpgradeBaseCost;
                break;
            case SurvivalStationKind::Consumable:
                base = 0U;
                break;
            case SurvivalStationKind::Perk: {
                const auto* perkItem = perk(item.contentId);
                base = perkItem != nullptr
                    ? perkItem->cost
                    : 0U;
                break;
            }
            case SurvivalStationKind::WallWeapon:
                break;
        }
    }

    return saturatingU32(
        static_cast<double>(base) *
        (frame_.discountActive ? 0.5 : 1.0));
}

std::uint32_t SurvivalRuntime::upgradeCost(
    const SurvivalStationDefinition& item,
    std::uint32_t currentTier) const noexcept {
    double value =
        static_cast<double>(
            item.cost != 0U
                ? item.cost
                : content_.rules.weaponUpgradeBaseCost);

    for (std::uint32_t tier = 0U;
         tier < currentTier;
         ++tier) {
        value *=
            static_cast<double>(
                content_.rules.weaponUpgradeCostMultiplier);
    }

    if (frame_.discountActive) {
        value *= 0.5;
    }

    return saturatingU32(value);
}

std::uint32_t SurvivalRuntime::chooseWeapon() noexcept {
    std::uint64_t totalWeight = 0U;

    for (std::size_t i = 0; i < content_.weaponPoolCount; ++i) {
        const auto& item = content_.weaponPool[i];
        if (!item.enabled ||
            frame_.round < item.minimumRound ||
            (item.maximumRound != 0U &&
             frame_.round > item.maximumRound)) {
            continue;
        }
        totalWeight += item.weight;
    }

    if (totalWeight == 0U) {
        return 0U;
    }

    const std::uint64_t pick =
        static_cast<std::uint64_t>(
            random01() *
            static_cast<float>(totalWeight));

    std::uint64_t cursor = 0U;
    for (std::size_t i = 0; i < content_.weaponPoolCount; ++i) {
        const auto& item = content_.weaponPool[i];
        if (!item.enabled ||
            frame_.round < item.minimumRound ||
            (item.maximumRound != 0U &&
             frame_.round > item.maximumRound)) {
            continue;
        }

        cursor += item.weight;
        if (pick < cursor) {
            return item.weaponId;
        }
    }

    return content_.weaponPool[content_.weaponPoolCount - 1U].weaponId;
}

std::uint32_t SurvivalRuntime::chooseConsumable() noexcept {
    std::uint64_t totalWeight = 0U;

    if (consumableDeckCount_ > 0U) {
        for (std::size_t i = 0; i < consumableDeckCount_; ++i) {
            const auto* item = consumable(consumableDeck_[i]);
            if (item != nullptr && item->enabled) {
                totalWeight += item->weight;
            }
        }
    } else {
        for (std::size_t i = 0; i < content_.consumableCount; ++i) {
            if (content_.consumables[i].enabled) {
                totalWeight += content_.consumables[i].weight;
            }
        }
    }

    if (totalWeight == 0U) {
        return 0U;
    }

    const std::uint64_t pick =
        static_cast<std::uint64_t>(
            random01() *
            static_cast<float>(totalWeight));

    std::uint64_t cursor = 0U;

    if (consumableDeckCount_ > 0U) {
        for (std::size_t i = 0; i < consumableDeckCount_; ++i) {
            const auto* item = consumable(consumableDeck_[i]);
            if (item == nullptr || !item->enabled) {
                continue;
            }

            cursor += item->weight;
            if (pick < cursor) {
                return item->id;
            }
        }
    } else {
        for (std::size_t i = 0; i < content_.consumableCount; ++i) {
            const auto& item = content_.consumables[i];
            if (!item.enabled) {
                continue;
            }

            cursor += item.weight;
            if (pick < cursor) {
                return item.id;
            }
        }
    }

    return 0U;
}

SurvivalPowerUpKind
SurvivalRuntime::choosePowerUp() noexcept {
    constexpr std::array<SurvivalPowerUpKind, 9> kinds{{
        SurvivalPowerUpKind::FullAmmo,
        SurvivalPowerUpKind::OneHit,
        SurvivalPowerUpKind::DoubleScore,
        SurvivalPowerUpKind::WaveClear,
        SurvivalPowerUpKind::RepairAll,
        SurvivalPowerUpKind::Discount,
        SurvivalPowerUpKind::HeavyWeapon,
        SurvivalPowerUpKind::RandomPerk,
        SurvivalPowerUpKind::FullHealth,
    }};

    constexpr std::array<std::uint32_t, 9> weights{{
        22U, 14U, 14U, 10U, 10U, 8U, 6U, 5U, 11U,
    }};

    std::uint32_t totalWeight = 0U;
    for (const auto weight : weights) {
        totalWeight += weight;
    }

    const std::uint32_t pick =
        static_cast<std::uint32_t>(
            random01() *
            static_cast<float>(totalWeight));

    std::uint32_t cursor = 0U;
    for (std::size_t i = 0; i < kinds.size(); ++i) {
        cursor += weights[i];
        if (pick < cursor) {
            return kinds[i];
        }
    }

    return SurvivalPowerUpKind::FullAmmo;
}

float SurvivalRuntime::random01() noexcept {
    std::uint32_t x = randomState_;
    x ^= x << 13U;
    x ^= x >> 17U;
    x ^= x << 5U;

    randomState_ =
        x != 0U
        ? x
        : 0x5A17C7U;

    return static_cast<float>(
        randomState_ & 0x00FFFFFFU) /
        static_cast<float>(0x01000000U);
}

bool SurvivalRuntime::grantPerk(
    std::uint32_t perkId,
    bool ignoreLimit) noexcept {
    const auto* item = perk(perkId);
    if (item == nullptr || !item->enabled || hasPerk(perkId)) {
        return false;
    }

    if (!ignoreLimit &&
        ownedPerkCount_ >= content_.rules.perkLimit) {
        return false;
    }

    if (ownedPerkCount_ >= ownedPerks_.size()) {
        return false;
    }

    ownedPerks_[ownedPerkCount_++] = perkId;
    recomputeModifiers();
    return true;
}

bool SurvivalRuntime::grantRandomPerk(
    bool ignoreLimit) noexcept {
    std::array<std::uint32_t, kMaxSurvivalPerks> candidates{};
    std::size_t count = 0U;

    for (std::size_t i = 0; i < content_.perkCount; ++i) {
        const auto& item = content_.perks[i];
        if (item.enabled && !hasPerk(item.id)) {
            candidates[count++] = item.id;
        }
    }

    if (count == 0U) {
        return false;
    }

    const std::size_t index =
        std::min<std::size_t>(
            static_cast<std::size_t>(
                random01() *
                static_cast<float>(count)),
            count - 1U);

    return grantPerk(candidates[index], ignoreLimit);
}

void SurvivalRuntime::applyPowerUp(
    SurvivalPowerUpKind kind) noexcept {
    if (kind == SurvivalPowerUpKind::Count) {
        return;
    }

    const float duration =
        content_.rules.timedPowerUpSeconds;

    switch (kind) {
        case SurvivalPowerUpKind::FullAmmo:
            frame_.refillAmmoThisTick = true;
            break;

        case SurvivalPowerUpKind::OneHit:
        case SurvivalPowerUpKind::DoubleScore:
        case SurvivalPowerUpKind::Discount:
        case SurvivalPowerUpKind::HeavyWeapon:
            frame_.powerUpSeconds[powerIndex(kind)] =
                std::max(
                    frame_.powerUpSeconds[powerIndex(kind)],
                    duration);
            if (kind == SurvivalPowerUpKind::HeavyWeapon) {
                frame_.heavyWeaponGrantedThisTick = true;
            }
            break;

        case SurvivalPowerUpKind::WaveClear:
            frame_.clearWaveThisTick = true;
            break;

        case SurvivalPowerUpKind::RepairAll:
            frame_.repairAllThisTick = true;
            break;

        case SurvivalPowerUpKind::RandomPerk:
            (void) grantRandomPerk(false);
            break;

        case SurvivalPowerUpKind::FullHealth:
            frame_.fullHealThisTick = true;
            break;

        case SurvivalPowerUpKind::Count:
            break;
    }

    updateDerivedFrame();
}

void SurvivalRuntime::updateDerivedFrame() noexcept {
    frame_.scoreMultiplier =
        frame_.powerUpSeconds[
            powerIndex(
                SurvivalPowerUpKind::DoubleScore)] > 0.0f
        ? 2.0f
        : 1.0f;

    frame_.oneHitDamage =
        frame_.powerUpSeconds[
            powerIndex(
                SurvivalPowerUpKind::OneHit)] > 0.0f;

    frame_.discountActive =
        frame_.powerUpSeconds[
            powerIndex(
                SurvivalPowerUpKind::Discount)] > 0.0f;

    frame_.heavyWeaponActive =
        frame_.powerUpSeconds[
            powerIndex(
                SurvivalPowerUpKind::HeavyWeapon)] > 0.0f;

    frame_.veilSeconds = veilSeconds_;
    frame_.freezeHordeSeconds = freezeHordeSeconds_;
    frame_.zombiesIgnorePlayer = veilSeconds_ > 0.0f;
    frame_.hordeFrozen = freezeHordeSeconds_ > 0.0f;
}

void SurvivalRuntime::recomputeModifiers() noexcept {
    modifiers_ = {};

    for (std::size_t i = 0; i < ownedPerkCount_; ++i) {
        const auto* item = perk(ownedPerks_[i]);
        if (item == nullptr || !item->enabled) {
            continue;
        }

        switch (item->effect) {
            case SurvivalPerkEffect::Fortitude:
                modifiers_.maxHealthScale *= item->magnitude;
                break;

            case SurvivalPerkEffect::QuickHands:
                modifiers_.reloadTimeScale *= item->magnitude;
                break;

            case SurvivalPerkEffect::Endurance:
                modifiers_.moveSpeedScale *= item->magnitude;
                break;

            case SurvivalPerkEffect::SecondChance:
                modifiers_.reviveTimeScale *= item->magnitude;
                break;

            case SurvivalPerkEffect::RapidFire:
                modifiers_.fireIntervalScale *= item->magnitude;
                break;

            case SurvivalPerkEffect::Precision:
                modifiers_.headshotDamageScale *= item->magnitude;
                break;

            case SurvivalPerkEffect::Arsenal:
                modifiers_.extraWeaponSlots +=
                    std::max<std::uint32_t>(
                        1U,
                        static_cast<std::uint32_t>(
                            std::round(item->magnitude)));
                break;

            case SurvivalPerkEffect::BlastGuard:
                modifiers_.explosiveDamageScale *= item->magnitude;
                break;
        }
    }
}

void SurvivalRuntime::emit(
    GameplayEventQueue* events,
    GameplayEventType type,
    std::uint32_t subjectId,
    std::uint32_t actorId,
    std::uint32_t amount,
    float value) const noexcept {
    if (events == nullptr) {
        return;
    }

    (void) events->push({
        .type = type,
        .subjectId = subjectId,
        .actorId = actorId,
        .amount = amount,
        .value = value,
    });
}

} // namespace xziel
