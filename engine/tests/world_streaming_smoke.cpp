#include "xziel/sanctum.hpp"
#include "xziel/world_streaming.hpp"

#include <array>
#include <cassert>
#include <cstddef>

namespace {

const xziel::StreamCellResourceDecision* findDecision(
    const std::array<xziel::StreamCellResourceDecision, 16>& decisions,
    std::size_t count,
    std::uint64_t id) {
    for (std::size_t i = 0U; i < count; ++i) {
        if (decisions[i].resourceId == id) {
            return &decisions[i];
        }
    }
    return nullptr;
}

} // namespace

int main() {
    const auto assetA =
        xziel::streamResourceId(
            "textures/xziel/sanctum/nave.ktx2");
    const auto assetAAgain =
        xziel::streamResourceId(
            "textures/xziel/sanctum/nave.ktx2");
    const auto assetB =
        xziel::streamResourceId(
            "textures/xziel/sanctum/office.ktx2");

    assert(assetA != 0U);
    assert(assetA == assetAAgain);
    assert(assetA != assetB);

    assert(
        xziel::sanctumZoneForAssetName(
            "mat_05_StGilesCripplegateOfficeCorridor02.ktx2") ==
        xziel::SanctumZone::OfficeCorridor);
    assert(
        xziel::sanctumZoneForAssetName(
            "mat_04_StGilesCripplegateOffice02.ktx2") ==
        xziel::SanctumZone::Office);
    assert(
        xziel::sanctumZoneForAssetName(
            "mat_03_StGilesCripplegateExterior04.ktx2") ==
        xziel::SanctumZone::Courtyard);
    assert(
        xziel::sanctumZoneForAssetName(
            "mat_09_StGilesCripplegateTowerTop06.ktx2") ==
        xziel::SanctumZone::TowerTop);

    xziel::StreamCellGraph graph;

    assert(graph.addCell({.id = 1U}));
    assert(graph.addCell({.id = 2U}));
    assert(graph.addCell({.id = 3U}));

    assert(graph.addPortal({
        .id = 100U,
        .cellA = 1U,
        .cellB = 2U,
        .open = false,
        .preloadAcrossClosed = true,
    }));

    assert(graph.addPortal({
        .id = 101U,
        .cellA = 2U,
        .cellB = 3U,
        .open = false,
        .preloadAcrossClosed = true,
    }));

    assert(graph.bindResource({
        .cellId = 1U,
        .resourceId = 10U,
        .kind = xziel::StreamResourceKind::Texture,
        .bytes = 100U,
    }));

    assert(graph.bindResource({
        .cellId = 2U,
        .resourceId = 20U,
        .kind = xziel::StreamResourceKind::Mesh,
        .bytes = 200U,
    }));

    assert(graph.bindResource({
        .cellId = 3U,
        .resourceId = 30U,
        .kind = xziel::StreamResourceKind::AudioBank,
        .bytes = 300U,
    }));

    // Shared gameplay-critical content appears in current and far cells.
    assert(graph.bindResource({
        .cellId = 1U,
        .resourceId = 99U,
        .kind = xziel::StreamResourceKind::Texture,
        .bytes = 50U,
        .pinned = true,
    }));

    assert(graph.bindResource({
        .cellId = 3U,
        .resourceId = 99U,
        .kind = xziel::StreamResourceKind::Texture,
        .bytes = 50U,
        .pinned = true,
    }));

    std::array<xziel::StreamCellResourceDecision, 16>
        decisions{};
    std::size_t written = 0U;

    auto stats = graph.plan(
        {
            .currentCell = 1U,
            .preloadPortalHops = 1U,
            .memoryPressure =
                xziel::MemoryPressure::Normal,
        },
        decisions.data(),
        decisions.size(),
        written);

    assert(written == 4U);
    assert(stats.hotCells == 1U);
    assert(stats.preloadCells == 1U);
    assert(stats.coldCells == 1U);

    const auto* hot =
        findDecision(decisions, written, 10U);
    const auto* preload =
        findDecision(decisions, written, 20U);
    const auto* cold =
        findDecision(decisions, written, 30U);
    const auto* pinned =
        findDecision(decisions, written, 99U);

    assert(hot != nullptr);
    assert(preload != nullptr);
    assert(cold != nullptr);
    assert(pinned != nullptr);

    assert(hot->heat == xziel::StreamCellHeat::Hot);
    assert(hot->desiredResident);
    assert(!hot->evictable);
    assert(hot->desiredMipBias == 0U);

    assert(
        preload->heat ==
        xziel::StreamCellHeat::Preload);
    assert(preload->desiredResident);
    assert(!preload->evictable);
    assert(preload->desiredMipBias == 1U);

    assert(cold->heat == xziel::StreamCellHeat::Cold);
    assert(!cold->desiredResident);
    assert(cold->evictable);

    assert(pinned->pinned);
    assert(pinned->heat == xziel::StreamCellHeat::Hot);
    assert(pinned->desiredResident);
    assert(!pinned->evictable);

    const xziel::StreamCellPlanInput normalInput{
        .currentCell = 1U,
        .preloadPortalHops = 1U,
        .memoryPressure =
            xziel::MemoryPressure::Normal,
    };

    assert(
        graph.cellHeat(
            normalInput,
            1U) ==
        xziel::StreamCellHeat::Hot);
    assert(
        graph.cellHeat(
            normalInput,
            2U) ==
        xziel::StreamCellHeat::Preload);
    assert(
        graph.cellHeat(
            normalInput,
            3U) ==
        xziel::StreamCellHeat::Cold);

    // Opening the first portal makes cell 2 reachable. The next closed door
    // may preload exactly cell 3, which proves the one-boundary rule.
    assert(graph.setPortalOpen(100U, true));

    stats = graph.plan(
        {
            .currentCell = 1U,
            .preloadPortalHops = 1U,
            .memoryPressure =
                xziel::MemoryPressure::Normal,
        },
        decisions.data(),
        decisions.size(),
        written);

    assert(stats.hotCells == 1U);
    assert(stats.preloadCells == 2U);
    assert(stats.coldCells == 0U);

    // Critical pressure disables speculative closed-door preloads and open
    // traversal beyond the current cell.
    stats = graph.plan(
        {
            .currentCell = 1U,
            .preloadPortalHops = 2U,
            .memoryPressure =
                xziel::MemoryPressure::Critical,
        },
        decisions.data(),
        decisions.size(),
        written);

    assert(stats.hotCells == 1U);
    assert(stats.preloadCells == 0U);
    assert(stats.coldCells == 2U);

    const xziel::StreamCellPlanInput criticalInput{
        .currentCell = 1U,
        .preloadPortalHops = 2U,
        .memoryPressure =
            xziel::MemoryPressure::Critical,
    };

    assert(
        graph.cellHeat(
            criticalInput,
            1U) ==
        xziel::StreamCellHeat::Hot);
    assert(
        graph.cellHeat(
            criticalInput,
            2U) ==
        xziel::StreamCellHeat::Cold);

    const auto* coldUnderPressure =
        findDecision(decisions, written, 20U);

    assert(coldUnderPressure != nullptr);
    assert(coldUnderPressure->evictable);
    assert(
        coldUnderPressure->desiredMipBias ==
        3U);

    xziel::StreamCellGraph sanctum;
    assert(
        xziel::configureSanctumStreamingGraph(
            sanctum));

    assert(sanctum.cellCount() == 10U);
    assert(sanctum.portalCount() == 9U);
    assert(sanctum.bindingCount() == 0U);

    assert(sanctum.setPortalOpen(2000U, true));
    assert(sanctum.setPortalOpen(2000U, false));
    assert(!sanctum.setPortalOpen(1001U, true));

    return 0;
}
