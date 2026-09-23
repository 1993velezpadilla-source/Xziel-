#include "xziel/net_protocol.hpp"

#include <algorithm>
#include <limits>

namespace xziel {

namespace {

class Writer final {
public:
    explicit Writer(std::span<std::byte> bytes) noexcept
        : bytes_(bytes) {}

    bool u8(std::uint8_t value) noexcept {
        return put(value);
    }

    bool u16(std::uint16_t value) noexcept {
        return
            put(static_cast<std::uint8_t>(value & 0xFFU)) &&
            put(static_cast<std::uint8_t>((value >> 8U) & 0xFFU));
    }

    bool i16(std::int16_t value) noexcept {
        return u16(static_cast<std::uint16_t>(value));
    }

    bool u32(std::uint32_t value) noexcept {
        return
            put(static_cast<std::uint8_t>(value & 0xFFU)) &&
            put(static_cast<std::uint8_t>((value >> 8U) & 0xFFU)) &&
            put(static_cast<std::uint8_t>((value >> 16U) & 0xFFU)) &&
            put(static_cast<std::uint8_t>((value >> 24U) & 0xFFU));
    }

    bool i32(std::int32_t value) noexcept {
        return u32(static_cast<std::uint32_t>(value));
    }

    [[nodiscard]] std::size_t offset() const noexcept {
        return offset_;
    }

private:
    bool put(std::uint8_t value) noexcept {
        if (offset_ >= bytes_.size()) {
            return false;
        }

        bytes_[offset_++] =
            static_cast<std::byte>(value);
        return true;
    }

    std::span<std::byte> bytes_{};
    std::size_t offset_ = 0U;
};

class Reader final {
public:
    explicit Reader(
        std::span<const std::byte> bytes) noexcept
        : bytes_(bytes) {}

    bool u8(std::uint8_t& value) noexcept {
        if (offset_ >= bytes_.size()) {
            return false;
        }

        value =
            std::to_integer<std::uint8_t>(
                bytes_[offset_++]);
        return true;
    }

    bool u16(std::uint16_t& value) noexcept {
        std::uint8_t a = 0U;
        std::uint8_t b = 0U;

        if (!u8(a) || !u8(b)) {
            return false;
        }

        value =
            static_cast<std::uint16_t>(a) |
            (static_cast<std::uint16_t>(b) << 8U);
        return true;
    }

    bool i16(std::int16_t& value) noexcept {
        std::uint16_t raw = 0U;
        if (!u16(raw)) {
            return false;
        }
        value = static_cast<std::int16_t>(raw);
        return true;
    }

    bool u32(std::uint32_t& value) noexcept {
        std::uint8_t a = 0U;
        std::uint8_t b = 0U;
        std::uint8_t c = 0U;
        std::uint8_t d = 0U;

        if (!u8(a) || !u8(b) || !u8(c) || !u8(d)) {
            return false;
        }

        value =
            static_cast<std::uint32_t>(a) |
            (static_cast<std::uint32_t>(b) << 8U) |
            (static_cast<std::uint32_t>(c) << 16U) |
            (static_cast<std::uint32_t>(d) << 24U);
        return true;
    }

    bool i32(std::int32_t& value) noexcept {
        std::uint32_t raw = 0U;
        if (!u32(raw)) {
            return false;
        }
        value = static_cast<std::int32_t>(raw);
        return true;
    }

    [[nodiscard]] std::size_t offset() const noexcept {
        return offset_;
    }

private:
    std::span<const std::byte> bytes_{};
    std::size_t offset_ = 0U;
};

bool writeHeader(
    Writer& writer,
    const NetPacketHeader& header,
    std::uint16_t payloadBytes) noexcept {
    return
        writer.u16(kNetProtocolMagic) &&
        writer.u8(kNetProtocolVersion) &&
        writer.u8(
            static_cast<std::uint8_t>(
                header.type)) &&
        writer.u16(header.sequence) &&
        writer.u16(payloadBytes);
}

bool readHeader(
    Reader& reader,
    NetPacketHeader& header) noexcept {
    std::uint16_t magic = 0U;
    std::uint8_t version = 0U;
    std::uint8_t type = 0U;

    if (!reader.u16(magic) ||
        !reader.u8(version) ||
        !reader.u8(type) ||
        !reader.u16(header.sequence) ||
        !reader.u16(header.payloadBytes)) {
        return false;
    }

    if (magic != kNetProtocolMagic ||
        version != kNetProtocolVersion) {
        return false;
    }

    header.type =
        static_cast<NetMessageType>(type);
    return true;
}

bool writePlayerSnapshot(
    Writer& writer,
    const NetPlayerSnapshot& value) noexcept {
    return
        writer.u8(value.playerId) &&
        writer.u8(value.flags) &&
        writer.u16(value.health) &&
        writer.u32(value.points) &&
        writer.i32(value.xMillimeters) &&
        writer.i32(value.yMillimeters) &&
        writer.i32(value.zMillimeters) &&
        writer.i16(value.yawCentidegrees) &&
        writer.i16(value.pitchCentidegrees) &&
        writer.u16(value.weaponId) &&
        writer.u16(value.ammo);
}

bool readPlayerSnapshot(
    Reader& reader,
    NetPlayerSnapshot& value) noexcept {
    return
        reader.u8(value.playerId) &&
        reader.u8(value.flags) &&
        reader.u16(value.health) &&
        reader.u32(value.points) &&
        reader.i32(value.xMillimeters) &&
        reader.i32(value.yMillimeters) &&
        reader.i32(value.zMillimeters) &&
        reader.i16(value.yawCentidegrees) &&
        reader.i16(value.pitchCentidegrees) &&
        reader.u16(value.weaponId) &&
        reader.u16(value.ammo);
}

bool writeZombieSnapshot(
    Writer& writer,
    const NetZombieSnapshot& value) noexcept {
    return
        writer.u16(value.zombieId) &&
        writer.u8(value.state) &&
        writer.u8(value.targetPlayerId) &&
        writer.u16(value.health) &&
        writer.i32(value.xMillimeters) &&
        writer.i32(value.yMillimeters) &&
        writer.i32(value.zMillimeters) &&
        writer.i16(value.yawCentidegrees);
}

bool readZombieSnapshot(
    Reader& reader,
    NetZombieSnapshot& value) noexcept {
    return
        reader.u16(value.zombieId) &&
        reader.u8(value.state) &&
        reader.u8(value.targetPlayerId) &&
        reader.u16(value.health) &&
        reader.i32(value.xMillimeters) &&
        reader.i32(value.yMillimeters) &&
        reader.i32(value.zMillimeters) &&
        reader.i16(value.yawCentidegrees);
}

constexpr std::size_t kPlayerInputBytes =
    4U + 2U + 2U + 2U + 2U + 2U + 2U + 2U;

constexpr std::size_t kPlayerSnapshotBytes =
    1U + 1U + 2U + 4U +
    4U + 4U + 4U +
    2U + 2U + 2U + 2U;

constexpr std::size_t kZombieSnapshotBytes =
    2U + 1U + 1U + 2U +
    4U + 4U + 4U + 2U;

constexpr std::size_t kSnapshotPrefixBytes =
    4U + 2U + 2U + 1U + 1U;

} // namespace

std::size_t netPlayerInputPayloadBytes() noexcept {
    return kPlayerInputBytes;
}

std::size_t netSnapshotPayloadBytes(
    const NetWorldSnapshot& snapshot) noexcept {
    const std::size_t players =
        std::min<std::size_t>(
            snapshot.playerCount,
            kOnlineMaxPlayers);

    const std::size_t zombies =
        std::min<std::size_t>(
            snapshot.zombieCount,
            kOnlineMaxReplicatedZombies);

    return
        kSnapshotPrefixBytes +
        players * kPlayerSnapshotBytes +
        zombies * kZombieSnapshotBytes;
}

bool encodeNetPlayerInput(
    const NetPacketHeader& header,
    const NetPlayerInput& input,
    std::span<std::byte> destination,
    std::size_t& written) noexcept {
    written = 0U;

    if (header.type !=
            NetMessageType::PlayerInput ||
        destination.size() <
            kNetHeaderBytes +
                kPlayerInputBytes) {
        return false;
    }

    Writer writer(destination);

    if (!writeHeader(
            writer,
            header,
            static_cast<std::uint16_t>(
                kPlayerInputBytes)) ||
        !writer.u32(input.clientTick) ||
        !writer.u16(input.buttons) ||
        !writer.i16(input.moveX) ||
        !writer.i16(input.moveY) ||
        !writer.i16(input.yawCentidegrees) ||
        !writer.i16(input.pitchCentidegrees) ||
        !writer.u16(input.fireSequence) ||
        !writer.u16(input.interactId)) {
        return false;
    }

    written = writer.offset();
    return true;
}

NetDecodeResult decodeNetPlayerInput(
    std::span<const std::byte> bytes,
    NetPacketHeader& header,
    NetPlayerInput& input) noexcept {
    header = {};
    input = {};

    if (bytes.size() <
        kNetHeaderBytes +
            kPlayerInputBytes) {
        return {};
    }

    Reader reader(bytes);

    if (!readHeader(reader, header) ||
        header.type !=
            NetMessageType::PlayerInput ||
        header.payloadBytes !=
            kPlayerInputBytes ||
        bytes.size() <
            kNetHeaderBytes +
                header.payloadBytes ||
        !reader.u32(input.clientTick) ||
        !reader.u16(input.buttons) ||
        !reader.i16(input.moveX) ||
        !reader.i16(input.moveY) ||
        !reader.i16(input.yawCentidegrees) ||
        !reader.i16(input.pitchCentidegrees) ||
        !reader.u16(input.fireSequence) ||
        !reader.u16(input.interactId)) {
        header = {};
        input = {};
        return {};
    }

    return {
        .success = true,
        .type = header.type,
        .bytesConsumed = reader.offset(),
    };
}

bool encodeNetSnapshot(
    const NetPacketHeader& header,
    const NetWorldSnapshot& snapshot,
    std::span<std::byte> destination,
    std::size_t& written) noexcept {
    written = 0U;

    if (header.type !=
            NetMessageType::Snapshot ||
        snapshot.playerCount >
            kOnlineMaxPlayers ||
        snapshot.zombieCount >
            kOnlineMaxReplicatedZombies) {
        return false;
    }

    const std::size_t payloadBytes =
        netSnapshotPayloadBytes(snapshot);

    if (payloadBytes >
            std::numeric_limits<
                std::uint16_t>::max() ||
        kNetHeaderBytes + payloadBytes >
            destination.size() ||
        kNetHeaderBytes + payloadBytes >
            kNetMaxPacketBytes) {
        return false;
    }

    Writer writer(destination);

    if (!writeHeader(
            writer,
            header,
            static_cast<std::uint16_t>(
                payloadBytes)) ||
        !writer.u32(snapshot.serverTick) ||
        !writer.u16(
            snapshot.ackInputSequence) ||
        !writer.u16(snapshot.round) ||
        !writer.u8(snapshot.playerCount) ||
        !writer.u8(snapshot.zombieCount)) {
        return false;
    }

    for (std::size_t i = 0U;
         i < snapshot.playerCount;
         ++i) {
        if (!writePlayerSnapshot(
                writer,
                snapshot.players[i])) {
            return false;
        }
    }

    for (std::size_t i = 0U;
         i < snapshot.zombieCount;
         ++i) {
        if (!writeZombieSnapshot(
                writer,
                snapshot.zombies[i])) {
            return false;
        }
    }

    written = writer.offset();
    return true;
}

NetDecodeResult decodeNetSnapshot(
    std::span<const std::byte> bytes,
    NetPacketHeader& header,
    NetWorldSnapshot& snapshot) noexcept {
    header = {};
    snapshot = {};

    if (bytes.size() <
        kNetHeaderBytes +
            kSnapshotPrefixBytes) {
        return {};
    }

    Reader reader(bytes);

    if (!readHeader(reader, header) ||
        header.type !=
            NetMessageType::Snapshot ||
        bytes.size() <
            kNetHeaderBytes +
                header.payloadBytes ||
        !reader.u32(snapshot.serverTick) ||
        !reader.u16(
            snapshot.ackInputSequence) ||
        !reader.u16(snapshot.round) ||
        !reader.u8(snapshot.playerCount) ||
        !reader.u8(snapshot.zombieCount) ||
        snapshot.playerCount >
            kOnlineMaxPlayers ||
        snapshot.zombieCount >
            kOnlineMaxReplicatedZombies) {
        header = {};
        snapshot = {};
        return {};
    }

    const std::size_t expected =
        netSnapshotPayloadBytes(snapshot);

    if (header.payloadBytes != expected) {
        header = {};
        snapshot = {};
        return {};
    }

    for (std::size_t i = 0U;
         i < snapshot.playerCount;
         ++i) {
        if (!readPlayerSnapshot(
                reader,
                snapshot.players[i])) {
            header = {};
            snapshot = {};
            return {};
        }
    }

    for (std::size_t i = 0U;
         i < snapshot.zombieCount;
         ++i) {
        if (!readZombieSnapshot(
                reader,
                snapshot.zombies[i])) {
            header = {};
            snapshot = {};
            return {};
        }
    }

    return {
        .success = true,
        .type = header.type,
        .bytesConsumed = reader.offset(),
    };
}

} // namespace xziel
