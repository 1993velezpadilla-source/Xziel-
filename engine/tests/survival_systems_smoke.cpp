#include "xziel/survival_systems.hpp"

#include <cassert>

int main() {
    xziel::SurvivalContentDefinition content{};
    content.rules.perkLimit = 2U;
    content.rules.dropBaseChance = 1.0f;
    content.rules.dropCooldownSeconds = 0.0f;
    content.rules.dropPityKills = 1U;
    content.rules.powerUpLifetimeSeconds = 1.0f;
    content.rules.timedPowerUpSeconds = 1.0f;
    content.rules.randomWeaponBaseCost = 950U;
    content.rules.weaponUpgradeBaseCost = 5000U;

    content.perks[0] = {
        .id = 101U,
        .effect = xziel::SurvivalPerkEffect::Fortitude,
        .cost = 2500U,
        .magnitude = 1.5f,
    };
    content.perks[1] = {
        .id = 102U,
        .effect = xziel::SurvivalPerkEffect::QuickHands,
        .cost = 3000U,
        .magnitude = 0.70f,
    };
    content.perks[2] = {
        .id = 103U,
        .effect = xziel::SurvivalPerkEffect::Endurance,
        .cost = 2000U,
        .magnitude = 1.12f,
    };
    content.perkCount = 3U;

    content.weaponPool[0] = {
        .weaponId = 1001U,
        .weight = 10U,
        .minimumRound = 1U,
    };
    content.weaponPool[1] = {
        .weaponId = 1002U,
        .weight = 1U,
        .minimumRound = 1U,
        .wonderWeapon = true,
    };
    content.weaponPoolCount = 2U;

    content.consumables[0] = {
        .id = 2001U,
        .effect = xziel::SurvivalConsumableEffect::GrantPowerUp,
        .powerUp = xziel::SurvivalPowerUpKind::DoubleScore,
        .durationSeconds = 1.0f,
    };
    content.consumables[1] = {
        .id = 2002U,
        .effect = xziel::SurvivalConsumableEffect::FreeRandomWeapon,
        .powerUp = xziel::SurvivalPowerUpKind::FullAmmo,
        .durationSeconds = 0.0f,
    };
    content.consumableCount = 2U;

    content.stations[0] = {
        .id = 3001U,
        .kind = xziel::SurvivalStationKind::Perk,
        .position = {0.0f, 0.0f, 0.0f},
        .contentId = 101U,
    };
    content.stations[1] = {
        .id = 3002U,
        .kind = xziel::SurvivalStationKind::Perk,
        .position = {1.0f, 0.0f, 0.0f},
        .contentId = 102U,
    };
    content.stations[2] = {
        .id = 3003U,
        .kind = xziel::SurvivalStationKind::Perk,
        .position = {2.0f, 0.0f, 0.0f},
        .contentId = 103U,
    };
    content.stations[3] = {
        .id = 3010U,
        .kind = xziel::SurvivalStationKind::RandomWeapon,
        .position = {0.0f, 0.0f, 1.0f},
    };
    content.stations[4] = {
        .id = 3011U,
        .kind = xziel::SurvivalStationKind::WallWeapon,
        .position = {0.0f, 0.0f, 2.0f},
        .cost = 1200U,
        .contentId = 1001U,
    };
    content.stations[5] = {
        .id = 3012U,
        .kind = xziel::SurvivalStationKind::WeaponUpgrade,
        .position = {0.0f, 0.0f, 3.0f},
    };
    content.stations[6] = {
        .id = 3013U,
        .kind = xziel::SurvivalStationKind::Consumable,
        .position = {0.0f, 0.0f, 4.0f},
        .cost = 0U,
    };
    content.stationCount = 7U;

    xziel::SurvivalRuntime runtime;
    assert(runtime.load(content));

    xziel::InteractionSystem interactions;
    assert(runtime.registerInteractions(interactions));
    assert(interactions.targetCount() == 7U);

    xziel::ScoreSystem score({
        .startingPoints = 50000U,
    });
    xziel::GameplayEventQueue events;

    const auto fortitude =
        runtime.purchasePerk(3001U, score, &events);
    assert(fortitude.success);
    assert(runtime.hasPerk(101U));
    assert(runtime.modifiers().maxHealthScale == 1.5f);

    const auto quickHands =
        runtime.purchasePerk(3002U, score, &events);
    assert(quickHands.success);
    assert(runtime.modifiers().reloadTimeScale == 0.70f);

    const auto capped =
        runtime.purchasePerk(3003U, score, &events);
    assert(!capped.success);
    assert(capped.inventoryFull);

    const auto wall =
        runtime.purchaseWallWeapon(3011U, score, &events);
    assert(wall.success);
    assert(wall.contentId == 1001U);

    runtime.beginRound(8U);
    const auto box =
        runtime.spinRandomWeapon(3010U, score, &events);
    assert(box.success);
    assert(box.contentId == 1001U || box.contentId == 1002U);

    const auto upgraded =
        runtime.upgradeWeapon(
            3012U,
            box.contentId,
            0U,
            score,
            &events);
    assert(upgraded.success);
    assert(upgraded.newTier == 1U);
    assert(upgraded.cost == 5000U);

    const std::uint32_t deck[]{2001U};
    assert(runtime.setConsumableDeck(deck, 1U));

    const auto draw =
        runtime.drawConsumable(
            3013U,
            score,
            &events);
    assert(draw.success);
    assert(draw.contentId == 2001U);
    assert(runtime.heldConsumableCount() == 1U);

    assert(runtime.activateConsumable(0U, score, &events));
    assert(runtime.frame().scoreMultiplier == 2.0f);
    assert(runtime.scaledScoreAward(100U) == 200U);

    for (int i = 0; i < 8; ++i) {
        (void) runtime.step(0.25f);
    }
    assert(runtime.frame().scoreMultiplier == 1.0f);

    runtime.beginTick();
    const auto dropId =
        runtime.onZombieKilled(
            {3.0f, 0.0f, 4.0f},
            true,
            &events);
    assert(dropId != 0U);
    assert(runtime.frame().powerUpSpawnedThisTick);
    assert(runtime.collectPowerUp(dropId, score, &events));
    assert(runtime.frame().powerUpCollectedThisTick);

    xziel::GameplayEvent event{};
    bool sawPerk = false;
    bool sawWeapon = false;
    bool sawConsumable = false;
    bool sawPowerUp = false;

    while (events.pop(event)) {
        sawPerk = sawPerk ||
            event.type == xziel::GameplayEventType::PerkPurchased;
        sawWeapon = sawWeapon ||
            event.type == xziel::GameplayEventType::RandomWeaponRolled ||
            event.type == xziel::GameplayEventType::WonderWeaponAwarded;
        sawConsumable = sawConsumable ||
            event.type == xziel::GameplayEventType::ConsumableActivated;
        sawPowerUp = sawPowerUp ||
            event.type == xziel::GameplayEventType::PowerUpCollected;
    }

    assert(sawPerk);
    assert(sawWeapon);
    assert(sawConsumable);
    assert(sawPowerUp);

    return 0;
}
