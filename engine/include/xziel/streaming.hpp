#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace xziel {

enum class StreamResourceKind : std::uint8_t {
    Texture,
    Mesh,
    AudioBank,
};

struct StreamResourceDesc {
    std::uint64_t id = 0;
    StreamResourceKind kind = StreamResourceKind::Texture;
    std::uint64_t bytes = 0;

    bool pinned = false;
    bool resident = true;
};

struct EvictionCandidate {
    std::uint64_t id = 0;
    StreamResourceKind kind = StreamResourceKind::Texture;
    std::uint64_t bytes = 0;
};

struct ResidencyStats {
    std::uint64_t textureBytes = 0;
    std::uint64_t meshBytes = 0;
    std::uint64_t audioBytes = 0;
    std::uint32_t residentCount = 0;
};

inline constexpr std::size_t kMaxStreamedTextureMips = 16U;

struct TextureMipChainDesc {
    std::uint64_t id = 0U;
    std::uint32_t mipCount = 0U;
    std::array<std::uint64_t, kMaxStreamedTextureMips>
        mipBytes{};

    // Mip 0 is highest resolution. A residentBaseMip of N means mips
    // [N, mipCount) are resident and form a complete sampleable tail.
    std::uint32_t residentBaseMip = 0U;
    std::uint32_t requestedBaseMip = 0U;
    bool pinned = false;
};

struct TextureMipChange {
    std::uint64_t id = 0U;
    std::uint32_t oldBaseMip = 0U;
    std::uint32_t newBaseMip = 0U;
    std::uint64_t bytesChanged = 0U;
};

struct TextureMipResidencyStats {
    std::uint64_t residentBytes = 0U;
    std::uint64_t requestedBytes = 0U;
    std::uint32_t textureCount = 0U;
    std::uint32_t degradedTextureCount = 0U;
};

class TextureMipResidencyManager final {
public:
    explicit TextureMipResidencyManager(
        std::uint32_t maxTextures = 1024U);

    [[nodiscard]] bool registerTexture(
        const TextureMipChainDesc& desc,
        std::uint64_t frameIndex) noexcept;

    void touch(
        std::uint64_t id,
        std::uint32_t requestedBaseMip,
        std::uint64_t frameIndex) noexcept;

    void setPinned(
        std::uint64_t id,
        bool pinned) noexcept;

    [[nodiscard]] bool applyResidentBaseMip(
        std::uint64_t id,
        std::uint32_t baseMip,
        std::uint64_t frameIndex) noexcept;

    // Demotions keep at least the final 1x1-ish mip resident. The planner
    // chooses stale, non-pinned textures first and may drop several top mips
    // in one action to meet the requested byte target without evicting the
    // whole texture.
    [[nodiscard]] std::size_t planDemotions(
        std::uint64_t targetBytesToFree,
        std::uint64_t currentFrame,
        std::uint64_t minimumUnusedFrames,
        TextureMipChange* destination,
        std::size_t destinationCapacity) const noexcept;

    // Promotions are intentionally gradual: at most one higher-resolution mip
    // per texture per planning pass, ordered by most-recent use.
    [[nodiscard]] std::size_t planPromotions(
        std::uint64_t availableBytes,
        std::uint64_t currentFrame,
        std::uint64_t maximumUnusedFrames,
        TextureMipChange* destination,
        std::size_t destinationCapacity) const noexcept;

    [[nodiscard]] TextureMipResidencyStats stats() const noexcept;

private:
    struct Slot {
        TextureMipChainDesc desc{};
        std::uint64_t lastTouchedFrame = 0U;
        bool occupied = false;
    };

    [[nodiscard]] static bool valid(
        const TextureMipChainDesc& desc) noexcept;

    [[nodiscard]] static std::uint64_t bytesFromMip(
        const TextureMipChainDesc& desc,
        std::uint32_t baseMip) noexcept;

    [[nodiscard]] Slot* find(std::uint64_t id) noexcept;
    [[nodiscard]] const Slot* find(std::uint64_t id) const noexcept;

    std::vector<Slot> slots_;
};

class ResidencyManager final {
public:
    explicit ResidencyManager(std::uint32_t maxResources = 4096);

    [[nodiscard]] bool registerResource(
        const StreamResourceDesc& desc,
        std::uint64_t frameIndex) noexcept;

    void touch(
        std::uint64_t id,
        std::uint64_t frameIndex) noexcept;

    void setPinned(
        std::uint64_t id,
        bool pinned) noexcept;

    void setResident(
        std::uint64_t id,
        bool resident,
        std::uint64_t frameIndex) noexcept;

    [[nodiscard]] std::size_t planEvictions(
        std::uint64_t targetBytesToFree,
        std::uint64_t currentFrame,
        std::uint64_t minimumUnusedFrames,
        EvictionCandidate* destination,
        std::size_t destinationCapacity) const noexcept;

    [[nodiscard]] ResidencyStats stats() const noexcept;

private:
    struct Slot {
        StreamResourceDesc desc{};
        std::uint64_t lastTouchedFrame = 0;
        bool occupied = false;
    };

    [[nodiscard]] Slot* find(std::uint64_t id) noexcept;
    [[nodiscard]] const Slot* find(std::uint64_t id) const noexcept;

    std::vector<Slot> slots_;
};

} // namespace xziel
