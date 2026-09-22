#include "xziel/static_mesh.hpp"

#include <array>
#include <bit>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace {

void appendU16(
    std::vector<std::byte>& bytes,
    std::uint16_t value) {
    bytes.push_back(
        static_cast<std::byte>(
            value & 0xFFU));
    bytes.push_back(
        static_cast<std::byte>(
            (value >> 8U) & 0xFFU));
}

void appendU32(
    std::vector<std::byte>& bytes,
    std::uint32_t value) {
    for (unsigned int shift :
         {0U, 8U, 16U, 24U}) {
        bytes.push_back(
            static_cast<std::byte>(
                (value >> shift) & 0xFFU));
    }
}

void appendF32(
    std::vector<std::byte>& bytes,
    float value) {
    appendU32(
        bytes,
        std::bit_cast<std::uint32_t>(
            value));
}

std::vector<std::byte> makeTriangle(std::uint32_t version) {
    std::vector<std::byte> bytes;

    for (char c : std::array<char, 4>{
             'X', 'Z', 'S', 'M'}) {
        bytes.push_back(
            static_cast<std::byte>(c));
    }

    appendU32(
        bytes,
        version);
    appendU32(bytes, 1U);
    appendU32(bytes, 3U);
    appendU32(bytes, 3U);

    appendU32(bytes, 3U);
    appendU32(bytes, 3U);

    std::array<char, 96> texture{};
    constexpr char name[] =
        "textures/xziel/sanctum/test";
    for (std::size_t i = 0U;
         i + 1U < sizeof(name);
         ++i) {
        texture[i] = name[i];
    }

    for (const char c : texture) {
        bytes.push_back(
            static_cast<std::byte>(c));
    }

    for (float value :
         std::array<float, 6>{
             -1.0f, -1.0f, 0.0f,
              1.0f,  1.0f, 0.0f}) {
        appendF32(bytes, value);
    }

    const std::array<std::array<float, 5>, 3>
        vertices{{
            {-1.0f, -1.0f, 0.0f, 0.0f, 0.0f},
            { 1.0f, -1.0f, 0.0f, 1.0f, 0.0f},
            { 0.0f,  1.0f, 0.0f, 0.5f, 1.0f},
        }};

    for (const auto& vertex : vertices) {
        appendF32(bytes, vertex[0]);
        appendF32(bytes, vertex[1]);
        appendF32(bytes, vertex[2]);

        if (version >=
            xziel::kStaticMeshFormatVersion) {
            appendF32(bytes, 0.0f);
            appendF32(bytes, 0.0f);
            appendF32(bytes, 1.0f);
        }

        appendF32(bytes, vertex[3]);
        appendF32(bytes, vertex[4]);

        for (std::uint8_t value :
             std::array<std::uint8_t, 4>{
                 220U, 210U, 200U, 255U}) {
            bytes.push_back(
                static_cast<std::byte>(value));
        }
    }

    appendU16(bytes, 0U);
    appendU16(bytes, 1U);
    appendU16(bytes, 2U);

    return bytes;
}

} // namespace

int main() {
    const auto encoded =
        makeTriangle(
            xziel::kStaticMeshFormatVersion);

    xziel::StaticMeshAsset asset;
    const auto parsed =
        xziel::parseStaticMeshXzsm(
            encoded,
            asset);

    assert(parsed.success);
    assert(
        parsed.error ==
        xziel::StaticMeshParseError::None);
    assert(asset.batches.size() == 1U);
    assert(asset.totalVertices == 3U);
    assert(asset.totalIndices == 3U);
    assert(
        asset.batches[0].textureName ==
        "textures/xziel/sanctum/test");
    assert(
        asset.batches[0].vertices.size() ==
        3U);
    assert(
        asset.batches[0].indices[2] ==
        2U);
    assert(
        asset.batches[0].vertices[0].nz >
        0.99f);

    const auto legacyEncoded =
        makeTriangle(
            xziel::kStaticMeshLegacyVersion);

    xziel::StaticMeshAsset legacyAsset;
    const auto legacyParsed =
        xziel::parseStaticMeshXzsm(
            legacyEncoded,
            legacyAsset);

    assert(legacyParsed.success);
    assert(
        legacyAsset.batches[0].vertices[0].ny >
        0.99f);

    auto invalidIndex =
        encoded;

    invalidIndex[
        invalidIndex.size() - 2U] =
        static_cast<std::byte>(9U);

    xziel::StaticMeshAsset rejected;
    const auto rejectedResult =
        xziel::parseStaticMeshXzsm(
            invalidIndex,
            rejected);

    assert(!rejectedResult.success);
    assert(
        rejectedResult.error ==
        xziel::StaticMeshParseError::
            InvalidIndex);
    assert(rejected.batches.empty());

    auto truncated =
        encoded;
    truncated.pop_back();

    const auto truncatedResult =
        xziel::parseStaticMeshXzsm(
            truncated,
            rejected);

    assert(!truncatedResult.success);
    assert(
        truncatedResult.error ==
        xziel::StaticMeshParseError::
            Truncated);

    xziel::StaticMeshAsset goodViewmodel{};
    xziel::StaticMeshBatch goodBatch{};
    goodBatch.textureName =
        "textures/xziel/weapons/test";

    for (std::uint32_t i = 0U;
         i < 128U;
         ++i) {
        xziel::StaticMeshVertex vertex{};
        vertex.x =
            0.90f *
            static_cast<float>(i) /
            127.0f;
        vertex.y =
            -0.08f +
            static_cast<float>(i % 17U) *
                0.010f;
        vertex.z =
            -0.13f +
            static_cast<float>(i % 23U) *
                0.012f;
        goodBatch.vertices.push_back(vertex);
    }

    goodViewmodel.totalVertices =
        static_cast<std::uint32_t>(
            goodBatch.vertices.size());
    goodViewmodel.batches.push_back(
        goodBatch);

    xziel::StaticMeshQualityMetrics
        goodMetrics{};

    assert(
        xziel::passesViewmodelStaticMeshSanity(
            goodViewmodel,
            &goodMetrics));
    assert(goodMetrics.longestExtent > 0.89f);
    assert(
        goodMetrics.robustAxisCoverage90 >
        0.80f);
    assert(
        goodMetrics.robustSecondExtent90 >
        0.10f);
    assert(
        goodMetrics.robustThirdExtent90 >
        0.08f);

    xziel::StaticMeshAsset collapsedViewmodel =
        goodViewmodel;

    auto& collapsedVertices =
        collapsedViewmodel.batches[0].vertices;

    for (std::size_t i = 0U;
         i + 1U < collapsedVertices.size();
         ++i) {
        collapsedVertices[i].x =
            0.02f *
            static_cast<float>(i) /
            static_cast<float>(
                collapsedVertices.size() - 2U);
        collapsedVertices[i].y =
            static_cast<float>(i % 3U) *
            0.002f;
        collapsedVertices[i].z =
            static_cast<float>(i % 5U) *
            0.002f;
    }

    collapsedVertices.back().x = 0.90f;
    collapsedVertices.back().y = 0.0f;
    collapsedVertices.back().z = 0.0f;

    xziel::StaticMeshQualityMetrics
        collapsedMetrics{};

    assert(
        !xziel::passesViewmodelStaticMeshSanity(
            collapsedViewmodel,
            &collapsedMetrics));
    assert(
        collapsedMetrics.longestExtent >
        0.89f);
    assert(
        collapsedMetrics.robustAxisCoverage90 <
        0.20f);
    assert(
        collapsedMetrics.robustSecondExtent90 <
        0.035f);
    assert(
        collapsedMetrics.robustThirdExtent90 <
        0.012f);

    // Also reject a long but nearly flat needle. This catches the variant
    // where enough outlier vertices span the expected 0.9 m length that a
    // longest-axis-only check would otherwise accept it.
    xziel::StaticMeshAsset flatSpikeViewmodel =
        goodViewmodel;
    auto& flatVertices =
        flatSpikeViewmodel.batches[0].vertices;

    for (std::size_t i = 0U;
         i < flatVertices.size();
         ++i) {
        const float t =
            static_cast<float>(i) /
            static_cast<float>(
                flatVertices.size() - 1U);
        flatVertices[i].x = 0.90f * t;
        flatVertices[i].y =
            static_cast<float>(i % 2U) *
            0.003f;
        flatVertices[i].z =
            static_cast<float>(i % 3U) *
            0.002f;
    }

    xziel::StaticMeshQualityMetrics
        flatMetrics{};

    assert(
        !xziel::passesViewmodelStaticMeshSanity(
            flatSpikeViewmodel,
            &flatMetrics));
    assert(
        flatMetrics.robustAxisCoverage90 >
        0.80f);
    assert(
        flatMetrics.robustSecondExtent90 <
        0.035f);

    return 0;
}
