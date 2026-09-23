#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace xziel {

inline constexpr std::uint32_t kStaticMeshLegacyVersion = 2U;
inline constexpr std::uint32_t kStaticMeshNormalsVersion = 3U;
inline constexpr std::uint32_t kStaticMeshMaterialFlagsVersion = 4U;
inline constexpr std::uint32_t kStaticMeshFormatVersion = 5U;
inline constexpr std::size_t kMaxStaticMeshBatches = 2048U;
inline constexpr std::uint32_t kMaxStaticMeshVertices = 8000000U;
inline constexpr std::uint32_t kMaxStaticMeshIndices = 12000000U;

struct StaticMeshVertex {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;

    float nx = 0.0f;
    float ny = 1.0f;
    float nz = 0.0f;

    float u = 0.0f;
    float v = 0.0f;
    std::array<std::uint8_t, 4> rgba{
        255U, 255U, 255U, 255U};
};

static_assert(
    sizeof(StaticMeshVertex) == 36U,
    "native XZSM runtime vertex ABI must stay 36 bytes");

struct StaticMeshBounds {
    std::array<float, 3> minimum{};
    std::array<float, 3> maximum{};
};

enum StaticMeshBatchFlags : std::uint32_t {
    StaticMeshBatchFlagNone = 0U,
    StaticMeshBatchFlagDoubleSided = 1U << 0U,
};

struct StaticMeshPbrMaterial {
    std::string normalTextureName{};
    std::string ormTextureName{};
    std::string emissiveTextureName{};

    std::array<float, 4> baseColorFactor{
        1.0f, 1.0f, 1.0f, 1.0f};
    float metallicFactor = 0.0f;
    float roughnessFactor = 1.0f;
    std::array<float, 3> emissiveFactor{
        0.0f, 0.0f, 0.0f};
    float normalScale = 1.0f;
    float occlusionStrength = 1.0f;
};

struct StaticMeshBatch {
    // Base-color texture stays in the legacy field so v2-v4 runtime code and
    // staged v5 rollouts can continue drawing before the full PBR bind set is
    // enabled.
    std::string textureName{};
    StaticMeshPbrMaterial pbr{};
    StaticMeshBounds bounds{};
    std::uint32_t flags =
        StaticMeshBatchFlagDoubleSided;
    bool pbrMaterial = false;
    std::vector<StaticMeshVertex> vertices{};
    std::vector<std::uint16_t> indices{};

    [[nodiscard]] bool doubleSided() const noexcept {
        return
            (flags &
             StaticMeshBatchFlagDoubleSided) != 0U;
    }

    [[nodiscard]] bool pbrEnabled() const noexcept {
        return pbrMaterial;
    }
};

struct StaticMeshAsset {
    std::vector<StaticMeshBatch> batches{};
    std::uint32_t totalVertices = 0U;
    std::uint32_t totalIndices = 0U;
};

struct StaticMeshBatchDirectoryEntry {
    std::string textureName{};
    StaticMeshBounds bounds{};
    std::uint32_t flags =
        StaticMeshBatchFlagDoubleSided;
    std::uint32_t vertexCount = 0U;
    std::uint32_t indexCount = 0U;
    std::uint64_t vertexDataOffset = 0U;
    std::uint64_t indexDataOffset = 0U;
    std::uint64_t payloadBytes = 0U;

    [[nodiscard]] bool doubleSided() const noexcept {
        return
            (flags &
             StaticMeshBatchFlagDoubleSided) != 0U;
    }
};

struct StaticMeshDirectory {
    std::vector<StaticMeshBatchDirectoryEntry>
        batches{};
    std::uint32_t version = 0U;
    std::uint32_t totalVertices = 0U;
    std::uint32_t totalIndices = 0U;
    std::uint64_t fileBytes = 0U;
};

enum class StaticMeshParseError : std::uint8_t {
    None,
    Truncated,
    InvalidMagic,
    UnsupportedVersion,
    CapacityExceeded,
    InvalidBatch,
    InvalidIndex,
    TotalMismatch,
    TrailingData,
};

struct StaticMeshParseResult {
    bool success = false;
    StaticMeshParseError error =
        StaticMeshParseError::None;
    std::size_t offset = 0U;
};

[[nodiscard]] StaticMeshParseResult
parseStaticMeshXzsm(
    std::span<const std::byte> bytes,
    StaticMeshAsset& destination) noexcept;

[[nodiscard]] StaticMeshParseResult
parseStaticMeshXzsmDirectory(
    std::span<const std::byte> bytes,
    StaticMeshDirectory& destination) noexcept;

} // namespace xziel
