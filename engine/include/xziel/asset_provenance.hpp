#pragma once

#include <cstdint>
#include <string_view>

namespace xziel {

enum class AssetCategory : std::uint8_t {
    Model,
    Animation,
    Texture,
    ParticleTexture,
    Audio,
    Font,
    Map,
    Shader,
    CodeDependency,
};

enum class AssetLicense : std::uint8_t {
    Original,
    CC0_1_0,
    CC_BY_4_0,
    CC_BY_SA_4_0,
    MIT,
    BSD_2_Clause,
    BSD_3_Clause,
    Apache_2_0,
    Zlib,
    GPL_2_0,
    GPL_3_0,
    Unknown,
    NonCommercial,
    EditorialOnly,
    Proprietary,
};

enum class AssetPolicyDecision : std::uint8_t {
    Accept,
    AcceptWithAttribution,
    AcceptWithShareAlike,
    RejectUnknownRights,
    RejectNonCommercial,
    RejectEditorialOnly,
    RejectProprietary,
    RejectShareAlike,
    RejectCopyleftCode,
};

struct AssetProvenanceRecord {
    std::string_view logicalId{};
    std::string_view sourceUrl{};
    std::string_view author{};
    std::string_view licenseTextOrUrl{};
    std::string_view contentHash{};

    AssetCategory category =
        AssetCategory::Model;

    AssetLicense license =
        AssetLicense::Unknown;

    bool modified = false;
};

struct AssetUsagePolicy {
    bool commercialDistribution = true;
    bool allowShareAlikeAssets = false;
    bool allowCopyleftCodeDependencies = false;
};

struct AssetPolicyResult {
    AssetPolicyDecision decision =
        AssetPolicyDecision::RejectUnknownRights;

    bool allowed = false;
    bool attributionRequired = false;
    bool shareAlikeRequired = false;
    bool sourceObligationsPossible = false;
};

[[nodiscard]] AssetPolicyResult evaluateAssetProvenance(
    const AssetProvenanceRecord& record,
    const AssetUsagePolicy& policy = {}) noexcept;

[[nodiscard]] std::string_view assetLicenseName(
    AssetLicense license) noexcept;

} // namespace xziel
