#include "xziel/asset_provenance.hpp"

namespace xziel {

AssetPolicyResult evaluateAssetProvenance(
    const AssetProvenanceRecord& record,
    const AssetUsagePolicy& policy) noexcept {
    AssetPolicyResult result{};

    switch (record.license) {
        case AssetLicense::Original:
        case AssetLicense::CC0_1_0:
        case AssetLicense::MIT:
        case AssetLicense::BSD_2_Clause:
        case AssetLicense::BSD_3_Clause:
        case AssetLicense::Apache_2_0:
        case AssetLicense::Zlib:
            result.allowed = true;
            result.decision =
                AssetPolicyDecision::Accept;
            return result;

        case AssetLicense::CC_BY_4_0:
            result.allowed = true;
            result.attributionRequired = true;
            result.decision =
                AssetPolicyDecision::AcceptWithAttribution;
            return result;

        case AssetLicense::CC_BY_SA_4_0:
            result.attributionRequired = true;
            result.shareAlikeRequired = true;

            if (!policy.allowShareAlikeAssets) {
                result.decision =
                    AssetPolicyDecision::RejectShareAlike;
                return result;
            }

            result.allowed = true;
            result.decision =
                AssetPolicyDecision::AcceptWithShareAlike;
            return result;

        case AssetLicense::GPL_2_0:
        case AssetLicense::GPL_3_0:
            result.sourceObligationsPossible = true;

            if (record.category !=
                    AssetCategory::CodeDependency ||
                !policy.allowCopyleftCodeDependencies) {
                result.decision =
                    AssetPolicyDecision::RejectCopyleftCode;
                return result;
            }

            result.allowed = true;
            result.decision =
                AssetPolicyDecision::Accept;
            return result;

        case AssetLicense::NonCommercial:
            result.decision =
                AssetPolicyDecision::RejectNonCommercial;
            return result;

        case AssetLicense::EditorialOnly:
            result.decision =
                AssetPolicyDecision::RejectEditorialOnly;
            return result;

        case AssetLicense::Proprietary:
            result.decision =
                AssetPolicyDecision::RejectProprietary;
            return result;

        case AssetLicense::Unknown:
        default:
            result.decision =
                AssetPolicyDecision::RejectUnknownRights;
            return result;
    }
}

std::string_view assetLicenseName(
    AssetLicense license) noexcept {
    switch (license) {
        case AssetLicense::Original:
            return "Original";
        case AssetLicense::CC0_1_0:
            return "CC0-1.0";
        case AssetLicense::CC_BY_4_0:
            return "CC-BY-4.0";
        case AssetLicense::CC_BY_SA_4_0:
            return "CC-BY-SA-4.0";
        case AssetLicense::MIT:
            return "MIT";
        case AssetLicense::BSD_2_Clause:
            return "BSD-2-Clause";
        case AssetLicense::BSD_3_Clause:
            return "BSD-3-Clause";
        case AssetLicense::Apache_2_0:
            return "Apache-2.0";
        case AssetLicense::Zlib:
            return "Zlib";
        case AssetLicense::GPL_2_0:
            return "GPL-2.0";
        case AssetLicense::GPL_3_0:
            return "GPL-3.0";
        case AssetLicense::NonCommercial:
            return "NonCommercial";
        case AssetLicense::EditorialOnly:
            return "EditorialOnly";
        case AssetLicense::Proprietary:
            return "Proprietary";
        case AssetLicense::Unknown:
        default:
            return "Unknown";
    }
}

} // namespace xziel
