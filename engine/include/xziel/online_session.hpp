#pragma once

#include "xziel/net_protocol.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace xziel {

enum class OnlineSessionState : std::uint8_t {
    Offline,
    Connecting,
    TransportConnected,
    Ready,
    Failed,
};

struct OnlineSessionStats {
    std::uint64_t packetsReceived = 0U;
    std::uint64_t snapshotsReceived = 0U;
    std::uint64_t invalidPackets = 0U;
    std::uint16_t lastInputSequence = 0U;
    std::uint32_t lastServerTick = 0U;
};

class OnlineSession final {
public:
    void reset() noexcept;

    void beginConnect() noexcept;

    void setTransportState(
        int transportState) noexcept;

    [[nodiscard]] bool consumePacket(
        std::span<const std::byte> packet) noexcept;

    [[nodiscard]] bool buildInputPacket(
        NetPlayerInput input,
        std::span<std::byte> destination,
        std::size_t& written) noexcept;

    [[nodiscard]] OnlineSessionState state() const noexcept;
    [[nodiscard]] bool ready() const noexcept;
    [[nodiscard]] std::uint8_t localPlayerId() const noexcept;
    [[nodiscard]] std::uint8_t playerCount() const noexcept;
    [[nodiscard]] const NetWorldSnapshot& latestSnapshot() const noexcept;
    [[nodiscard]] const OnlineSessionStats& stats() const noexcept;

private:
    OnlineSessionState state_ =
        OnlineSessionState::Offline;

    std::uint8_t localPlayerId_ = 0xFFU;
    std::uint8_t maxPlayers_ =
        kOnlineMaxPlayers;

    std::uint16_t nextInputSequence_ = 1U;

    NetWorldSnapshot latestSnapshot_{};
    OnlineSessionStats stats_{};
};

} // namespace xziel
