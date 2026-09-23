#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace xziel {

inline constexpr std::uint8_t kOnlineMaxPlayers = 4U;
inline constexpr std::uint8_t kOnlineMaxReplicatedZombies = 24U;

inline constexpr std::uint16_t kNetProtocolMagic = 0x5A58U; // "XZ"
inline constexpr std::uint8_t kNetProtocolVersion = 1U;
inline constexpr std::size_t kNetHeaderBytes = 8U;
inline constexpr std::size_t kNetMaxPacketBytes = 1200U;

inline constexpr std::uint32_t kNetServerTickHz = 20U;
inline constexpr std::uint32_t kNetClientInputHz = 30U;
inline constexpr std::uint32_t kNetSnapshotHz = 20U;
inline constexpr std::uint32_t kNetInterpolationDelayMs = 100U;
inline constexpr std::uint32_t kNetDisconnectTimeoutMs = 8000U;

enum class NetMessageType : std::uint8_t {
    Invalid = 0U,
    Hello = 1U,
    Welcome = 2U,
    PlayerInput = 3U,
    Snapshot = 4U,
    GameplayEvent = 5U,
    Ping = 6U,
    Pong = 7U,
    Disconnect = 8U,
};

enum NetInputButtons : std::uint16_t {
    NetInputFire = 1U << 0U,
    NetInputAim = 1U << 1U,
    NetInputReload = 1U << 2U,
    NetInputInteract = 1U << 3U,
    NetInputJump = 1U << 4U,
    NetInputSprint = 1U << 5U,
    NetInputCrouch = 1U << 6U,
    NetInputMelee = 1U << 7U,
};

struct NetPacketHeader {
    NetMessageType type = NetMessageType::Invalid;
    std::uint16_t sequence = 0U;
    std::uint16_t payloadBytes = 0U;
};

struct NetWelcome {
    std::uint8_t playerId = 0U;
    std::uint8_t maxPlayers = kOnlineMaxPlayers;
    std::uint32_t serverTick = 0U;
};

struct NetPlayerInput {
    std::uint32_t clientTick = 0U;
    std::uint16_t buttons = 0U;
    std::int16_t moveX = 0;
    std::int16_t moveY = 0;
    std::int16_t yawCentidegrees = 0;
    std::int16_t pitchCentidegrees = 0;
    std::uint16_t fireSequence = 0U;
    std::uint16_t interactId = 0U;
};

struct NetPlayerSnapshot {
    std::uint8_t playerId = 0U;
    std::uint8_t flags = 0U;
    std::uint16_t health = 0U;
    std::uint32_t points = 0U;
    std::int32_t xMillimeters = 0;
    std::int32_t yMillimeters = 0;
    std::int32_t zMillimeters = 0;
    std::int16_t yawCentidegrees = 0;
    std::int16_t pitchCentidegrees = 0;
    std::uint16_t weaponId = 0U;
    std::uint16_t ammo = 0U;
};

struct NetZombieSnapshot {
    std::uint16_t zombieId = 0U;
    std::uint8_t state = 0U;
    std::uint8_t targetPlayerId = 0U;
    std::uint16_t health = 0U;
    std::int32_t xMillimeters = 0;
    std::int32_t yMillimeters = 0;
    std::int32_t zMillimeters = 0;
    std::int16_t yawCentidegrees = 0;
};

struct NetWorldSnapshot {
    std::uint32_t serverTick = 0U;
    std::uint16_t ackInputSequence = 0U;
    std::uint16_t round = 1U;
    std::uint8_t playerCount = 0U;
    std::uint8_t zombieCount = 0U;
    std::array<NetPlayerSnapshot, kOnlineMaxPlayers> players{};
    std::array<NetZombieSnapshot, kOnlineMaxReplicatedZombies> zombies{};
};

struct NetDecodeResult {
    bool success = false;
    NetMessageType type = NetMessageType::Invalid;
    std::size_t bytesConsumed = 0U;
};

[[nodiscard]] std::size_t netWelcomePayloadBytes() noexcept;
[[nodiscard]] std::size_t netPlayerInputPayloadBytes() noexcept;
[[nodiscard]] std::size_t netSnapshotPayloadBytes(
    const NetWorldSnapshot& snapshot) noexcept;

[[nodiscard]] NetDecodeResult decodeNetWelcome(
    std::span<const std::byte> bytes,
    NetPacketHeader& header,
    NetWelcome& welcome) noexcept;

[[nodiscard]] bool encodeNetPlayerInput(
    const NetPacketHeader& header,
    const NetPlayerInput& input,
    std::span<std::byte> destination,
    std::size_t& written) noexcept;

[[nodiscard]] NetDecodeResult decodeNetPlayerInput(
    std::span<const std::byte> bytes,
    NetPacketHeader& header,
    NetPlayerInput& input) noexcept;

[[nodiscard]] bool encodeNetSnapshot(
    const NetPacketHeader& header,
    const NetWorldSnapshot& snapshot,
    std::span<std::byte> destination,
    std::size_t& written) noexcept;

[[nodiscard]] NetDecodeResult decodeNetSnapshot(
    std::span<const std::byte> bytes,
    NetPacketHeader& header,
    NetWorldSnapshot& snapshot) noexcept;

} // namespace xziel
