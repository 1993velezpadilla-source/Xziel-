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

inline constexpr std::uint32_t kViewmodelMaxBatches = 128U;
inline constexpr std::uint32_t kViewmodelMinVertices = 96U;
inline constexpr std::uint32_t kViewmodelMaxVertices = 600000U;
inline constexpr std::uint32_t kViewmodelMinIndices = 96U;
inline constexpr std::uint32_t kViewmodelMaxIndices = 900000U;
inline constexpr float kViewmodelMinExtentMeters = 0.30f;
inline constexpr float kViewmodelMaxExtentMeters = 1.50f;
inline constexpr float kViewmodelMinAxisCoverage90 = 0.20f;
inline constexpr float kViewmodelMinRobustExtent90 = 0.25f;
inline constexpr float kViewmodelMinRobustSecondExtent90 = 0.035f;
inline constexpr float kViewmodelMinRobustThirdExtent90 = 0.012f;
inline constexpr float kViewmodelMaxPeakVoxelOccupancy = 0.75f;

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
    std::array<float, 3> robustExtents90{};
    float longestExtent = 0.0f;
    float robustAxisCoverage90 = 0.0f;
    float robustLongestExtent90 = 0.0f;
    float robustSecondExtent90 = 0.0f;
    float robustThirdExtent90 = 0.0f;
    float peakVoxelOccupancyRatio = 0.0f;
    std::uint32_t batchCount = 0U;
    std::uint32_t vertexCount = 0U;
    std::uint32_t indexCount = 0U;
};

enum class ViewmodelStaticMeshRejection : std::uint8_t {
    None,
    NoBatches,
    TooManyBatches,
    TooFewVertices,
    TooManyVertices,
    TooFewIndices,
    TooManyIndices,
    NonTriangleIndexCount,
    InvalidEnvelope,
    CollapsedVertexCloud,
    NeedleThin,
};

struct ViewmodelStaticMeshQualityResult {
    bool success = false;
    ViewmodelStaticMeshRejection rejection =
        ViewmodelStaticMeshRejection::None;
    StaticMeshQualityMetrics metrics{};
};

[[nodiscard]] StaticMeshQualityMetrics
measureStaticMeshQuality(
    const StaticMeshAsset& asset) noexcept;

[[nodiscard]] ViewmodelStaticMeshQualityResult
evaluateViewmodelStaticMesh(
    const StaticMeshAsset& asset) noexcept;

[[nodiscard]] const char*
viewmodelStaticMeshRejectionName(
    ViewmodelStaticMeshRejection rejection) noexcept;

[[nodiscard]] bool
passesViewmodelStaticMeshSanity(
    const StaticMeshAsset& asset,
    StaticMeshQualityMetrics* metrics = nullptr) noexcept;

[[nodiscard]] StaticMeshParseResult
parseStaticMeshXzsm(
    std::span<const std::byte> bytes,
    StaticMeshAsset& destination) noexcept;

} // namespace xziel
