#include "xziel/online_session.hpp"

#include <array>
#include <cassert>
#include <cstddef>

namespace {

std::array<std::byte, 14> welcomePacket(
    std::uint8_t playerId,
    std::uint32_t serverTick) {
    std::array<std::byte, 14> bytes{};

    auto put8 =
        [&](std::size_t offset,
            std::uint8_t value) {
            bytes[offset] =
                static_cast<std::byte>(value);
        };

    auto put16 =
        [&](std::size_t offset,
            std::uint16_t value) {
            put8(
                offset,
                static_cast<std::uint8_t>(
                    value & 0xFFU));
            put8(
                offset + 1U,
                static_cast<std::uint8_t>(
                    (value >> 8U) & 0xFFU));
        };

    auto put32 =
        [&](std::size_t offset,
            std::uint32_t value) {
            put16(
                offset,
                static_cast<std::uint16_t>(
                    value & 0xFFFFU));
            put16(
                offset + 2U,
                static_cast<std::uint16_t>(
                    (value >> 16U) &
                    0xFFFFU));
        };

    put16(0U, xziel::kNetProtocolMagic);
    put8(2U, xziel::kNetProtocolVersion);
    put8(
        3U,
        static_cast<std::uint8_t>(
            xziel::NetMessageType::Welcome));
    put16(4U, 0U);
    put16(
        6U,
        static_cast<std::uint16_t>(
            xziel::netWelcomePayloadBytes()));
    put8(8U, playerId);
    put8(9U, xziel::kOnlineMaxPlayers);
    put32(10U, serverTick);

    return bytes;
}

} // namespace

int main() {
    xziel::OnlineSession session;
    session.beginConnect();

    assert(
        session.state() ==
        xziel::OnlineSessionState::
            Connecting);
    assert(!session.ready());

    session.setTransportState(2);

    assert(
        session.state() ==
        xziel::OnlineSessionState::
            TransportConnected);

    const auto welcome =
        welcomePacket(2U, 900U);

    assert(
        session.consumePacket(
            std::span<const std::byte>(
                welcome.data(),
                welcome.size())));

    assert(session.ready());
    assert(session.localPlayerId() == 2U);

    xziel::NetPlayerInput input{
        .clientTick = 20U,
        .buttons = xziel::NetInputFire,
        .moveX = 1000,
        .moveY = 2000,
        .yawCentidegrees = 4500,
        .pitchCentidegrees = -300,
        .fireSequence = 2U,
    };

    std::array<
        std::byte,
        xziel::kNetMaxPacketBytes> packet{};

    std::size_t written = 0U;

    assert(
        session.buildInputPacket(
            input,
            packet,
            written));

    xziel::NetPacketHeader inputHeader{};
    xziel::NetPlayerInput inputDecoded{};

    const auto inputResult =
        xziel::decodeNetPlayerInput(
            std::span<const std::byte>(
                packet.data(),
                written),
            inputHeader,
            inputDecoded);

    assert(inputResult.success);
    assert(inputHeader.sequence == 1U);
    assert(inputDecoded.clientTick == 20U);

    xziel::NetWorldSnapshot snapshot{};
    snapshot.serverTick = 901U;
    snapshot.round = 2U;
    snapshot.playerCount = 4U;

    for (std::uint8_t i = 0U;
         i < snapshot.playerCount;
         ++i) {
        snapshot.players[i].playerId = i;
        snapshot.players[i].health =
            static_cast<std::uint16_t>(
                100U - i * 5U);
        snapshot.players[i].points =
            500U + i * 100U;
    }

    const xziel::NetPacketHeader snapshotHeader{
        .type =
            xziel::NetMessageType::Snapshot,
        .sequence = 22U,
    };

    written = 0U;
    assert(
        xziel::encodeNetSnapshot(
            snapshotHeader,
            snapshot,
            packet,
            written));

    assert(
        session.consumePacket(
            std::span<const std::byte>(
                packet.data(),
                written)));

    assert(session.playerCount() == 4U);
    assert(
        session.latestSnapshot().
            players[3].points == 800U);
    assert(
        session.stats().
            snapshotsReceived == 1U);

    return 0;
}
