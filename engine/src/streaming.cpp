#include "xziel/streaming.hpp"

#include <algorithm>
#include <limits>

namespace xziel {

ResidencyManager::ResidencyManager(std::uint32_t maxResources)
    : slots_(std::max<std::uint32_t>(1U, maxResources)) {}

bool ResidencyManager::registerResource(
    const StreamResourceDesc& desc,
    std::uint64_t frameIndex) noexcept {
    if (desc.id == 0 || desc.bytes == 0) {
        return false;
    }

    if (auto* existing = find(desc.id)) {
        existing->desc = desc;
        existing->lastTouchedFrame = frameIndex;
        return true;
    }

    for (auto& slot : slots_) {
        if (!slot.occupied) {
            slot.occupied = true;
            slot.desc = desc;
            slot.lastTouchedFrame = frameIndex;
            return true;
        }
    }

    return false;
}

void ResidencyManager::touch(
    std::uint64_t id,
    std::uint64_t frameIndex) noexcept {
    if (auto* slot = find(id)) {
        slot->lastTouchedFrame = frameIndex;
    }
}

void ResidencyManager::setPinned(
    std::uint64_t id,
    bool pinned) noexcept {
    if (auto* slot = find(id)) {
        slot->desc.pinned = pinned;
    }
}

void ResidencyManager::setResident(
    std::uint64_t id,
    bool resident,
    std::uint64_t frameIndex) noexcept {
    if (auto* slot = find(id)) {
        slot->desc.resident = resident;
        slot->lastTouchedFrame = frameIndex;
    }
}

std::size_t ResidencyManager::planEvictions(
    std::uint64_t targetBytesToFree,
    std::uint64_t currentFrame,
    std::uint64_t minimumUnusedFrames,
    EvictionCandidate* destination,
    std::size_t destinationCapacity) const noexcept {
    if (destination == nullptr ||
        destinationCapacity == 0 ||
        targetBytesToFree == 0) {
        return 0;
    }

    std::uint64_t freed = 0;
    std::size_t written = 0;

    // Fixed-capacity selection without heap allocation/sorting. Each pass picks
    // the stalest eligible resource not already emitted. Eviction planning is
    // not a per-draw operation and resource counts are bounded.
    while (written < destinationCapacity &&
           freed < targetBytesToFree) {
        const Slot* best = nullptr;
        std::uint64_t bestAge = 0;

        for (const auto& slot : slots_) {
            if (!slot.occupied ||
                !slot.desc.resident ||
                slot.desc.pinned) {
                continue;
            }

            bool alreadyChosen = false;
            for (std::size_t i = 0; i < written; ++i) {
                if (destination[i].id == slot.desc.id) {
                    alreadyChosen = true;
                    break;
                }
            }
            if (alreadyChosen) {
                continue;
            }

            const std::uint64_t age =
                currentFrame >= slot.lastTouchedFrame
                ? currentFrame - slot.lastTouchedFrame
                : 0;

            if (age < minimumUnusedFrames) {
                continue;
            }

            if (best == nullptr ||
                age > bestAge ||
                (age == bestAge &&
                 slot.desc.bytes > best->desc.bytes)) {
                best = &slot;
                bestAge = age;
            }
        }

        if (best == nullptr) {
            break;
        }

        destination[written++] = {
            .id = best->desc.id,
            .kind = best->desc.kind,
            .bytes = best->desc.bytes,
        };
        freed += best->desc.bytes;
    }

    return written;
}

ResidencyStats ResidencyManager::stats() const noexcept {
    ResidencyStats out{};

    for (const auto& slot : slots_) {
        if (!slot.occupied || !slot.desc.resident) {
            continue;
        }

        ++out.residentCount;
        switch (slot.desc.kind) {
            case StreamResourceKind::Texture:
                out.textureBytes += slot.desc.bytes;
                break;
            case StreamResourceKind::Mesh:
                out.meshBytes += slot.desc.bytes;
                break;
            case StreamResourceKind::AudioBank:
                out.audioBytes += slot.desc.bytes;
                break;
        }
    }

    return out;
}

ResidencyManager::Slot* ResidencyManager::find(
    std::uint64_t id) noexcept {
    for (auto& slot : slots_) {
        if (slot.occupied && slot.desc.id == id) {
            return &slot;
        }
    }
    return nullptr;
}

const ResidencyManager::Slot* ResidencyManager::find(
    std::uint64_t id) const noexcept {
    for (const auto& slot : slots_) {
        if (slot.occupied && slot.desc.id == id) {
            return &slot;
        }
    }
    return nullptr;
}

} // namespace xziel
