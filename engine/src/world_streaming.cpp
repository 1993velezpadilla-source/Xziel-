#include "xziel/world_streaming.hpp"

#include <algorithm>
#include <array>
#include <limits>

namespace xziel {

namespace {

[[nodiscard]] int heatRank(
    StreamCellHeat heat) noexcept {
    switch (heat) {
        case StreamCellHeat::Cold: return 0;
        case StreamCellHeat::Preload: return 1;
        case StreamCellHeat::Hot: return 2;
    }
    return 0;
}

[[nodiscard]] std::uint8_t preloadMipBias(
    MemoryPressure pressure) noexcept {
    switch (pressure) {
        case MemoryPressure::Normal:
            return 1U;
        case MemoryPressure::Elevated:
            return 2U;
        case MemoryPressure::Critical:
            return 3U;
    }
    return 2U;
}

} // namespace

void StreamCellGraph::reset() noexcept {
    cells_ = {};
    portals_ = {};
    bindings_ = {};
    cellCount_ = 0U;
    portalCount_ = 0U;
    bindingCount_ = 0U;
}

bool StreamCellGraph::addCell(
    const StreamCellDefinition& cell) noexcept {
    if (cell.id == 0U ||
        cellCount_ >= cells_.size() ||
        cellIndex(cell.id) >= 0) {
        return false;
    }

    cells_[cellCount_++] = cell;
    return true;
}

bool StreamCellGraph::addPortal(
    const StreamPortalDefinition& portal) noexcept {
    if (portal.id == 0U ||
        portal.cellA == 0U ||
        portal.cellB == 0U ||
        portal.cellA == portal.cellB ||
        portalCount_ >= portals_.size() ||
        portalIndex(portal.id) >= 0 ||
        cellIndex(portal.cellA) < 0 ||
        cellIndex(portal.cellB) < 0) {
        return false;
    }

    portals_[portalCount_++] = portal;
    return true;
}

bool StreamCellGraph::setPortalOpen(
    std::uint32_t portalId,
    bool open) noexcept {
    const int index =
        portalIndex(portalId);

    if (index < 0) {
        return false;
    }

    portals_[
        static_cast<std::size_t>(index)].open =
        open;
    return true;
}

bool StreamCellGraph::bindResource(
    const StreamCellResourceBinding& binding) noexcept {
    if (binding.cellId == 0U ||
        binding.resourceId == 0U ||
        binding.bytes == 0U ||
        bindingCount_ >= bindings_.size() ||
        cellIndex(binding.cellId) < 0) {
        return false;
    }

    bindings_[bindingCount_++] =
        binding;
    return true;
}

StreamCellPlanStats StreamCellGraph::plan(
    const StreamCellPlanInput& input,
    StreamCellResourceDecision* destination,
    std::size_t destinationCapacity,
    std::size_t& written) const noexcept {
    written = 0U;
    StreamCellPlanStats stats{};

    if (destination == nullptr ||
        destinationCapacity == 0U ||
        cellCount_ == 0U) {
        return stats;
    }

    const int start =
        cellIndex(input.currentCell);

    if (start < 0) {
        return stats;
    }

    constexpr std::uint8_t kUnreached =
        std::numeric_limits<std::uint8_t>::max();

    std::array<std::uint8_t, kMaxStreamCells>
        distance{};
    distance.fill(kUnreached);

    std::array<std::size_t, kMaxStreamCells>
        queue{};

    std::size_t queueRead = 0U;
    std::size_t queueWrite = 0U;

    distance[static_cast<std::size_t>(start)] = 0U;
    queue[queueWrite++] =
        static_cast<std::size_t>(start);

    const std::uint8_t maxHops =
        input.memoryPressure ==
            MemoryPressure::Critical
        ? 0U
        : input.preloadPortalHops;

    while (queueRead < queueWrite) {
        const std::size_t currentIndex =
            queue[queueRead++];

        const std::uint8_t currentDistance =
            distance[currentIndex];

        if (currentDistance >= maxHops) {
            continue;
        }

        const std::uint32_t currentId =
            cells_[currentIndex].id;

        for (std::size_t p = 0U;
             p < portalCount_;
             ++p) {
            const auto& portal =
                portals_[p];

            if (!portal.open) {
                continue;
            }

            std::uint32_t nextId = 0U;

            if (portal.cellA == currentId) {
                nextId = portal.cellB;
            } else if (
                portal.cellB == currentId) {
                nextId = portal.cellA;
            } else {
                continue;
            }

            const int nextIndex =
                cellIndex(nextId);

            if (nextIndex < 0) {
                continue;
            }

            const auto next =
                static_cast<std::size_t>(
                    nextIndex);

            if (distance[next] !=
                kUnreached) {
                continue;
            }

            distance[next] =
                static_cast<std::uint8_t>(
                    currentDistance + 1U);

            if (queueWrite < queue.size()) {
                queue[queueWrite++] =
                    next;
            }
        }
    }

    std::array<StreamCellHeat, kMaxStreamCells>
        cellHeat{};

    for (std::size_t i = 0U;
         i < cellCount_;
         ++i) {
        if (distance[i] == 0U) {
            cellHeat[i] =
                StreamCellHeat::Hot;
            ++stats.hotCells;
        } else if (
            distance[i] != kUnreached) {
            cellHeat[i] =
                StreamCellHeat::Preload;
            ++stats.preloadCells;
        } else {
            cellHeat[i] =
                StreamCellHeat::Cold;
        }
    }

    if (input.memoryPressure !=
        MemoryPressure::Critical) {
        for (std::size_t p = 0U;
             p < portalCount_;
             ++p) {
            const auto& portal =
                portals_[p];

            if (portal.open ||
                !portal.preloadAcrossClosed) {
                continue;
            }

            const int a =
                cellIndex(portal.cellA);
            const int b =
                cellIndex(portal.cellB);

            if (a < 0 || b < 0) {
                continue;
            }

            const auto ai =
                static_cast<std::size_t>(a);
            const auto bi =
                static_cast<std::size_t>(b);

            const bool aWarm =
                cellHeat[ai] !=
                    StreamCellHeat::Cold;
            const bool bWarm =
                cellHeat[bi] !=
                    StreamCellHeat::Cold;

            if (aWarm && !bWarm) {
                cellHeat[bi] =
                    StreamCellHeat::Preload;
                ++stats.preloadCells;
            } else if (
                bWarm && !aWarm) {
                cellHeat[ai] =
                    StreamCellHeat::Preload;
                ++stats.preloadCells;
            }
        }
    }

    stats.coldCells =
        static_cast<std::uint32_t>(
            cellCount_) -
        stats.hotCells -
        stats.preloadCells;

    for (std::size_t i = 0U;
         i < bindingCount_;
         ++i) {
        const auto& binding =
            bindings_[i];

        const int owner =
            cellIndex(binding.cellId);

        if (owner < 0) {
            continue;
        }

        const auto heat =
            cellHeat[
                static_cast<std::size_t>(
                    owner)];

        std::size_t existing =
            destinationCapacity;

        for (std::size_t j = 0U;
             j < written;
             ++j) {
            if (destination[j].resourceId ==
                binding.resourceId) {
                existing = j;
                break;
            }
        }

        if (existing ==
            destinationCapacity) {
            if (written >=
                destinationCapacity) {
                continue;
            }

            existing = written++;
            destination[existing] = {
                .resourceId =
                    binding.resourceId,
                .kind =
                    binding.kind,
                .bytes =
                    binding.bytes,
                .heat = heat,
                .desiredMipBias = 0U,
                .priority = 0U,
                .desiredResident = false,
                .evictable = false,
                .pinned =
                    binding.pinned,
            };
        } else {
            auto& decision =
                destination[existing];

            if (heatRank(heat) >
                heatRank(decision.heat)) {
                decision.heat = heat;
            }

            decision.bytes =
                std::max(
                    decision.bytes,
                    binding.bytes);
            decision.pinned =
                decision.pinned ||
                binding.pinned;
        }
    }

    for (std::size_t i = 0U;
         i < written;
         ++i) {
        auto& decision =
            destination[i];

        if (decision.pinned) {
            decision.heat =
                StreamCellHeat::Hot;
        }

        switch (decision.heat) {
            case StreamCellHeat::Hot:
                decision.priority = 255U;
                decision.desiredMipBias = 0U;
                decision.desiredResident = true;
                decision.evictable = false;
                ++stats.hotResources;
                break;

            case StreamCellHeat::Preload:
                decision.priority =
                    input.memoryPressure ==
                        MemoryPressure::Elevated
                    ? 112U
                    : 176U;
                decision.desiredMipBias =
                    preloadMipBias(
                        input.memoryPressure);
                decision.desiredResident =
                    input.memoryPressure !=
                        MemoryPressure::Critical;
                decision.evictable =
                    !decision.desiredResident &&
                    !decision.pinned;
                ++stats.preloadResources;
                break;

            case StreamCellHeat::Cold:
                decision.priority = 16U;
                decision.desiredMipBias =
                    input.memoryPressure ==
                        MemoryPressure::Normal
                    ? 2U
                    : 3U;
                decision.desiredResident =
                    decision.pinned;
                decision.evictable =
                    !decision.pinned;
                ++stats.coldResources;
                break;
        }

        if (decision.desiredResident) {
            stats.desiredResidentBytes +=
                decision.bytes;
        }

        if (decision.evictable) {
            stats.evictableBytes +=
                decision.bytes;
        }
    }

    return stats;
}

std::size_t StreamCellGraph::cellCount() const noexcept {
    return cellCount_;
}

std::size_t StreamCellGraph::portalCount() const noexcept {
    return portalCount_;
}

std::size_t StreamCellGraph::bindingCount() const noexcept {
    return bindingCount_;
}

int StreamCellGraph::cellIndex(
    std::uint32_t id) const noexcept {
    for (std::size_t i = 0U;
         i < cellCount_;
         ++i) {
        if (cells_[i].id == id) {
            return static_cast<int>(i);
        }
    }

    return -1;
}

int StreamCellGraph::portalIndex(
    std::uint32_t id) const noexcept {
    for (std::size_t i = 0U;
         i < portalCount_;
         ++i) {
        if (portals_[i].id == id) {
            return static_cast<int>(i);
        }
    }

    return -1;
}

} // namespace xziel
