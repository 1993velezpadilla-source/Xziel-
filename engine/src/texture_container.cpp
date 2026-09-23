#include "xziel/texture_container.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <utility>

namespace xziel {

namespace {

constexpr std::array<std::byte, 12> kIdentifier{{
    std::byte{0xAB},
    std::byte{0x4B},
    std::byte{0x54},
    std::byte{0x58},
    std::byte{0x20},
    std::byte{0x32},
    std::byte{0x30},
    std::byte{0xBB},
    std::byte{0x0D},
    std::byte{0x0A},
    std::byte{0x1A},
    std::byte{0x0A},
}};

class Reader final {
public:
    explicit Reader(
        std::span<const std::byte> bytes) noexcept
        : bytes_(bytes) {}

    [[nodiscard]] std::size_t offset() const noexcept {
        return offset_;
    }

    [[nodiscard]] bool readU32(
        std::uint32_t& value) noexcept {
        if (offset_ + 4U > bytes_.size()) {
            return false;
        }

        value =
            static_cast<std::uint32_t>(
                std::to_integer<std::uint8_t>(
                    bytes_[offset_])) |
            (static_cast<std::uint32_t>(
                 std::to_integer<std::uint8_t>(
                     bytes_[offset_ + 1U]))
             << 8U) |
            (static_cast<std::uint32_t>(
                 std::to_integer<std::uint8_t>(
                     bytes_[offset_ + 2U]))
             << 16U) |
            (static_cast<std::uint32_t>(
                 std::to_integer<std::uint8_t>(
                     bytes_[offset_ + 3U]))
             << 24U);

        offset_ += 4U;
        return true;
    }

    [[nodiscard]] bool readU64(
        std::uint64_t& value) noexcept {
        std::uint32_t low = 0U;
        std::uint32_t high = 0U;

        if (!readU32(low) ||
            !readU32(high)) {
            return false;
        }

        value =
            static_cast<std::uint64_t>(low) |
            (static_cast<std::uint64_t>(high)
             << 32U);
        return true;
    }

private:
    std::span<const std::byte> bytes_{};
    std::size_t offset_ = 0U;
};

[[nodiscard]] Ktx2ParseResult failure(
    Ktx2ParseError error,
    std::size_t offset,
    Ktx2Texture& destination) noexcept {
    destination = {};
    return {
        .success = false,
        .error = error,
        .offset = offset,
    };
}

struct AstcFootprint {
    std::uint32_t width = 0U;
    std::uint32_t height = 0U;
    bool srgb = false;
};

[[nodiscard]] bool astcFootprint(
    std::uint32_t vkFormat,
    AstcFootprint& out) noexcept {
    if (vkFormat < kVkFormatAstc4x4Unorm ||
        vkFormat > kVkFormatAstc12x12Srgb) {
        return false;
    }

    const std::uint32_t pair =
        (vkFormat -
         kVkFormatAstc4x4Unorm) /
        2U;

    constexpr std::array<std::array<std::uint32_t, 2>, 14>
        footprints{{
            {{4U, 4U}},
            {{5U, 4U}},
            {{5U, 5U}},
            {{6U, 5U}},
            {{6U, 6U}},
            {{8U, 5U}},
            {{8U, 6U}},
            {{8U, 8U}},
            {{10U, 5U}},
            {{10U, 6U}},
            {{10U, 8U}},
            {{10U, 10U}},
            {{12U, 10U}},
            {{12U, 12U}},
        }};

    if (pair >= footprints.size()) {
        return false;
    }

    out.width = footprints[pair][0];
    out.height = footprints[pair][1];
    out.srgb =
        ((vkFormat -
          kVkFormatAstc4x4Unorm) &
         1U) != 0U;
    return true;
}

[[nodiscard]] bool rangeInside(
    std::uint64_t offset,
    std::uint64_t length,
    std::size_t total) noexcept {
    if (offset >
        static_cast<std::uint64_t>(total)) {
        return false;
    }

    const std::uint64_t remaining =
        static_cast<std::uint64_t>(total) -
        offset;

    return length <= remaining;
}

[[nodiscard]] std::uint32_t mipDimension(
    std::uint32_t base,
    std::uint32_t level) noexcept {
    if (level >= 31U) {
        return 1U;
    }

    return
        std::max<std::uint32_t>(
            1U,
            base >> level);
}

[[nodiscard]] std::uint64_t expectedAstcBytes(
    std::uint32_t width,
    std::uint32_t height,
    std::uint32_t blockWidth,
    std::uint32_t blockHeight) noexcept {
    const std::uint64_t blocksX =
        (static_cast<std::uint64_t>(width) +
         blockWidth - 1U) /
        blockWidth;
    const std::uint64_t blocksY =
        (static_cast<std::uint64_t>(height) +
         blockHeight - 1U) /
        blockHeight;

    if (blocksX >
        std::numeric_limits<std::uint64_t>::max() /
        std::max<std::uint64_t>(blocksY, 1U) /
        16U) {
        return 0U;
    }

    return
        blocksX *
        blocksY *
        16U;
}

} // namespace

Ktx2ParseResult parseKtx2Astc(
    std::span<const std::byte> bytes,
    Ktx2Texture& destination) noexcept {
    destination = {};

    if (bytes.size() < 80U) {
        return failure(
            Ktx2ParseError::Truncated,
            bytes.size(),
            destination);
    }

    if (!std::equal(
            kIdentifier.begin(),
            kIdentifier.end(),
            bytes.begin())) {
        return failure(
            Ktx2ParseError::InvalidIdentifier,
            0U,
            destination);
    }

    Reader reader(
        bytes.subspan(12U));

    std::uint32_t vkFormat = 0U;
    std::uint32_t typeSize = 0U;
    std::uint32_t pixelWidth = 0U;
    std::uint32_t pixelHeight = 0U;
    std::uint32_t pixelDepth = 0U;
    std::uint32_t layerCount = 0U;
    std::uint32_t faceCount = 0U;
    std::uint32_t levelCount = 0U;
    std::uint32_t supercompression = 0U;
    std::uint32_t dfdOffset = 0U;
    std::uint32_t dfdLength = 0U;
    std::uint32_t kvdOffset = 0U;
    std::uint32_t kvdLength = 0U;
    std::uint64_t sgdOffset = 0U;
    std::uint64_t sgdLength = 0U;

    if (!reader.readU32(vkFormat) ||
        !reader.readU32(typeSize) ||
        !reader.readU32(pixelWidth) ||
        !reader.readU32(pixelHeight) ||
        !reader.readU32(pixelDepth) ||
        !reader.readU32(layerCount) ||
        !reader.readU32(faceCount) ||
        !reader.readU32(levelCount) ||
        !reader.readU32(supercompression) ||
        !reader.readU32(dfdOffset) ||
        !reader.readU32(dfdLength) ||
        !reader.readU32(kvdOffset) ||
        !reader.readU32(kvdLength) ||
        !reader.readU64(sgdOffset) ||
        !reader.readU64(sgdLength)) {
        return failure(
            Ktx2ParseError::Truncated,
            12U + reader.offset(),
            destination);
    }

    AstcFootprint footprint{};
    if (!astcFootprint(
            vkFormat,
            footprint)) {
        return failure(
            Ktx2ParseError::UnsupportedFormat,
            12U,
            destination);
    }

    if (typeSize != 1U ||
        pixelWidth == 0U ||
        pixelHeight == 0U ||
        pixelDepth != 0U ||
        layerCount != 0U ||
        faceCount != 1U ||
        levelCount == 0U) {
        return failure(
            Ktx2ParseError::UnsupportedTextureType,
            16U,
            destination);
    }

    if (supercompression != 0U ||
        sgdOffset != 0U ||
        sgdLength != 0U) {
        return failure(
            Ktx2ParseError::UnsupportedSupercompression,
            44U,
            destination);
    }

    std::uint32_t maxLevels = 1U;
    std::uint32_t largest =
        std::max(
            pixelWidth,
            pixelHeight);

    while (largest > 1U) {
        largest >>= 1U;
        ++maxLevels;
    }

    if (levelCount > maxLevels ||
        levelCount > 32U) {
        return failure(
            Ktx2ParseError::InvalidLevel,
            40U,
            destination);
    }

    const std::uint64_t indexEnd =
        80ULL +
        static_cast<std::uint64_t>(
            levelCount) *
        24ULL;

    if (indexEnd >
        static_cast<std::uint64_t>(
            bytes.size())) {
        return failure(
            Ktx2ParseError::Truncated,
            bytes.size(),
            destination);
    }

    if (dfdLength < 4U ||
        dfdOffset < indexEnd ||
        !rangeInside(
            dfdOffset,
            dfdLength,
            bytes.size()) ||
        (kvdLength == 0U && kvdOffset != 0U) ||
        (kvdLength != 0U &&
         (kvdOffset < indexEnd ||
          !rangeInside(
              kvdOffset,
              kvdLength,
              bytes.size())))) {
        return failure(
            Ktx2ParseError::InvalidMetadata,
            48U,
            destination);
    }

    const auto readU32At =
        [&](std::size_t offset,
            std::uint32_t& value) noexcept {
            if (offset + 4U > bytes.size()) {
                return false;
            }

            value =
                static_cast<std::uint32_t>(
                    std::to_integer<std::uint8_t>(
                        bytes[offset])) |
                (static_cast<std::uint32_t>(
                     std::to_integer<std::uint8_t>(
                         bytes[offset + 1U]))
                 << 8U) |
                (static_cast<std::uint32_t>(
                     std::to_integer<std::uint8_t>(
                         bytes[offset + 2U]))
                 << 16U) |
                (static_cast<std::uint32_t>(
                     std::to_integer<std::uint8_t>(
                         bytes[offset + 3U]))
                 << 24U);
            return true;
        };

    std::uint32_t dfdTotalSize = 0U;
    if (!readU32At(
            dfdOffset,
            dfdTotalSize) ||
        dfdTotalSize != dfdLength) {
        return failure(
            Ktx2ParseError::InvalidMetadata,
            dfdOffset,
            destination);
    }

    Reader levelsReader(
        bytes.subspan(80U));

    try {
        destination.levels.reserve(
            levelCount);
    } catch (...) {
        return failure(
            Ktx2ParseError::InvalidLevel,
            80U,
            destination);
    }

    std::vector<std::pair<std::uint64_t, std::uint64_t>>
        ranges;

    try {
        ranges.reserve(levelCount);
    } catch (...) {
        return failure(
            Ktx2ParseError::InvalidLevel,
            80U,
            destination);
    }

    for (std::uint32_t level = 0U;
         level < levelCount;
         ++level) {
        std::uint64_t offset = 0U;
        std::uint64_t byteLength = 0U;
        std::uint64_t uncompressedLength = 0U;

        if (!levelsReader.readU64(offset) ||
            !levelsReader.readU64(byteLength) ||
            !levelsReader.readU64(uncompressedLength)) {
            return failure(
                Ktx2ParseError::Truncated,
                80U + levelsReader.offset(),
                destination);
        }

        const std::uint32_t width =
            mipDimension(
                pixelWidth,
                level);
        const std::uint32_t height =
            mipDimension(
                pixelHeight,
                level);

        const std::uint64_t expected =
            expectedAstcBytes(
                width,
                height,
                footprint.width,
                footprint.height);

        if (expected == 0U ||
            byteLength != expected ||
            uncompressedLength != expected ||
            (offset % 16U) != 0U ||
            offset < indexEnd ||
            !rangeInside(
                offset,
                byteLength,
                bytes.size())) {
            return failure(
                Ktx2ParseError::InvalidLevel,
                80U +
                    static_cast<std::size_t>(level) *
                    24U,
                destination);
        }

        const std::uint64_t end =
            offset + byteLength;

        for (const auto& range : ranges) {
            if (offset < range.second &&
                end > range.first) {
                return failure(
                    Ktx2ParseError::InvalidIndex,
                    80U +
                        static_cast<std::size_t>(level) *
                        24U,
                    destination);
            }
        }

        ranges.emplace_back(
            offset,
            end);

        destination.levels.push_back({
            .byteOffset = offset,
            .byteLength = byteLength,
            .width = width,
            .height = height,
        });
    }

    destination.vkFormat = vkFormat;
    destination.width = pixelWidth;
    destination.height = pixelHeight;
    destination.blockWidth =
        footprint.width;
    destination.blockHeight =
        footprint.height;
    destination.srgb =
        footprint.srgb;

    return {
        .success = true,
        .error = Ktx2ParseError::None,
        .offset = bytes.size(),
    };
}

Ktx2ResidentMipRange
planKtx2ResidentMipRange(
    const Ktx2Texture& texture,
    std::uint32_t baseMip) noexcept {
    Ktx2ResidentMipRange out{};

    if (texture.levels.empty() ||
        baseMip >= texture.levels.size() ||
        texture.levels.size() >
            std::numeric_limits<std::uint32_t>::max()) {
        return out;
    }

    const auto& first =
        texture.levels[baseMip];

    if (first.width == 0U ||
        first.height == 0U) {
        return out;
    }

    std::uint64_t payloadBytes = 0U;

    for (std::size_t i = baseMip;
         i < texture.levels.size();
         ++i) {
        const auto& level =
            texture.levels[i];

        if (level.width == 0U ||
            level.height == 0U ||
            level.byteLength == 0U ||
            level.byteLength >
                std::numeric_limits<std::uint64_t>::max() -
                    payloadBytes) {
            return out;
        }

        payloadBytes += level.byteLength;
    }

    out.valid = true;
    out.baseMip = baseMip;
    out.width = first.width;
    out.height = first.height;
    out.mipCount =
        static_cast<std::uint32_t>(
            texture.levels.size() -
            baseMip);
    out.payloadBytes = payloadBytes;
    return out;
}

} // namespace xziel
