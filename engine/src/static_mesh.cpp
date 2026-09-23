#include "xziel/static_mesh.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>
#include <type_traits>

namespace xziel {

namespace {

class Reader final {
public:
    explicit Reader(
        std::span<const std::byte> bytes) noexcept
        : bytes_(bytes) {}

    [[nodiscard]] std::size_t offset() const noexcept {
        return offset_;
    }

    [[nodiscard]] std::size_t remaining() const noexcept {
        return bytes_.size() - offset_;
    }

    [[nodiscard]] bool readBytes(
        void* destination,
        std::size_t size) noexcept {
        if (destination == nullptr ||
            size > remaining()) {
            return false;
        }

        std::memcpy(
            destination,
            bytes_.data() + offset_,
            size);

        offset_ += size;
        return true;
    }

    [[nodiscard]] bool readU16(
        std::uint16_t& value) noexcept {
        std::array<std::uint8_t, 2> raw{};
        if (!readBytes(raw.data(), raw.size())) {
            return false;
        }

        value =
            static_cast<std::uint16_t>(
                raw[0]) |
            static_cast<std::uint16_t>(
                static_cast<std::uint16_t>(raw[1])
                << 8U);
        return true;
    }

    [[nodiscard]] bool readU32(
        std::uint32_t& value) noexcept {
        std::array<std::uint8_t, 4> raw{};
        if (!readBytes(raw.data(), raw.size())) {
            return false;
        }

        value =
            static_cast<std::uint32_t>(raw[0]) |
            (static_cast<std::uint32_t>(raw[1]) << 8U) |
            (static_cast<std::uint32_t>(raw[2]) << 16U) |
            (static_cast<std::uint32_t>(raw[3]) << 24U);
        return true;
    }

    [[nodiscard]] bool readF32(
        float& value) noexcept {
        std::uint32_t bits = 0U;
        if (!readU32(bits)) {
            return false;
        }

        value = std::bit_cast<float>(bits);
        return std::isfinite(value);
    }

private:
    std::span<const std::byte> bytes_{};
    std::size_t offset_ = 0U;
};

StaticMeshParseResult failure(
    StaticMeshParseError error,
    std::size_t offset,
    StaticMeshAsset& destination) noexcept {
    destination = {};
    return {
        .success = false,
        .error = error,
        .offset = offset,
    };
}

[[nodiscard]] bool safeBatchStorage(
    std::uint32_t vertexCount,
    std::uint32_t indexCount) noexcept {
    if (vertexCount == 0U ||
        vertexCount > 65535U ||
        indexCount == 0U ||
        (indexCount % 3U) != 0U) {
        return false;
    }

    const std::size_t vertexBytes =
        static_cast<std::size_t>(
            vertexCount) *
        sizeof(StaticMeshVertex);

    const std::size_t indexBytes =
        static_cast<std::size_t>(
            indexCount) *
        sizeof(std::uint16_t);

    return vertexBytes /
            sizeof(StaticMeshVertex) ==
        vertexCount &&
        indexBytes /
            sizeof(std::uint16_t) ==
        indexCount;
}

} // namespace

StaticMeshParseResult
parseStaticMeshXzsm(
    std::span<const std::byte> bytes,
    StaticMeshAsset& destination) noexcept {
    destination = {};

    Reader reader(bytes);

    std::array<char, 4> magic{};
    std::uint32_t version = 0U;
    std::uint32_t batchCount = 0U;
    std::uint32_t declaredVertices = 0U;
    std::uint32_t declaredIndices = 0U;

    if (!reader.readBytes(
            magic.data(),
            magic.size()) ||
        !reader.readU32(version) ||
        !reader.readU32(batchCount) ||
        !reader.readU32(declaredVertices) ||
        !reader.readU32(declaredIndices)) {
        return failure(
            StaticMeshParseError::Truncated,
            reader.offset(),
            destination);
    }

    if (magic !=
        std::array<char, 4>{'X', 'Z', 'S', 'M'}) {
        return failure(
            StaticMeshParseError::InvalidMagic,
            0U,
            destination);
    }

    if (version != kStaticMeshLegacyVersion &&
        version != kStaticMeshNormalsVersion &&
        version != kStaticMeshMaterialFlagsVersion &&
        version != kStaticMeshFormatVersion) {
        return failure(
            StaticMeshParseError::UnsupportedVersion,
            4U,
            destination);
    }

    if (batchCount == 0U ||
        batchCount > kMaxStaticMeshBatches ||
        declaredVertices == 0U ||
        declaredVertices > kMaxStaticMeshVertices ||
        declaredIndices == 0U ||
        declaredIndices > kMaxStaticMeshIndices) {
        return failure(
            StaticMeshParseError::CapacityExceeded,
            reader.offset(),
            destination);
    }

    try {
        destination.batches.reserve(batchCount);
    } catch (...) {
        return failure(
            StaticMeshParseError::CapacityExceeded,
            reader.offset(),
            destination);
    }

    std::uint64_t seenVertices = 0U;
    std::uint64_t seenIndices = 0U;

    for (std::uint32_t batchIndex = 0U;
         batchIndex < batchCount;
         ++batchIndex) {
        std::uint32_t vertexCount = 0U;
        std::uint32_t indexCount = 0U;
        std::array<char, 96> texture{};
        std::array<char, 96> normalTexture{};
        std::array<char, 96> ormTexture{};
        std::array<char, 96> emissiveTexture{};
        StaticMeshPbrMaterial pbr{};
        StaticMeshBounds bounds{};
        std::uint32_t flags =
            StaticMeshBatchFlagDoubleSided;

        if (!reader.readU32(vertexCount) ||
            !reader.readU32(indexCount) ||
            !reader.readBytes(
                texture.data(),
                texture.size())) {
            return failure(
                StaticMeshParseError::Truncated,
                reader.offset(),
                destination);
        }

        if (version >= kStaticMeshMaterialFlagsVersion) {
            if (!reader.readU32(flags)) {
                return failure(
                    StaticMeshParseError::Truncated,
                    reader.offset(),
                    destination);
            }

            constexpr std::uint32_t kKnownFlags =
                StaticMeshBatchFlagDoubleSided;

            if ((flags & ~kKnownFlags) != 0U) {
                return failure(
                    StaticMeshParseError::InvalidBatch,
                    reader.offset(),
                    destination);
            }
        }

        if (version >= kStaticMeshFormatVersion) {
            if (!reader.readBytes(
                    normalTexture.data(),
                    normalTexture.size()) ||
                !reader.readBytes(
                    ormTexture.data(),
                    ormTexture.size()) ||
                !reader.readBytes(
                    emissiveTexture.data(),
                    emissiveTexture.size())) {
                return failure(
                    StaticMeshParseError::Truncated,
                    reader.offset(),
                    destination);
            }

            for (float& value : pbr.baseColorFactor) {
                if (!reader.readF32(value)) {
                    return failure(
                        StaticMeshParseError::InvalidBatch,
                        reader.offset(),
                        destination);
                }
            }

            if (!reader.readF32(pbr.metallicFactor) ||
                !reader.readF32(pbr.roughnessFactor)) {
                return failure(
                    StaticMeshParseError::InvalidBatch,
                    reader.offset(),
                    destination);
            }

            for (float& value : pbr.emissiveFactor) {
                if (!reader.readF32(value)) {
                    return failure(
                        StaticMeshParseError::InvalidBatch,
                        reader.offset(),
                        destination);
                }
            }

            if (!reader.readF32(pbr.normalScale) ||
                !reader.readF32(pbr.occlusionStrength)) {
                return failure(
                    StaticMeshParseError::InvalidBatch,
                    reader.offset(),
                    destination);
            }

            const auto unitRange =
                [](float value) noexcept {
                    return value >= 0.0f && value <= 1.0f;
                };

            if (!std::all_of(
                    pbr.baseColorFactor.begin(),
                    pbr.baseColorFactor.end(),
                    unitRange) ||
                !unitRange(pbr.metallicFactor) ||
                !unitRange(pbr.roughnessFactor) ||
                !unitRange(pbr.occlusionStrength) ||
                pbr.normalScale < 0.0f ||
                !std::all_of(
                    pbr.emissiveFactor.begin(),
                    pbr.emissiveFactor.end(),
                    [](float value) noexcept {
                        return value >= 0.0f;
                    })) {
                return failure(
                    StaticMeshParseError::InvalidBatch,
                    reader.offset(),
                    destination);
            }
        }

        for (float& value : bounds.minimum) {
            if (!reader.readF32(value)) {
                return failure(
                    StaticMeshParseError::InvalidBatch,
                    reader.offset(),
                    destination);
            }
        }

        for (float& value : bounds.maximum) {
            if (!reader.readF32(value)) {
                return failure(
                    StaticMeshParseError::InvalidBatch,
                    reader.offset(),
                    destination);
            }
        }

        if (!safeBatchStorage(
                vertexCount,
                indexCount)) {
            return failure(
                StaticMeshParseError::InvalidBatch,
                reader.offset(),
                destination);
        }

        for (std::size_t axis = 0U;
             axis < 3U;
             ++axis) {
            if (bounds.minimum[axis] >
                bounds.maximum[axis]) {
                return failure(
                    StaticMeshParseError::InvalidBatch,
                    reader.offset(),
                    destination);
            }
        }

        seenVertices += vertexCount;
        seenIndices += indexCount;

        if (seenVertices > declaredVertices ||
            seenIndices > declaredIndices ||
            seenVertices > kMaxStaticMeshVertices ||
            seenIndices > kMaxStaticMeshIndices) {
            return failure(
                StaticMeshParseError::TotalMismatch,
                reader.offset(),
                destination);
        }

        StaticMeshBatch batch{};
        const auto nul =
            std::find(
                texture.begin(),
                texture.end(),
                '\0');

        batch.textureName.assign(
            texture.begin(),
            nul);

        if (version >= kStaticMeshFormatVersion) {
            const auto assignOptionalTexture =
                [](const std::array<char, 96>& field) {
                    const auto end =
                        std::find(
                            field.begin(),
                            field.end(),
                            '\0');
                    return std::string(
                        field.begin(),
                        end);
                };

            pbr.normalTextureName =
                assignOptionalTexture(normalTexture);
            pbr.ormTextureName =
                assignOptionalTexture(ormTexture);
            pbr.emissiveTextureName =
                assignOptionalTexture(emissiveTexture);
            batch.pbr = std::move(pbr);
        }

        batch.bounds = bounds;
        batch.flags = flags;
        batch.pbrMaterial =
            version >= kStaticMeshFormatVersion;

        if (batch.textureName.empty()) {
            return failure(
                StaticMeshParseError::InvalidBatch,
                reader.offset(),
                destination);
        }

        try {
            batch.vertices.resize(vertexCount);
            batch.indices.resize(indexCount);
        } catch (...) {
            return failure(
                StaticMeshParseError::CapacityExceeded,
                reader.offset(),
                destination);
        }

        for (auto& vertex : batch.vertices) {
            if (!reader.readF32(vertex.x) ||
                !reader.readF32(vertex.y) ||
                !reader.readF32(vertex.z)) {
                return failure(
                    StaticMeshParseError::Truncated,
                    reader.offset(),
                    destination);
            }

            if (version >= kStaticMeshNormalsVersion) {
                if (!reader.readF32(vertex.nx) ||
                    !reader.readF32(vertex.ny) ||
                    !reader.readF32(vertex.nz)) {
                    return failure(
                        StaticMeshParseError::Truncated,
                        reader.offset(),
                        destination);
                }

                const float normalLengthSquared =
                    vertex.nx * vertex.nx +
                    vertex.ny * vertex.ny +
                    vertex.nz * vertex.nz;

                if (!std::isfinite(normalLengthSquared) ||
                    normalLengthSquared < 1.0e-8f) {
                    return failure(
                        StaticMeshParseError::InvalidBatch,
                        reader.offset(),
                        destination);
                }

                const float inverseLength =
                    1.0f /
                    std::sqrt(
                        normalLengthSquared);

                vertex.nx *= inverseLength;
                vertex.ny *= inverseLength;
                vertex.nz *= inverseLength;
            } else {
                // v2 assets predate stored normals. Keep them readable for
                // compatibility, but native Sanctum exports use v3.
                vertex.nx = 0.0f;
                vertex.ny = 1.0f;
                vertex.nz = 0.0f;
            }

            if (!reader.readF32(vertex.u) ||
                !reader.readF32(vertex.v) ||
                !reader.readBytes(
                    vertex.rgba.data(),
                    vertex.rgba.size())) {
                return failure(
                    StaticMeshParseError::Truncated,
                    reader.offset(),
                    destination);
            }
        }

        for (auto& index : batch.indices) {
            if (!reader.readU16(index)) {
                return failure(
                    StaticMeshParseError::Truncated,
                    reader.offset(),
                    destination);
            }

            if (index >= vertexCount) {
                return failure(
                    StaticMeshParseError::InvalidIndex,
                    reader.offset(),
                    destination);
            }
        }

        destination.batches.emplace_back(
            std::move(batch));
    }

    if (seenVertices != declaredVertices ||
        seenIndices != declaredIndices) {
        return failure(
            StaticMeshParseError::TotalMismatch,
            reader.offset(),
            destination);
    }

    if (reader.remaining() != 0U) {
        return failure(
            StaticMeshParseError::TrailingData,
            reader.offset(),
            destination);
    }

    destination.totalVertices =
        declaredVertices;
    destination.totalIndices =
        declaredIndices;

    return {
        .success = true,
        .error = StaticMeshParseError::None,
        .offset = reader.offset(),
    };
}

} // namespace xziel
