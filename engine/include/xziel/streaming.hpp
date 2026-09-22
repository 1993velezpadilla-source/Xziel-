#pragma once

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
