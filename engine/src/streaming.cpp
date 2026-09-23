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


TextureMipResidencyManager::TextureMipResidencyManager(
    std::uint32_t maxTextures)
    : slots_(
          std::max<std::uint32_t>(
              1U,
              maxTextures)) {}

void TextureMipResidencyManager::reset() noexcept {
    for (auto& slot : slots_) {
        slot = {};
    }
}

bool TextureMipResidencyManager::valid(
    const TextureMipChainDesc& desc) noexcept {
    if (desc.id == 0U ||
        desc.mipCount == 0U ||
        desc.mipCount >
            kMaxStreamedTextureMips ||
        desc.residentBaseMip >=
            desc.mipCount ||
        desc.requestedBaseMip >=
            desc.mipCount) {
        return false;
    }

    for (std::uint32_t mip = 0U;
         mip < desc.mipCount;
         ++mip) {
        if (desc.mipBytes[mip] == 0U) {
            return false;
        }
    }

    return true;
}

std::uint64_t TextureMipResidencyManager::bytesFromMip(
    const TextureMipChainDesc& desc,
    std::uint32_t baseMip) noexcept {
    if (baseMip >= desc.mipCount) {
        return 0U;
    }

    std::uint64_t total = 0U;

    for (std::uint32_t mip = baseMip;
         mip < desc.mipCount;
         ++mip) {
        const std::uint64_t value =
            desc.mipBytes[mip];

        if (value >
            std::numeric_limits<std::uint64_t>::max() -
                total) {
            return
                std::numeric_limits<std::uint64_t>::max();
        }

        total += value;
    }

    return total;
}

bool TextureMipResidencyManager::registerTexture(
    const TextureMipChainDesc& desc,
    std::uint64_t frameIndex) noexcept {
    if (!valid(desc)) {
        return false;
    }

    if (auto* existing = find(desc.id)) {
        existing->desc = desc;
        existing->lastTouchedFrame =
            frameIndex;
        return true;
    }

    for (auto& slot : slots_) {
        if (!slot.occupied) {
            slot.occupied = true;
            slot.desc = desc;
            slot.lastTouchedFrame =
                frameIndex;
            return true;
        }
    }

    return false;
}

void TextureMipResidencyManager::touch(
    std::uint64_t id,
    std::uint32_t requestedBaseMip,
    std::uint64_t frameIndex) noexcept {
    if (auto* slot = find(id)) {
        slot->desc.requestedBaseMip =
            std::min(
                requestedBaseMip,
                slot->desc.mipCount - 1U);
        slot->lastTouchedFrame =
            frameIndex;
    }
}

void TextureMipResidencyManager::setPinned(
    std::uint64_t id,
    bool pinned) noexcept {
    if (auto* slot = find(id)) {
        slot->desc.pinned = pinned;
    }
}

bool TextureMipResidencyManager::applyResidentBaseMip(
    std::uint64_t id,
    std::uint32_t baseMip,
    std::uint64_t frameIndex) noexcept {
    auto* slot = find(id);

    if (slot == nullptr ||
        baseMip >= slot->desc.mipCount) {
        return false;
    }

    slot->desc.residentBaseMip =
        baseMip;
    slot->lastTouchedFrame =
        frameIndex;
    return true;
}

std::size_t TextureMipResidencyManager::planDemotions(
    std::uint64_t targetBytesToFree,
    std::uint64_t currentFrame,
    std::uint64_t minimumUnusedFrames,
    TextureMipChange* destination,
    std::size_t destinationCapacity) const noexcept {
    if (targetBytesToFree == 0U ||
        destination == nullptr ||
        destinationCapacity == 0U) {
        return 0U;
    }

    std::uint64_t plannedBytes = 0U;
    std::size_t written = 0U;

    while (
        written < destinationCapacity &&
        plannedBytes < targetBytesToFree) {
        const Slot* best = nullptr;
        std::uint64_t bestAge = 0U;
        std::uint64_t bestResidentBytes = 0U;

        for (const auto& slot : slots_) {
            if (!slot.occupied ||
                slot.desc.pinned ||
                slot.desc.residentBaseMip + 1U >=
                    slot.desc.mipCount) {
                continue;
            }

            bool alreadyPlanned = false;
            for (std::size_t i = 0U;
                 i < written;
                 ++i) {
                if (destination[i].id ==
                    slot.desc.id) {
                    alreadyPlanned = true;
                    break;
                }
            }

            if (alreadyPlanned) {
                continue;
            }

            const std::uint64_t age =
                currentFrame >=
                        slot.lastTouchedFrame
                ? currentFrame -
                    slot.lastTouchedFrame
                : 0U;

            if (age < minimumUnusedFrames) {
                continue;
            }

            const std::uint64_t residentBytes =
                bytesFromMip(
                    slot.desc,
                    slot.desc.residentBaseMip);

            if (best == nullptr ||
                age > bestAge ||
                (age == bestAge &&
                 residentBytes >
                     bestResidentBytes)) {
                best = &slot;
                bestAge = age;
                bestResidentBytes =
                    residentBytes;
            }
        }

        if (best == nullptr) {
            break;
        }

        std::uint32_t newBaseMip =
            best->desc.residentBaseMip;
        std::uint64_t freed = 0U;

        while (
            newBaseMip + 1U <
                best->desc.mipCount &&
            plannedBytes + freed <
                targetBytesToFree) {
            freed +=
                best->desc.mipBytes[
                    newBaseMip];
            ++newBaseMip;
        }

        if (freed == 0U) {
            break;
        }

        destination[written++] = {
            .id = best->desc.id,
            .oldBaseMip =
                best->desc.residentBaseMip,
            .newBaseMip = newBaseMip,
            .bytesChanged = freed,
        };

        plannedBytes += freed;
    }

    return written;
}

std::size_t TextureMipResidencyManager::planPromotions(
    std::uint64_t availableBytes,
    std::uint64_t currentFrame,
    std::uint64_t maximumUnusedFrames,
    TextureMipChange* destination,
    std::size_t destinationCapacity) const noexcept {
    if (availableBytes == 0U ||
        destination == nullptr ||
        destinationCapacity == 0U) {
        return 0U;
    }

    std::uint64_t plannedBytes = 0U;
    std::size_t written = 0U;

    while (
        written < destinationCapacity) {
        const Slot* best = nullptr;
        std::uint64_t bestAge =
            std::numeric_limits<std::uint64_t>::max();

        for (const auto& slot : slots_) {
            if (!slot.occupied ||
                slot.desc.residentBaseMip == 0U ||
                slot.desc.residentBaseMip <=
                    slot.desc.requestedBaseMip) {
                continue;
            }

            bool alreadyPlanned = false;
            for (std::size_t i = 0U;
                 i < written;
                 ++i) {
                if (destination[i].id ==
                    slot.desc.id) {
                    alreadyPlanned = true;
                    break;
                }
            }

            if (alreadyPlanned) {
                continue;
            }

            const std::uint64_t age =
                currentFrame >=
                        slot.lastTouchedFrame
                ? currentFrame -
                    slot.lastTouchedFrame
                : 0U;

            if (age > maximumUnusedFrames) {
                continue;
            }

            const std::uint32_t nextMip =
                slot.desc.residentBaseMip -
                1U;
            const std::uint64_t cost =
                slot.desc.mipBytes[
                    nextMip];

            if (cost >
                availableBytes -
                    plannedBytes) {
                continue;
            }

            if (best == nullptr ||
                age < bestAge ||
                (age == bestAge &&
                 cost <
                     best->desc.mipBytes[
                         best->desc.residentBaseMip -
                         1U])) {
                best = &slot;
                bestAge = age;
            }
        }

        if (best == nullptr) {
            break;
        }

        const std::uint32_t newBaseMip =
            best->desc.residentBaseMip -
            1U;
        const std::uint64_t cost =
            best->desc.mipBytes[
                newBaseMip];

        destination[written++] = {
            .id = best->desc.id,
            .oldBaseMip =
                best->desc.residentBaseMip,
            .newBaseMip = newBaseMip,
            .bytesChanged = cost,
        };

        plannedBytes += cost;

        if (plannedBytes >=
            availableBytes) {
            break;
        }
    }

    return written;
}

TextureMipResidencyStats
TextureMipResidencyManager::stats() const noexcept {
    TextureMipResidencyStats out{};

    for (const auto& slot : slots_) {
        if (!slot.occupied) {
            continue;
        }

        ++out.textureCount;

        out.residentBytes +=
            bytesFromMip(
                slot.desc,
                slot.desc.residentBaseMip);

        out.requestedBytes +=
            bytesFromMip(
                slot.desc,
                slot.desc.requestedBaseMip);

        if (slot.desc.residentBaseMip >
            slot.desc.requestedBaseMip) {
            ++out.degradedTextureCount;
        }
    }

    return out;
}

TextureMipResidencyManager::Slot*
TextureMipResidencyManager::find(
    std::uint64_t id) noexcept {
    for (auto& slot : slots_) {
        if (slot.occupied &&
            slot.desc.id == id) {
            return &slot;
        }
    }

    return nullptr;
}

const TextureMipResidencyManager::Slot*
TextureMipResidencyManager::find(
    std::uint64_t id) const noexcept {
    for (const auto& slot : slots_) {
        if (slot.occupied &&
            slot.desc.id == id) {
            return &slot;
        }
    }

    return nullptr;
}

} // namespace xziel
