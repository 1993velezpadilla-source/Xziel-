#include "xziel/net_protocol.hpp"

#include <array>
#include <cassert>
#include <cstddef>

int main() {
    std::array<std::byte, xziel::kNetMaxPacketBytes> buffer{};

    xziel::NetPacketHeader inputHeader{
        .type = xziel::NetMessageType::PlayerInput,
        .sequence = 77U,
    };

    xziel::NetPlayerInput input{
        .clientTick = 901U,
        .buttons =
            xziel::NetInputFire |
            xziel::NetInputSprint,
        .moveX = 1234,
        .moveY = -2234,
        .yawCentidegrees = 1211,
        .pitchCentidegrees = -322,
        .fireSequence = 12U,
        .interactId = 2001U,
    };

    std::size_t written = 0U;
    assert(
        xziel::encodeNetPlayerInput(
            inputHeader,
            input,
            buffer,
            written));
    assert(
        written ==
        xziel::kNetHeaderBytes +
            xziel::netPlayerInputPayloadBytes());

    xziel::NetPacketHeader decodedHeader{};
    xziel::NetPlayerInput decodedInput{};

    const auto decoded =
        xziel::decodeNetPlayerInput(
            std::span<const std::byte>(
                buffer.data(),
                written),
            decodedHeader,
            decodedInput);

    assert(decoded.success);
    assert(
        decoded.type ==
        xziel::NetMessageType::PlayerInput);
    assert(decodedHeader.sequence == 77U);
    assert(decodedInput.clientTick == 901U);
    assert(decodedInput.buttons == input.buttons);
    assert(decodedInput.moveX == 1234);
    assert(decodedInput.moveY == -2234);
    assert(decodedInput.interactId == 2001U);

    xziel::NetWorldSnapshot snapshot{};
    snapshot.serverTick = 5000U;
    snapshot.ackInputSequence = 77U;
    snapshot.round = 9U;
    snapshot.playerCount =
        xziel::kOnlineMaxPlayers;
    snapshot.zombieCount = 2U;

    for (std::uint8_t i = 0U;
         i < xziel::kOnlineMaxPlayers;
         ++i) {
        auto& player =
            snapshot.players[i];

        player.playerId = i;
        player.health =
            static_cast<std::uint16_t>(
                100U - i * 10U);
        player.points =
            1000U + i * 250U;
        player.xMillimeters =
            static_cast<std::int32_t>(
                i) * 1100;
        player.zMillimeters =
            static_cast<std::int32_t>(
                i) * -900;
        player.weaponId =
            static_cast<std::uint16_t>(
                10U + i);
        player.ammo =
            static_cast<std::uint16_t>(
                60U - i);
    }

    snapshot.zombies[0] = {
        .zombieId = 4U,
        .state = 2U,
        .targetPlayerId = 1U,
        .health = 80U,
        .xMillimeters = 2200,
        .yMillimeters = -1480,
        .zMillimeters = 3300,
        .yawCentidegrees = 9000,
    };

    snapshot.zombies[1] = {
        .zombieId = 5U,
        .state = 3U,
        .targetPlayerId = 3U,
        .health = 25U,
        .xMillimeters = -1400,
        .yMillimeters = -1480,
        .zMillimeters = 800,
        .yawCentidegrees = -4500,
    };

    xziel::NetPacketHeader snapshotHeader{
        .type = xziel::NetMessageType::Snapshot,
        .sequence = 88U,
    };

    written = 0U;
    assert(
        xziel::encodeNetSnapshot(
            snapshotHeader,
            snapshot,
            buffer,
            written));
    assert(
        written <=
        xziel::kNetMaxPacketBytes);

    xziel::NetWorldSnapshot decodedSnapshot{};
    decodedHeader = {};

    const auto snapshotDecoded =
        xziel::decodeNetSnapshot(
            std::span<const std::byte>(
                buffer.data(),
                written),
            decodedHeader,
            decodedSnapshot);

    assert(snapshotDecoded.success);
    assert(decodedHeader.sequence == 88U);
    assert(decodedSnapshot.serverTick == 5000U);
    assert(decodedSnapshot.round == 9U);
    assert(
        decodedSnapshot.playerCount ==
        xziel::kOnlineMaxPlayers);
    assert(decodedSnapshot.zombieCount == 2U);
    assert(
        decodedSnapshot.players[3].points ==
        1750U);
    assert(
        decodedSnapshot.zombies[1].
            targetPlayerId == 3U);

    // Four players plus the protocol zombie envelope must remain under the
    // transport-neutral 1200-byte ceiling so the same codec can later move
    // from WebSocket to UDP/QUIC without fragmentation.
    xziel::NetWorldSnapshot maximum{};
    maximum.playerCount =
        xziel::kOnlineMaxPlayers;
    maximum.zombieCount =
        xziel::kOnlineMaxReplicatedZombies;

    assert(
        xziel::kNetHeaderBytes +
            xziel::netSnapshotPayloadBytes(
                maximum) <=
        xziel::kNetMaxPacketBytes);

    return 0;
}
