#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace xziel {

inline constexpr std::uint32_t kVkFormatAstc4x4Unorm = 157U;
inline constexpr std::uint32_t kVkFormatAstc4x4Srgb = 158U;
inline constexpr std::uint32_t kVkFormatAstc12x12Unorm = 183U;
inline constexpr std::uint32_t kVkFormatAstc12x12Srgb = 184U;

struct Ktx2MipLevel {
    std::uint64_t byteOffset = 0U;
    std::uint64_t byteLength = 0U;
    std::uint32_t width = 0U;
    std::uint32_t height = 0U;
};

struct Ktx2Texture {
    std::uint32_t vkFormat = 0U;
    std::uint32_t width = 0U;
    std::uint32_t height = 0U;
    std::uint32_t blockWidth = 0U;
    std::uint32_t blockHeight = 0U;
    bool srgb = false;
    std::vector<Ktx2MipLevel> levels{};
};

enum class Ktx2ParseError : std::uint8_t {
    None,
    Truncated,
    InvalidIdentifier,
    UnsupportedFormat,
    UnsupportedTextureType,
    UnsupportedSupercompression,
    InvalidIndex,
    InvalidMetadata,
    InvalidLevel,
};

struct Ktx2ParseResult {
    bool success = false;
    Ktx2ParseError error = Ktx2ParseError::None;
    std::size_t offset = 0U;
};

[[nodiscard]] Ktx2ParseResult parseKtx2Astc(
    std::span<const std::byte> bytes,
    Ktx2Texture& destination) noexcept;

} // namespace xziel
