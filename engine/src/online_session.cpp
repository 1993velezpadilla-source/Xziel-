#include "xziel/online_session.hpp"

namespace xziel {

void OnlineSession::reset() noexcept {
    state_ = OnlineSessionState::Offline;
    localPlayerId_ = 0xFFU;
    maxPlayers_ = kOnlineMaxPlayers;
    nextInputSequence_ = 1U;
    latestSnapshot_ = {};
    stats_ = {};
}

void OnlineSession::beginConnect() noexcept {
    localPlayerId_ = 0xFFU;
    latestSnapshot_ = {};
    state_ = OnlineSessionState::Connecting;
}

void OnlineSession::setTransportState(
    int transportState) noexcept {
    switch (transportState) {
    case 1:
        if (state_ !=
            OnlineSessionState::Ready) {
            state_ =
                OnlineSessionState::Connecting;
        }
        break;

    case 2:
        if (state_ !=
            OnlineSessionState::Ready) {
            state_ =
                OnlineSessionState::
                    TransportConnected;
        }
        break;

    case 3:
        state_ = OnlineSessionState::Failed;
        break;

    default:
        if (state_ !=
            OnlineSessionState::Offline) {
            state_ =
                OnlineSessionState::Offline;
            localPlayerId_ = 0xFFU;
        }
        break;
    }
}

bool OnlineSession::consumePacket(
    std::span<const std::byte> packet) noexcept {
    if (packet.size() <
        kNetHeaderBytes ||
        packet.size() >
        kNetMaxPacketBytes) {
        ++stats_.invalidPackets;
        return false;
    }

    ++stats_.packetsReceived;

    const std::uint8_t type =
        std::to_integer<std::uint8_t>(
            packet[3]);

    if (type ==
        static_cast<std::uint8_t>(
            NetMessageType::Welcome)) {
        NetPacketHeader header{};
        NetWelcome welcome{};

        const auto decoded =
            decodeNetWelcome(
                packet,
                header,
                welcome);

        if (!decoded.success) {
            ++stats_.invalidPackets;
            return false;
        }

        localPlayerId_ =
            welcome.playerId;
        maxPlayers_ =
            welcome.maxPlayers;
        stats_.lastServerTick =
            welcome.serverTick;
        state_ =
            OnlineSessionState::Ready;
        return true;
    }

    if (type ==
        static_cast<std::uint8_t>(
            NetMessageType::Snapshot)) {
        NetPacketHeader header{};
        NetWorldSnapshot snapshot{};

        const auto decoded =
            decodeNetSnapshot(
                packet,
                header,
                snapshot);

        if (!decoded.success) {
            ++stats_.invalidPackets;
            return false;
        }

        if (snapshot.playerCount >
            maxPlayers_) {
            ++stats_.invalidPackets;
            return false;
        }

        latestSnapshot_ =
            snapshot;
        stats_.lastServerTick =
            snapshot.serverTick;
        ++stats_.snapshotsReceived;

        if (localPlayerId_ != 0xFFU) {
            state_ =
                OnlineSessionState::Ready;
        }

        return true;
    }

    ++stats_.invalidPackets;
    return false;
}

bool OnlineSession::buildInputPacket(
    NetPlayerInput input,
    std::span<std::byte> destination,
    std::size_t& written) noexcept {
    written = 0U;

    if (!ready()) {
        return false;
    }

    const std::uint16_t sequence =
        nextInputSequence_++;

    if (nextInputSequence_ == 0U) {
        nextInputSequence_ = 1U;
    }

    const NetPacketHeader header{
        .type =
            NetMessageType::PlayerInput,
        .sequence = sequence,
    };

    if (!encodeNetPlayerInput(
            header,
            input,
            destination,
            written)) {
        return false;
    }

    stats_.lastInputSequence =
        sequence;
    return true;
}

OnlineSessionState OnlineSession::state() const noexcept {
    return state_;
}

bool OnlineSession::ready() const noexcept {
    return
        state_ == OnlineSessionState::Ready &&
        localPlayerId_ <
            kOnlineMaxPlayers;
}

std::uint8_t OnlineSession::localPlayerId() const noexcept {
    return localPlayerId_;
}

std::uint8_t OnlineSession::playerCount() const noexcept {
    return latestSnapshot_.playerCount;
}

const NetWorldSnapshot&
OnlineSession::latestSnapshot() const noexcept {
    return latestSnapshot_;
}

const OnlineSessionStats&
OnlineSession::stats() const noexcept {
    return stats_;
}

} // namespace xziel
