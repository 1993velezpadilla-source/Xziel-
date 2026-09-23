#include "xziel/texture_container.hpp"

#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace {

void writeU32(
    std::vector<std::byte>& bytes,
    std::size_t offset,
    std::uint32_t value) {
    for (std::size_t i = 0U; i < 4U; ++i) {
        bytes[offset + i] =
            static_cast<std::byte>(
                (value >> (i * 8U)) &
                0xFFU);
    }
}

void writeU64(
    std::vector<std::byte>& bytes,
    std::size_t offset,
    std::uint64_t value) {
    writeU32(
        bytes,
        offset,
        static_cast<std::uint32_t>(
            value & 0xFFFFFFFFULL));
    writeU32(
        bytes,
        offset + 4U,
        static_cast<std::uint32_t>(
            value >> 32U));
}

std::vector<std::byte> makeAstc6x6Ktx2() {
    std::vector<std::byte> bytes(
        288U,
        std::byte{0});

    constexpr std::array<std::uint8_t, 12>
        identifier{{
            0xAB, 0x4B, 0x54, 0x58,
            0x20, 0x32, 0x30, 0xBB,
            0x0D, 0x0A, 0x1A, 0x0A,
        }};

    for (std::size_t i = 0U;
         i < identifier.size();
         ++i) {
        bytes[i] =
            static_cast<std::byte>(
                identifier[i]);
    }

    writeU32(bytes, 12U, 166U); // ASTC 6x6 SRGB
    writeU32(bytes, 16U, 1U);
    writeU32(bytes, 20U, 12U);
    writeU32(bytes, 24U, 12U);
    writeU32(bytes, 28U, 0U);
    writeU32(bytes, 32U, 0U);
    writeU32(bytes, 36U, 1U);
    writeU32(bytes, 40U, 3U);
    writeU32(bytes, 44U, 0U);
    writeU32(bytes, 48U, 160U);
    writeU32(bytes, 52U, 24U);
    writeU32(bytes, 56U, 0U);
    writeU32(bytes, 60U, 0U);
    writeU64(bytes, 64U, 0U);
    writeU64(bytes, 72U, 0U);

    // Base level: 12x12 -> four 6x6 blocks -> 64 bytes.
    writeU64(bytes, 80U, 224U);
    writeU64(bytes, 88U, 64U);
    writeU64(bytes, 96U, 64U);

    // Mip 1: 6x6 -> one block.
    writeU64(bytes, 104U, 208U);
    writeU64(bytes, 112U, 16U);
    writeU64(bytes, 120U, 16U);

    // Mip 2: 3x3 still occupies one ASTC block.
    writeU64(bytes, 128U, 192U);
    writeU64(bytes, 136U, 16U);
    writeU64(bytes, 144U, 16U);

    writeU32(bytes, 160U, 24U);

    for (std::size_t i = 192U;
         i < bytes.size();
         ++i) {
        bytes[i] =
            static_cast<std::byte>(
                i & 0xFFU);
    }

    return bytes;
}

} // namespace

int main() {
    auto encoded =
        makeAstc6x6Ktx2();

    xziel::Ktx2Texture texture{};
    auto parsed =
        xziel::parseKtx2Astc(
            encoded,
            texture);

    assert(parsed.success);
    assert(
        parsed.error ==
        xziel::Ktx2ParseError::None);
    assert(texture.vkFormat == 166U);
    assert(texture.width == 12U);
    assert(texture.height == 12U);
    assert(texture.blockWidth == 6U);
    assert(texture.blockHeight == 6U);
    assert(texture.srgb);
    assert(texture.levels.size() == 3U);
    assert(texture.levels[0].byteOffset == 224U);
    assert(texture.levels[0].byteLength == 64U);
    assert(texture.levels[0].width == 12U);
    assert(texture.levels[1].width == 6U);
    assert(texture.levels[2].width == 3U);

    auto badIdentifier = encoded;
    badIdentifier[0] = std::byte{0};
    parsed =
        xziel::parseKtx2Astc(
            badIdentifier,
            texture);
    assert(!parsed.success);
    assert(
        parsed.error ==
        xziel::Ktx2ParseError::InvalidIdentifier);

    auto supercompressed = encoded;
    writeU32(
        supercompressed,
        44U,
        2U);
    parsed =
        xziel::parseKtx2Astc(
            supercompressed,
            texture);
    assert(!parsed.success);
    assert(
        parsed.error ==
        xziel::Ktx2ParseError::
            UnsupportedSupercompression);

    auto invalidLength = encoded;
    writeU64(
        invalidLength,
        88U,
        48U);
    parsed =
        xziel::parseKtx2Astc(
            invalidLength,
            texture);
    assert(!parsed.success);
    assert(
        parsed.error ==
        xziel::Ktx2ParseError::InvalidLevel);

    auto overlapping = encoded;
    writeU64(
        overlapping,
        104U,
        224U);
    parsed =
        xziel::parseKtx2Astc(
            overlapping,
            texture);
    assert(!parsed.success);
    assert(
        parsed.error ==
        xziel::Ktx2ParseError::InvalidIndex);

    auto linear = encoded;
    writeU32(
        linear,
        12U,
        165U);
    parsed =
        xziel::parseKtx2Astc(
            linear,
            texture);
    assert(parsed.success);
    assert(!texture.srgb);

    return 0;
}
