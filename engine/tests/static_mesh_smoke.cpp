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

std::vector<std::byte> makeTriangle() {
    std::vector<std::byte> bytes;

    for (char c : std::array<char, 4>{
             'X', 'Z', 'S', 'M'}) {
        bytes.push_back(
            static_cast<std::byte>(c));
    }

    appendU32(
        bytes,
        xziel::kStaticMeshFormatVersion);
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
        for (float value : vertex) {
            appendF32(bytes, value);
        }

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
        makeTriangle();

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

    return 0;
}
