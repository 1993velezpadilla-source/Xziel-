#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace xziel {

inline constexpr std::uint32_t kStaticMeshLegacyVersion = 2U;
inline constexpr std::uint32_t kStaticMeshFormatVersion = 3U;
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
    "native XZSM v3 runtime vertex ABI must stay 36 bytes");

struct StaticMeshBounds {
    std::array<float, 3> minimum{};
    std::array<float, 3> maximum{};
};

struct StaticMeshBatch {
    std::string textureName{};
    StaticMeshBounds bounds{};
    std::vector<StaticMeshVertex> vertices{};
    std::vector<std::uint16_t> indices{};
};

struct StaticMeshAsset {
    std::vector<StaticMeshBatch> batches{};
    std::uint32_t totalVertices = 0U;
    std::uint32_t totalIndices = 0U;
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

struct StaticMeshQualityMetrics {
    StaticMeshBounds bounds{};
    float longestExtent = 0.0f;
    float robustAxisCoverage90 = 0.0f;
    std::uint32_t vertexCount = 0U;
};

[[nodiscard]] StaticMeshQualityMetrics
measureStaticMeshQuality(
    const StaticMeshAsset& asset) noexcept;

[[nodiscard]] bool
passesViewmodelStaticMeshSanity(
    const StaticMeshAsset& asset,
    StaticMeshQualityMetrics* metrics = nullptr) noexcept;

[[nodiscard]] StaticMeshParseResult
parseStaticMeshXzsm(
    std::span<const std::byte> bytes,
    StaticMeshAsset& destination) noexcept;

} // namespace xziel
