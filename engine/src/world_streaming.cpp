#include "xziel/world_streaming.hpp"

#include <algorithm>
#include <array>
#include <limits>

namespace xziel {

std::uint64_t streamResourceId(
    std::string_view assetKey) noexcept {
    // FNV-1a 64-bit: deterministic across cooker/runtime processes and
    // platforms, unlike std::hash whose representation is implementation
    // defined. Zero is reserved as "invalid" by the residency systems.
    std::uint64_t hash =
        14695981039346656037ULL;

    for (const unsigned char value :
         assetKey) {
        hash ^= static_cast<std::uint64_t>(
            value);
        hash *= 1099511628211ULL;
    }

    return hash != 0U
        ? hash
        : 1U;
}

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
    portalCellAIndices_.fill(
        std::numeric_limits<std::uint8_t>::max());
    portalCellBIndices_.fill(
        std::numeric_limits<std::uint8_t>::max());
    bindings_ = {};
    bindingCellIndices_.fill(
        std::numeric_limits<std::uint8_t>::max());
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
        portalIndex(portal.id) >= 0) {
        return false;
    }

    const int cellAIndex =
        cellIndex(portal.cellA);
    const int cellBIndex =
        cellIndex(portal.cellB);

    if (cellAIndex < 0 ||
        cellBIndex < 0) {
        return false;
    }

    portals_[portalCount_] = portal;
    portalCellAIndices_[portalCount_] =
        static_cast<std::uint8_t>(
            cellAIndex);
    portalCellBIndices_[portalCount_] =
        static_cast<std::uint8_t>(
            cellBIndex);
    ++portalCount_;
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

bool StreamCellGraph::portalOpen(
    std::uint32_t portalId,
    bool& open) const noexcept {
    const int index =
        portalIndex(portalId);

    if (index < 0) {
        return false;
    }

    open =
        portals_[
            static_cast<std::size_t>(index)].
                open;

    return true;
}

bool StreamCellGraph::bindResource(
    const StreamCellResourceBinding& binding) noexcept {
    if (binding.cellId == 0U ||
        binding.resourceId == 0U ||
        binding.bytes == 0U ||
        bindingCount_ >= bindings_.size()) {
        return false;
    }

    const int ownerIndex =
        cellIndex(binding.cellId);

    if (ownerIndex < 0) {
        return false;
    }

    bindings_[bindingCount_] =
        binding;
    bindingCellIndices_[bindingCount_] =
        static_cast<std::uint8_t>(
            ownerIndex);
    ++bindingCount_;
    return true;
}

StreamCellPlanStats StreamCellGraph::plan(
    const StreamCellPlanInput& input,
    StreamCellResourceDecision* destination,
    std::size_t destinationCapacity,
    std::size_t& written,
    StreamCellPlanCellState* cellDestination,
    std::size_t cellDestinationCapacity,
    std::size_t* cellWritten) const noexcept {
    written = 0U;

    if (cellWritten != nullptr) {
        *cellWritten = 0U;
    }

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

            std::size_t next =
                kMaxStreamCells;

            if (portal.cellA == currentId) {
                next =
                    portalCellBIndices_[p];
            } else if (
                portal.cellB == currentId) {
                next =
                    portalCellAIndices_[p];
            } else {
                continue;
            }

            if (next >= cellCount_) {
                continue;
            }

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
            distance[i] != kUnreached &&
            distance[i] <= maxHops) {
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

            const auto ai =
                static_cast<std::size_t>(
                    portalCellAIndices_[p]);
            const auto bi =
                static_cast<std::size_t>(
                    portalCellBIndices_[p]);

            if (ai >= cellCount_ ||
                bi >= cellCount_) {
                continue;
            }

            // Closed-door preloading is exactly one boundary deep.
            // Only cells reached through the open graph may seed it; a cell
            // that became warm only because of another closed door may not
            // cascade preload through the rest of the map.
            const bool aReachable =
                distance[ai] != kUnreached &&
                distance[ai] <= maxHops;
            const bool bReachable =
                distance[bi] != kUnreached &&
                distance[bi] <= maxHops;

            if (aReachable &&
                cellHeat[bi] ==
                    StreamCellHeat::Cold) {
                cellHeat[bi] =
                    StreamCellHeat::Preload;
                ++stats.preloadCells;
            } else if (
                bReachable &&
                cellHeat[ai] ==
                    StreamCellHeat::Cold) {
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

    if (cellDestination != nullptr &&
        cellDestinationCapacity > 0U) {
        const std::size_t cellOutputCount =
            std::min(
                cellCount_,
                cellDestinationCapacity);

        for (std::size_t i = 0U;
             i < cellOutputCount;
             ++i) {
            cellDestination[i] = {
                .cellId = cells_[i].id,
                .heat = cellHeat[i],
                .reachableThroughOpenPortals =
                    distance[i] != kUnreached,
            };
        }

        if (cellWritten != nullptr) {
            *cellWritten =
                cellOutputCount;
        }
    }

    for (std::size_t i = 0U;
         i < bindingCount_;
         ++i) {
        const auto& binding =
            bindings_[i];

        const auto owner =
            static_cast<std::size_t>(
                bindingCellIndices_[i]);

        if (owner >= cellCount_) {
            continue;
        }

        const auto heat =
            cellHeat[owner];

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

StreamCellHeat StreamCellGraph::cellHeat(
    const StreamCellPlanInput& input,
    std::uint32_t cellId) const noexcept {
    const int start =
        cellIndex(input.currentCell);
    const int target =
        cellIndex(cellId);

    if (start < 0 || target < 0) {
        return StreamCellHeat::Cold;
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

            std::size_t next =
                kMaxStreamCells;

            if (portal.cellA == currentId) {
                next =
                    portalCellBIndices_[p];
            } else if (
                portal.cellB == currentId) {
                next =
                    portalCellAIndices_[p];
            } else {
                continue;
            }

            if (next >= cellCount_) {
                continue;
            }

            if (distance[next] !=
                kUnreached) {
                continue;
            }

            distance[next] =
                static_cast<std::uint8_t>(
                    currentDistance + 1U);

            if (queueWrite < queue.size()) {
                queue[queueWrite++] = next;
            }
        }
    }

    const auto targetIndex =
        static_cast<std::size_t>(target);

    if (distance[targetIndex] == 0U) {
        return StreamCellHeat::Hot;
    }

    if (distance[targetIndex] != kUnreached) {
        return StreamCellHeat::Preload;
    }

    if (input.memoryPressure ==
        MemoryPressure::Critical) {
        return StreamCellHeat::Cold;
    }

    for (std::size_t p = 0U;
         p < portalCount_;
         ++p) {
        const auto& portal =
            portals_[p];

        if (portal.open ||
            !portal.preloadAcrossClosed) {
            continue;
        }

        std::size_t otherIndex =
            kMaxStreamCells;

        if (portal.cellA == cellId) {
            otherIndex =
                portalCellBIndices_[p];
        } else if (
            portal.cellB == cellId) {
            otherIndex =
                portalCellAIndices_[p];
        } else {
            continue;
        }

        if (otherIndex < cellCount_ &&
            distance[otherIndex] !=
                kUnreached) {
            return StreamCellHeat::Preload;
        }
    }

    return StreamCellHeat::Cold;
}

bool StreamCellGraph::cellReachableThroughOpenPortals(
    std::uint32_t startCell,
    std::uint32_t targetCell) const noexcept {
    const int start =
        cellIndex(startCell);
    const int target =
        cellIndex(targetCell);

    if (start < 0 || target < 0) {
        return false;
    }

    if (start == target) {
        return true;
    }

    std::array<bool, kMaxStreamCells>
        visited{};
    std::array<std::size_t, kMaxStreamCells>
        queue{};

    std::size_t read = 0U;
    std::size_t write = 0U;

    visited[
        static_cast<std::size_t>(start)] =
        true;
    queue[write++] =
        static_cast<std::size_t>(start);

    while (read < write) {
        const std::size_t currentIndex =
            queue[read++];
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

            std::size_t nextIndex =
                kMaxStreamCells;

            if (portal.cellA == currentId) {
                nextIndex =
                    portalCellBIndices_[p];
            } else if (
                portal.cellB == currentId) {
                nextIndex =
                    portalCellAIndices_[p];
            } else {
                continue;
            }

            if (nextIndex >= cellCount_ ||
                visited[nextIndex]) {
                continue;
            }

            if (nextIndex ==
                static_cast<std::size_t>(
                    target)) {
                return true;
            }

            visited[nextIndex] = true;

            if (write < queue.size()) {
                queue[write++] =
                    nextIndex;
            }
        }
    }

    return false;
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
