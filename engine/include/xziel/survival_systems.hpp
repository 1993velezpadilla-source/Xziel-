#pragma once

#include "xziel/gameplay_events.hpp"
#include "xziel/interaction.hpp"
#include "xziel/score.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

inline constexpr std::size_t kMaxSurvivalPerks = 12;
inline constexpr std::size_t kMaxSurvivalStations = 64;
inline constexpr std::size_t kMaxSurvivalWeaponPool = 64;
inline constexpr std::size_t kMaxSurvivalConsumables = 32;
inline constexpr std::size_t kMaxSurvivalConsumableDeck = 5;
inline constexpr std::size_t kMaxSurvivalHeldConsumables = 3;
inline constexpr std::size_t kMaxSurvivalPowerUpDrops = 16;

enum class SurvivalStationKind : std::uint8_t {
    Perk,
    RandomWeapon,
    WallWeapon,
    WeaponUpgrade,
    Consumable,
};

enum class SurvivalPerkEffect : std::uint8_t {
    Fortitude,
    QuickHands,
    Endurance,
    SecondChance,
    RapidFire,
    Precision,
    Arsenal,
    BlastGuard,
};

enum class SurvivalPowerUpKind : std::uint8_t {
    FullAmmo,
    OneHit,
    DoubleScore,
    WaveClear,
    RepairAll,
    Discount,
    HeavyWeapon,
    RandomPerk,
    FullHealth,
    Count,
};

enum class SurvivalConsumableEffect : std::uint8_t {
    GrantPowerUp,
    GrantRandomPerk,
    GrantAllPerks,
    FreeRandomWeapon,
    FreeWeaponUpgrade,
    Veil,
    TimeFreeze,
};

struct SurvivalRules {
    std::uint32_t perkLimit = 4;
    std::uint32_t randomWeaponBaseCost = 950;
    std::uint32_t weaponUpgradeBaseCost = 5000;
    float weaponUpgradeCostMultiplier = 2.0f;
    std::uint32_t consumableDrawCostStep = 500;
    std::uint32_t maxWeaponUpgradeTier = 3;

    float powerUpLifetimeSeconds = 12.0f;
    float timedPowerUpSeconds = 30.0f;
    float dropBaseChance = 0.035f;
    std::uint32_t dropPityKills = 28;
    float dropCooldownSeconds = 8.0f;
};

struct SurvivalPerkDefinition {
    std::uint32_t id = 0;
    SurvivalPerkEffect effect = SurvivalPerkEffect::Fortitude;
    std::uint32_t cost = 2500;
    float magnitude = 1.0f;
    bool enabled = true;
};

struct SurvivalWeaponPoolEntry {
    std::uint32_t weaponId = 0;
    std::uint32_t weight = 1;
    std::uint32_t minimumRound = 1;
    std::uint32_t maximumRound = 0;
    bool wonderWeapon = false;
    bool enabled = true;
};

struct SurvivalConsumableDefinition {
    std::uint32_t id = 0;
    SurvivalConsumableEffect effect =
        SurvivalConsumableEffect::GrantPowerUp;
    SurvivalPowerUpKind powerUp =
        SurvivalPowerUpKind::FullAmmo;
    float durationSeconds = 0.0f;
    std::uint32_t weight = 1;
    bool enabled = true;
};

struct SurvivalStationDefinition {
    std::uint32_t id = 0;
    SurvivalStationKind kind = SurvivalStationKind::Perk;
    Vec3 position{};
    std::uint32_t cost = 0;
    std::uint32_t contentId = 0;

    float maximumDistance = 1.75f;
    float minimumFacingDot = 0.20f;
    float priority = 1.0f;
    float holdSeconds = 0.10f;
    bool enabled = true;
};

struct SurvivalContentDefinition {
    SurvivalRules rules{};

    std::array<SurvivalPerkDefinition, kMaxSurvivalPerks> perks{};
    std::size_t perkCount = 0;

    std::array<SurvivalWeaponPoolEntry, kMaxSurvivalWeaponPool>
        weaponPool{};
    std::size_t weaponPoolCount = 0;

    std::array<SurvivalConsumableDefinition, kMaxSurvivalConsumables>
        consumables{};
    std::size_t consumableCount = 0;

    std::array<SurvivalStationDefinition, kMaxSurvivalStations>
        stations{};
    std::size_t stationCount = 0;
};

struct SurvivalModifiers {
    float maxHealthScale = 1.0f;
    float reloadTimeScale = 1.0f;
    float moveSpeedScale = 1.0f;
    float reviveTimeScale = 1.0f;
    float fireIntervalScale = 1.0f;
    float headshotDamageScale = 1.0f;
    float explosiveDamageScale = 1.0f;
    std::uint32_t extraWeaponSlots = 0;
};

struct SurvivalTransaction {
    bool success = false;
    bool insufficientFunds = false;
    bool inventoryFull = false;

    std::uint32_t stationId = 0;
    std::uint32_t contentId = 0;
    std::uint32_t cost = 0;
    std::uint32_t newTier = 0;

    bool wonderWeapon = false;
};

struct SurvivalPowerUpDrop {
    std::uint32_t id = 0;
    SurvivalPowerUpKind kind = SurvivalPowerUpKind::FullAmmo;
    Vec3 position{};
    float remainingSeconds = 0.0f;
    bool active = false;
};

struct SurvivalFrame {
    std::uint32_t round = 1;
    std::array<float, static_cast<std::size_t>(
        SurvivalPowerUpKind::Count)> powerUpSeconds{};

    float scoreMultiplier = 1.0f;
    float veilSeconds = 0.0f;
    float freezeHordeSeconds = 0.0f;

    bool oneHitDamage = false;
    bool discountActive = false;
    bool heavyWeaponActive = false;
    bool zombiesIgnorePlayer = false;
    bool hordeFrozen = false;

    bool refillAmmoThisTick = false;
    bool repairAllThisTick = false;
    bool clearWaveThisTick = false;
    bool fullHealThisTick = false;
    bool heavyWeaponGrantedThisTick = false;
    bool powerUpSpawnedThisTick = false;
    bool powerUpCollectedThisTick = false;

    std::uint32_t lastDropId = 0;
    SurvivalPowerUpKind lastPowerUp =
        SurvivalPowerUpKind::FullAmmo;
};

class SurvivalRuntime final {
public:
    [[nodiscard]] bool load(
        const SurvivalContentDefinition& definition) noexcept;

    void reset(
        std::uint32_t seed = 0x5A17C7U) noexcept;

    void beginTick() noexcept;
    void beginRound(std::uint32_t round) noexcept;

    [[nodiscard]] bool registerInteractions(
        InteractionSystem& interactions) const noexcept;

    [[nodiscard]] bool setConsumableDeck(
        const std::uint32_t* ids,
        std::size_t count) noexcept;

    [[nodiscard]] SurvivalTransaction purchasePerk(
        std::uint32_t stationId,
        ScoreSystem& score,
        GameplayEventQueue* events = nullptr) noexcept;

    [[nodiscard]] SurvivalTransaction purchaseWallWeapon(
        std::uint32_t stationId,
        ScoreSystem& score,
        GameplayEventQueue* events = nullptr) noexcept;

    [[nodiscard]] SurvivalTransaction spinRandomWeapon(
        std::uint32_t stationId,
        ScoreSystem& score,
        GameplayEventQueue* events = nullptr) noexcept;

    [[nodiscard]] SurvivalTransaction upgradeWeapon(
        std::uint32_t stationId,
        std::uint32_t weaponId,
        std::uint32_t currentTier,
        ScoreSystem& score,
        GameplayEventQueue* events = nullptr) noexcept;

    [[nodiscard]] SurvivalTransaction drawConsumable(
        std::uint32_t stationId,
        ScoreSystem& score,
        GameplayEventQueue* events = nullptr) noexcept;

    [[nodiscard]] bool activateConsumable(
        std::size_t heldSlot,
        ScoreSystem& score,
        GameplayEventQueue* events = nullptr) noexcept;

    [[nodiscard]] std::uint32_t onZombieKilled(
        Vec3 position,
        bool eligible,
        GameplayEventQueue* events = nullptr) noexcept;

    [[nodiscard]] bool collectPowerUp(
        std::uint32_t dropId,
        ScoreSystem& score,
        GameplayEventQueue* events = nullptr) noexcept;

    [[nodiscard]] SurvivalFrame step(
        float deltaSeconds) noexcept;

    [[nodiscard]] bool hasPerk(
        std::uint32_t perkId) const noexcept;

    [[nodiscard]] std::size_t perkCount() const noexcept;
    [[nodiscard]] std::size_t heldConsumableCount() const noexcept;
    [[nodiscard]] std::uint32_t heldConsumable(
        std::size_t slot) const noexcept;

    [[nodiscard]] std::uint32_t scaledScoreAward(
        std::uint32_t baseAward) const noexcept;

    [[nodiscard]] const SurvivalModifiers& modifiers() const noexcept;
    [[nodiscard]] const SurvivalFrame& frame() const noexcept;
    [[nodiscard]] const SurvivalContentDefinition& content() const noexcept;
    [[nodiscard]] const std::array<
        SurvivalPowerUpDrop,
        kMaxSurvivalPowerUpDrops>& drops() const noexcept;

private:
    [[nodiscard]] const SurvivalStationDefinition* station(
        std::uint32_t id) const noexcept;
    [[nodiscard]] const SurvivalPerkDefinition* perk(
        std::uint32_t id) const noexcept;
    [[nodiscard]] const SurvivalConsumableDefinition* consumable(
        std::uint32_t id) const noexcept;

    [[nodiscard]] std::uint32_t effectiveStationCost(
        const SurvivalStationDefinition& station) const noexcept;
    [[nodiscard]] std::uint32_t upgradeCost(
        const SurvivalStationDefinition& station,
        std::uint32_t currentTier) const noexcept;

    [[nodiscard]] std::uint32_t chooseWeapon() noexcept;
    [[nodiscard]] std::uint32_t chooseConsumable() noexcept;
    [[nodiscard]] SurvivalPowerUpKind choosePowerUp() noexcept;
    [[nodiscard]] float random01() noexcept;

    [[nodiscard]] bool grantPerk(
        std::uint32_t perkId,
        bool ignoreLimit) noexcept;
    [[nodiscard]] bool grantRandomPerk(
        bool ignoreLimit) noexcept;

    void applyPowerUp(
        SurvivalPowerUpKind kind) noexcept;
    void updateDerivedFrame() noexcept;
    void recomputeModifiers() noexcept;

    void emit(
        GameplayEventQueue* events,
        GameplayEventType type,
        std::uint32_t subjectId,
        std::uint32_t actorId = 0,
        std::uint32_t amount = 0,
        float value = 0.0f) const noexcept;

    SurvivalContentDefinition content_{};
    SurvivalModifiers modifiers_{};
    SurvivalFrame frame_{};

    std::array<std::uint32_t, kMaxSurvivalPerks> ownedPerks_{};
    std::size_t ownedPerkCount_ = 0;

    std::array<std::uint32_t, kMaxSurvivalConsumableDeck>
        consumableDeck_{};
    std::size_t consumableDeckCount_ = 0;

    std::array<std::uint32_t, kMaxSurvivalHeldConsumables>
        heldConsumables_{};
    std::size_t heldConsumableCount_ = 0;

    std::array<SurvivalPowerUpDrop, kMaxSurvivalPowerUpDrops>
        drops_{};

    std::uint32_t randomState_ = 0x5A17C7U;
    std::uint32_t nextDropId_ = 1;
    std::uint32_t killsSinceDrop_ = 0;
    std::uint32_t consumableDrawsThisRound_ = 0;
    std::uint32_t freeRandomWeaponSpins_ = 0;
    std::uint32_t freeWeaponUpgrades_ = 0;

    float dropCooldownSeconds_ = 0.0f;
    float veilSeconds_ = 0.0f;
    float freezeHordeSeconds_ = 0.0f;

    bool loaded_ = false;
};

} // namespace xziel
