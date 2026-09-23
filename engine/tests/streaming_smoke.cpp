#include "xziel/streaming.hpp"

#include <array>
#include <cassert>
#include <cstdint>

int main() {
    xziel::ResidencyManager manager(8);

    assert(manager.registerResource(
        {.id = 1, .kind = xziel::StreamResourceKind::Texture, .bytes = 64, .pinned = true},
        1));
    assert(manager.registerResource(
        {.id = 2, .kind = xziel::StreamResourceKind::Texture, .bytes = 128},
        2));
    assert(manager.registerResource(
        {.id = 3, .kind = xziel::StreamResourceKind::Mesh, .bytes = 96},
        20));
    assert(manager.registerResource(
        {.id = 4, .kind = xziel::StreamResourceKind::AudioBank, .bytes = 80},
        3));

    const auto before = manager.stats();
    assert(before.residentCount == 4);
    assert(before.textureBytes == 192);

    std::array<xziel::EvictionCandidate, 4> evictions{};
    const auto count = manager.planEvictions(
        160,
        100,
        10,
        evictions.data(),
        evictions.size());

    assert(count >= 2);

    // Resource 1 is pinned and may never be selected.
    for (std::size_t i = 0; i < count; ++i) {
        assert(evictions[i].id != 1);
        manager.setResident(evictions[i].id, false, 100);
    }

    const auto after = manager.stats();
    assert(after.residentCount < before.residentCount);

    xziel::TextureMipResidencyManager mipManager(4);

    xziel::TextureMipChainDesc stale{};
    stale.id = 101U;
    stale.mipCount = 4U;
    stale.mipBytes = {
        1024U, 256U, 64U, 16U};
    stale.residentBaseMip = 0U;
    stale.requestedBaseMip = 0U;

    xziel::TextureMipChainDesc pinned{};
    pinned.id = 102U;
    pinned.mipCount = 4U;
    pinned.mipBytes = {
        2048U, 512U, 128U, 32U};
    pinned.residentBaseMip = 0U;
    pinned.requestedBaseMip = 0U;
    pinned.pinned = true;

    xziel::TextureMipChainDesc recent{};
    recent.id = 103U;
    recent.mipCount = 4U;
    recent.mipBytes = {
        1024U, 256U, 64U, 16U};
    recent.residentBaseMip = 2U;
    recent.requestedBaseMip = 0U;

    assert(
        mipManager.registerTexture(
            stale,
            1U));
    assert(
        mipManager.registerTexture(
            pinned,
            1U));
    assert(
        mipManager.registerTexture(
            recent,
            95U));

    auto mipStats =
        mipManager.stats();

    assert(
        mipStats.textureCount == 3U);
    assert(
        mipStats.degradedTextureCount == 1U);
    assert(
        mipStats.residentBytes ==
        (1360U + 2720U + 80U));

    std::array<xziel::TextureMipChange, 4>
        mipChanges{};

    const auto demotionCount =
        mipManager.planDemotions(
            700U,
            100U,
            50U,
            mipChanges.data(),
            mipChanges.size());

    assert(demotionCount == 1U);
    assert(mipChanges[0].id == 101U);
    assert(
        mipChanges[0].oldBaseMip == 0U);
    assert(
        mipChanges[0].newBaseMip == 1U);
    assert(
        mipChanges[0].bytesChanged ==
        1024U);

    assert(
        mipManager.applyResidentBaseMip(
            mipChanges[0].id,
            mipChanges[0].newBaseMip,
            100U));

    mipStats = mipManager.stats();
    assert(
        mipStats.degradedTextureCount == 2U);

    // A small promotion budget should restore the recently used texture from
    // mip 2 -> 1 first. It needs only the 256-byte mip while stale mip 0 would
    // require 1024 bytes.
    mipManager.touch(
        103U,
        0U,
        101U);

    const auto promotionCount =
        mipManager.planPromotions(
            300U,
            101U,
            20U,
            mipChanges.data(),
            mipChanges.size());

    assert(promotionCount == 1U);
    assert(mipChanges[0].id == 103U);
    assert(
        mipChanges[0].oldBaseMip == 2U);
    assert(
        mipChanges[0].newBaseMip == 1U);
    assert(
        mipChanges[0].bytesChanged ==
        256U);

    assert(
        mipManager.applyResidentBaseMip(
            103U,
            1U,
            101U));

    // Pinned textures are never selected for demotion.
    mipManager.setPinned(101U, true);

    const auto pinnedDemotions =
        mipManager.planDemotions(
            4096U,
            1000U,
            50U,
            mipChanges.data(),
            mipChanges.size());

    for (std::size_t i = 0U;
         i < pinnedDemotions;
         ++i) {
        assert(mipChanges[i].id != 101U);
        assert(mipChanges[i].id != 102U);
    }

    mipManager.reset();
    mipStats = mipManager.stats();
    assert(mipStats.textureCount == 0U);
    assert(mipStats.residentBytes == 0U);
    assert(mipStats.requestedBytes == 0U);
    assert(mipStats.degradedTextureCount == 0U);

    xziel::TextureMipChainDesc invalid{};
    invalid.id = 999U;
    invalid.mipCount = 2U;
    invalid.mipBytes = {128U, 0U};

    assert(
        !mipManager.registerTexture(
            invalid,
            0U));

    return 0;
}
