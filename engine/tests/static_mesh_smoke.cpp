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

void appendFixed96(
    std::vector<std::byte>& bytes,
    const char* text) {
    std::array<char, 96> field{};
    if (text != nullptr) {
        for (std::size_t i = 0U;
             i + 1U < field.size() &&
             text[i] != '\0';
             ++i) {
            field[i] = text[i];
        }
    }
    for (const char c : field) {
        bytes.push_back(
            static_cast<std::byte>(c));
    }
}

std::vector<std::byte> makeTriangle(
    std::uint32_t version,
    bool authoredPbr = true,
    std::uint32_t batchFlags =
        xziel::StaticMeshBatchFlagNone) {
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

    if (version >=
        xziel::kStaticMeshMaterialFlagsVersion) {
        appendU32(
            bytes,
            batchFlags);
    }

    if (version >=
        xziel::kStaticMeshFormatVersion) {
        appendFixed96(
            bytes,
            authoredPbr
                ? "textures/xziel/sanctum/test_n"
                : "");
        appendFixed96(
            bytes,
            authoredPbr
                ? "textures/xziel/sanctum/test_orm"
                : "");
        appendFixed96(
            bytes,
            authoredPbr
                ? "textures/xziel/sanctum/test_e"
                : "");

        const std::array<float, 4> baseColor =
            authoredPbr
            ? std::array<float, 4>{
                  0.90f, 0.80f, 0.70f, 1.0f}
            : std::array<float, 4>{
                  1.0f, 1.0f, 1.0f, 1.0f};

        for (float value : baseColor) {
            appendF32(bytes, value);
        }

        appendF32(
            bytes,
            authoredPbr ? 0.25f : 0.0f);
        appendF32(
            bytes,
            authoredPbr ? 0.65f : 1.0f);

        const std::array<float, 3> emissive =
            authoredPbr
            ? std::array<float, 3>{
                  0.10f, 0.05f, 0.02f}
            : std::array<float, 3>{
                  0.0f, 0.0f, 0.0f};

        for (float value : emissive) {
            appendF32(bytes, value);
        }

        appendF32(
            bytes,
            authoredPbr ? 0.75f : 1.0f);
        appendF32(
            bytes,
            authoredPbr ? 0.85f : 1.0f);
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
            xziel::kStaticMeshNormalsVersion) {
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
    assert(
        !asset.batches[0].doubleSided());
    assert(asset.batches[0].pbrEnabled());
    assert(
        asset.batches[0].pbr.normalTextureName ==
        "textures/xziel/sanctum/test_n");
    assert(
        asset.batches[0].pbr.ormTextureName ==
        "textures/xziel/sanctum/test_orm");
    assert(
        asset.batches[0].pbr.emissiveTextureName ==
        "textures/xziel/sanctum/test_e");
    assert(
        asset.batches[0].pbr.metallicFactor >
        0.24f &&
        asset.batches[0].pbr.metallicFactor <
        0.26f);
    assert(
        asset.batches[0].pbr.roughnessFactor >
        0.64f &&
        asset.batches[0].pbr.roughnessFactor <
        0.66f);

    xziel::StaticMeshDirectory directory;
    const auto directoryParsed =
        xziel::parseStaticMeshXzsmDirectory(
            encoded,
            directory);

    assert(directoryParsed.success);
    assert(
        directoryParsed.error ==
        xziel::StaticMeshParseError::None);
    assert(
        directory.version ==
        xziel::kStaticMeshFormatVersion);
    assert(directory.batches.size() == 1U);
    assert(directory.totalVertices == 3U);
    assert(directory.totalIndices == 3U);
    assert(directory.fileBytes == encoded.size());

    const auto& directoryBatch =
        directory.batches[0];

    assert(
        directoryBatch.textureName ==
        "textures/xziel/sanctum/test");
    assert(directoryBatch.vertexCount == 3U);
    assert(directoryBatch.indexCount == 3U);
    assert(
        directoryBatch.vertexDataOffset <
        directoryBatch.indexDataOffset);
    assert(
        directoryBatch.indexDataOffset +
            3U * sizeof(std::uint16_t) ==
        encoded.size());
    assert(
        directoryBatch.payloadBytes ==
        encoded.size() -
            directoryBatch.vertexDataOffset);
    assert(!directoryBatch.doubleSided());

    const auto photoPbrEncoded =
        makeTriangle(
            xziel::kStaticMeshFormatVersion,
            true,
            xziel::StaticMeshBatchFlagPhotogrammetryPbr);

    xziel::StaticMeshAsset photoPbrAsset;
    const auto photoPbrParsed =
        xziel::parseStaticMeshXzsm(
            photoPbrEncoded,
            photoPbrAsset);

    assert(photoPbrParsed.success);
    assert(photoPbrAsset.batches.size() == 1U);
    assert(photoPbrAsset.batches[0].pbrEnabled());
    assert(photoPbrAsset.batches[0].photogrammetryPbr());

    xziel::StaticMeshDirectory photoPbrDirectory;
    const auto photoPbrDirectoryParsed =
        xziel::parseStaticMeshXzsmDirectory(
            photoPbrEncoded,
            photoPbrDirectory);

    assert(photoPbrDirectoryParsed.success);
    assert(
        photoPbrDirectory.batches[0].
            photogrammetryPbr());

    // Mixed v5 assets can use the v5 record layout while leaving legacy
    // photogrammetry batches on the source-fidelity non-PBR path.
    const auto neutralV5Encoded =
        makeTriangle(
            xziel::kStaticMeshFormatVersion,
            false);

    xziel::StaticMeshAsset neutralV5Asset;
    const auto neutralV5Parsed =
        xziel::parseStaticMeshXzsm(
            neutralV5Encoded,
            neutralV5Asset);

    assert(neutralV5Parsed.success);
    assert(neutralV5Asset.batches.size() == 1U);
    assert(!neutralV5Asset.batches[0].pbrEnabled());
    assert(
        neutralV5Asset.batches[0].
            pbr.normalTextureName.empty());
    assert(
        neutralV5Asset.batches[0].
            pbr.ormTextureName.empty());
    assert(
        neutralV5Asset.batches[0].
            pbr.roughnessFactor == 1.0f);

    const auto v4Encoded =
        makeTriangle(
            xziel::kStaticMeshMaterialFlagsVersion);

    xziel::StaticMeshAsset v4Asset;
    const auto v4Parsed =
        xziel::parseStaticMeshXzsm(
            v4Encoded,
            v4Asset);

    assert(v4Parsed.success);

    xziel::StaticMeshDirectory v4Directory;
    const auto v4DirectoryParsed =
        xziel::parseStaticMeshXzsmDirectory(
            v4Encoded,
            v4Directory);
    assert(v4DirectoryParsed.success);
    assert(
        v4Directory.version ==
        xziel::kStaticMeshMaterialFlagsVersion);
    assert(v4Directory.batches.size() == 1U);
    assert(
        v4Directory.batches[0].indexDataOffset +
            3U * sizeof(std::uint16_t) ==
        v4Encoded.size());

    assert(!v4Asset.batches[0].doubleSided());
    assert(!v4Asset.batches[0].pbrEnabled());
    assert(v4Asset.batches[0].pbr.normalTextureName.empty());
    assert(v4Asset.batches[0].pbr.metallicFactor == 0.0f);
    assert(v4Asset.batches[0].pbr.roughnessFactor == 1.0f);

    const auto v3Encoded =
        makeTriangle(
            xziel::kStaticMeshNormalsVersion);

    xziel::StaticMeshAsset v3Asset;
    const auto v3Parsed =
        xziel::parseStaticMeshXzsm(
            v3Encoded,
            v3Asset);

    assert(v3Parsed.success);
    // v3 had no material-side metadata; preserve the old renderer behavior.
    assert(v3Asset.batches[0].doubleSided());
    assert(v3Asset.batches[0].vertices[0].nz > 0.99f);

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

    xziel::StaticMeshDirectory truncatedDirectory;
    const auto truncatedDirectoryResult =
        xziel::parseStaticMeshXzsmDirectory(
            truncated,
            truncatedDirectory);
    assert(!truncatedDirectoryResult.success);
    assert(
        truncatedDirectoryResult.error ==
        xziel::StaticMeshParseError::
            Truncated);
    assert(truncatedDirectory.batches.empty());

    return 0;
}
