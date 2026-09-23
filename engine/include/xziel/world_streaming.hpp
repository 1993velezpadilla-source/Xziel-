#pragma once

#include "xziel/runtime_policy.hpp"
#include "xziel/streaming.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

namespace xziel {

[[nodiscard]] std::uint64_t streamResourceId(
    std::string_view assetKey) noexcept;

inline constexpr std::size_t kMaxStreamCells = 64U;
inline constexpr std::size_t kMaxStreamPortals = 128U;
inline constexpr std::size_t kMaxStreamBindings = 512U;

enum class StreamCellHeat : std::uint8_t {
    Cold,
    Preload,
    Hot,
};

struct StreamCellDefinition {
    std::uint32_t id = 0U;
};

struct StreamPortalDefinition {
    std::uint32_t id = 0U;
    std::uint32_t cellA = 0U;
    std::uint32_t cellB = 0U;
    bool open = false;
    bool preloadAcrossClosed = true;
};

struct StreamCellResourceBinding {
    std::uint32_t cellId = 0U;
    std::uint64_t resourceId = 0U;
    StreamResourceKind kind =
        StreamResourceKind::Texture;
    std::uint64_t bytes = 0U;
    bool pinned = false;
};

struct StreamCellPlanInput {
    std::uint32_t currentCell = 0U;
    std::uint8_t preloadPortalHops = 1U;
    MemoryPressure memoryPressure =
        MemoryPressure::Normal;
};

struct StreamCellResourceDecision {
    std::uint64_t resourceId = 0U;
    StreamResourceKind kind =
        StreamResourceKind::Texture;
    std::uint64_t bytes = 0U;

    StreamCellHeat heat =
        StreamCellHeat::Cold;

    // Textures can translate this into a resident base-mip preference.
    // Other resource kinds may treat it as a generic quality bias.
    std::uint8_t desiredMipBias = 0U;

    std::uint8_t priority = 0U;
    bool desiredResident = false;
    bool evictable = false;
    bool pinned = false;
};

struct StreamCellPlanStats {
    std::uint32_t hotCells = 0U;
    std::uint32_t preloadCells = 0U;
    std::uint32_t coldCells = 0U;

    std::uint32_t hotResources = 0U;
    std::uint32_t preloadResources = 0U;
    std::uint32_t coldResources = 0U;

    std::uint64_t desiredResidentBytes = 0U;
    std::uint64_t evictableBytes = 0U;
};

class StreamCellGraph final {
public:
    void reset() noexcept;

    [[nodiscard]] bool addCell(
        const StreamCellDefinition& cell) noexcept;

    [[nodiscard]] bool addPortal(
        const StreamPortalDefinition& portal) noexcept;

    [[nodiscard]] bool setPortalOpen(
        std::uint32_t portalId,
        bool open) noexcept;

    [[nodiscard]] bool bindResource(
        const StreamCellResourceBinding& binding) noexcept;

    [[nodiscard]] StreamCellPlanStats plan(
        const StreamCellPlanInput& input,
        StreamCellResourceDecision* destination,
        std::size_t destinationCapacity,
        std::size_t& written) const noexcept;

    [[nodiscard]] StreamCellHeat cellHeat(
        const StreamCellPlanInput& input,
        std::uint32_t cellId) const noexcept;

    [[nodiscard]] std::size_t cellCount() const noexcept;
    [[nodiscard]] std::size_t portalCount() const noexcept;
    [[nodiscard]] std::size_t bindingCount() const noexcept;

private:
    [[nodiscard]] int cellIndex(
        std::uint32_t id) const noexcept;

    [[nodiscard]] int portalIndex(
        std::uint32_t id) const noexcept;

    std::array<StreamCellDefinition, kMaxStreamCells>
        cells_{};
    std::array<StreamPortalDefinition, kMaxStreamPortals>
        portals_{};
    std::array<StreamCellResourceBinding, kMaxStreamBindings>
        bindings_{};

    std::size_t cellCount_ = 0U;
    std::size_t portalCount_ = 0U;
    std::size_t bindingCount_ = 0U;
};

} // namespace xziel
