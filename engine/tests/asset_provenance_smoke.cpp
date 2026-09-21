#include "xziel/asset_provenance.hpp"

#include <cassert>

int main() {
    xziel::AssetProvenanceRecord cc0{};
    cc0.logicalId = "rain/splash-a";
    cc0.category =
        xziel::AssetCategory::ParticleTexture;
    cc0.license =
        xziel::AssetLicense::CC0_1_0;

    const auto cc0Result =
        xziel::evaluateAssetProvenance(
            cc0);

    assert(cc0Result.allowed);
    assert(
        !cc0Result.attributionRequired);

    xziel::AssetProvenanceRecord attribution{};
    attribution.logicalId = "fog/model-a";
    attribution.category =
        xziel::AssetCategory::Model;
    attribution.license =
        xziel::AssetLicense::CC_BY_4_0;

    const auto attributionResult =
        xziel::evaluateAssetProvenance(
            attribution);

    assert(
        attributionResult.allowed);
    assert(
        attributionResult.attributionRequired);

    xziel::AssetProvenanceRecord nonCommercial{};
    nonCommercial.license =
        xziel::AssetLicense::NonCommercial;

    assert(
        !xziel::evaluateAssetProvenance(
             nonCommercial).allowed);

    xziel::AssetProvenanceRecord shareAlike{};
    shareAlike.license =
        xziel::AssetLicense::CC_BY_SA_4_0;

    assert(
        !xziel::evaluateAssetProvenance(
             shareAlike).allowed);

    xziel::AssetUsagePolicy legacyPack{};
    legacyPack.allowShareAlikeAssets = true;

    const auto shareAlikeAllowed =
        xziel::evaluateAssetProvenance(
            shareAlike,
            legacyPack);

    assert(
        shareAlikeAllowed.allowed);
    assert(
        shareAlikeAllowed.shareAlikeRequired);

    xziel::AssetProvenanceRecord gplCode{};
    gplCode.category =
        xziel::AssetCategory::CodeDependency;
    gplCode.license =
        xziel::AssetLicense::GPL_2_0;

    assert(
        !xziel::evaluateAssetProvenance(
             gplCode).allowed);

    xziel::AssetUsagePolicy gplBuild{};
    gplBuild.allowCopyleftCodeDependencies =
        true;

    assert(
        xziel::evaluateAssetProvenance(
            gplCode,
            gplBuild).allowed);

    return 0;
}
