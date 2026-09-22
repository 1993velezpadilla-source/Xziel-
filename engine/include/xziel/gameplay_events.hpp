#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

enum class GameplayEventType : std::uint8_t {
    None,
    RoundStarted,
    RoundCompleted,
    ZombieSpawned,
    ZombieKilled,
    ZombieHeadshot,
    DoorOpened,
    WindowBreached,
    PlankRebuilt,
    WindowFullyRebuilt,
    PowerStateChanged,
    PurchaseCompleted,
    PerkPurchased,
    RandomWeaponRolled,
    WallWeaponPurchased,
    WeaponUpgraded,
    WonderWeaponAwarded,
    ConsumableDispensed,
    ConsumableActivated,
    PowerUpSpawned,
    PowerUpCollected,
    PlayerDamaged,
    PlayerDowned,
    PlayerRevived,
    InteractionActivated,
    QuestItemCollected,
    ScriptSignal,
};

struct GameplayEvent {
    GameplayEventType type = GameplayEventType::None;
    std::uint32_t subjectId = 0;
    std::uint32_t actorId = 0;
    std::uint32_t amount = 0;
    float value = 0.0f;
    std::uint64_t simulationTick = 0;
};

inline constexpr std::size_t kGameplayEventCapacity = 128;

class GameplayEventQueue final {
public:
    void clear() noexcept;

    [[nodiscard]] bool push(
        const GameplayEvent& event) noexcept;

    [[nodiscard]] bool pop(
        GameplayEvent& destination) noexcept;

    [[nodiscard]] std::size_t size() const noexcept;
    [[nodiscard]] bool empty() const noexcept;
    [[nodiscard]] std::uint64_t droppedCount() const noexcept;

private:
    std::array<GameplayEvent, kGameplayEventCapacity> events_{};
    std::size_t read_ = 0;
    std::size_t write_ = 0;
    std::size_t size_ = 0;
    std::uint64_t dropped_ = 0;
};

} // namespace xziel
