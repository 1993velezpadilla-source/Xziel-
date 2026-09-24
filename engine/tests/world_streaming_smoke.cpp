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

const xziel::StreamCellPlanCellState* findCellState(
    const std::array<xziel::StreamCellPlanCellState, 16>& states,
    std::size_t count,
    std::uint32_t id) {
    for (std::size_t i = 0U; i < count; ++i) {
        if (states[i].cellId == id) {
            return &states[i];
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
    std::array<xziel::StreamCellPlanCellState, 16>
        cellStates{};
    std::size_t written = 0U;
    std::size_t cellWritten = 0U;

    auto stats = graph.plan(
        {
            .currentCell = 1U,
            .preloadPortalHops = 1U,
            .memoryPressure =
                xziel::MemoryPressure::Normal,
        },
        decisions.data(),
        decisions.size(),
        written,
        cellStates.data(),
        cellStates.size(),
        &cellWritten);

    assert(written == 4U);
    assert(cellWritten == 3U);

    const auto* cell1 =
        findCellState(
            cellStates,
            cellWritten,
            1U);
    const auto* cell2 =
        findCellState(
            cellStates,
            cellWritten,
            2U);
    const auto* cell3 =
        findCellState(
            cellStates,
            cellWritten,
            3U);

    assert(cell1 != nullptr);
    assert(cell2 != nullptr);
    assert(cell3 != nullptr);
    assert(cell1->heat == xziel::StreamCellHeat::Hot);
    assert(cell1->reachableThroughOpenPortals);
    assert(cell2->heat == xziel::StreamCellHeat::Preload);
    assert(!cell2->reachableThroughOpenPortals);
    assert(cell3->heat == xziel::StreamCellHeat::Cold);
    assert(!cell3->reachableThroughOpenPortals);
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

    assert(
        graph.cellReachableThroughOpenPortals(
            1U,
            1U));
    assert(
        !graph.cellReachableThroughOpenPortals(
            1U,
            2U));
    assert(
        !graph.cellReachableThroughOpenPortals(
            1U,
            3U));

    bool portalIsOpen = true;
    assert(graph.portalOpen(100U, portalIsOpen));
    assert(!portalIsOpen);
    assert(!graph.portalOpen(999U, portalIsOpen));

    // Opening the first portal makes cell 2 reachable. The next closed door
    // may preload exactly cell 3, which proves the one-boundary rule.
    assert(graph.setPortalOpen(100U, true));
    assert(graph.portalOpen(100U, portalIsOpen));
    assert(portalIsOpen);

    stats = graph.plan(
        {
            .currentCell = 1U,
            .preloadPortalHops = 1U,
            .memoryPressure =
                xziel::MemoryPressure::Normal,
        },
        decisions.data(),
        decisions.size(),
        written,
        cellStates.data(),
        cellStates.size(),
        &cellWritten);

    cell2 =
        findCellState(
            cellStates,
            cellWritten,
            2U);
    cell3 =
        findCellState(
            cellStates,
            cellWritten,
            3U);

    assert(cell2 != nullptr);
    assert(cell3 != nullptr);
    assert(cell2->reachableThroughOpenPortals);
    assert(cell2->heat == xziel::StreamCellHeat::Preload);
    assert(!cell3->reachableThroughOpenPortals);
    assert(cell3->heat == xziel::StreamCellHeat::Preload);

    assert(stats.hotCells == 1U);
    assert(stats.preloadCells == 2U);
    assert(stats.coldCells == 0U);

    assert(
        graph.cellReachableThroughOpenPortals(
            1U,
            2U));
    assert(
        !graph.cellReachableThroughOpenPortals(
            1U,
            3U));

    assert(graph.setPortalOpen(101U, true));
    assert(
        graph.cellReachableThroughOpenPortals(
            1U,
            3U));
    assert(graph.setPortalOpen(101U, false));

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
        written,
        cellStates.data(),
        cellStates.size(),
        &cellWritten);

    cell2 =
        findCellState(
            cellStates,
            cellWritten,
            2U);

    assert(cell2 != nullptr);
    assert(cell2->reachableThroughOpenPortals);
    assert(cell2->heat == xziel::StreamCellHeat::Cold);

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

    // Sparse/non-ordinal IDs prove that cached topology slots are resolved
    // from IDs during graph construction rather than treating IDs as indices.
    xziel::StreamCellGraph sparseGraph;
    assert(sparseGraph.addCell({.id = 10U}));
    assert(sparseGraph.addCell({.id = 4000000000U}));
    assert(sparseGraph.addPortal({
        .id = 77U,
        .cellA = 10U,
        .cellB = 4000000000U,
        .open = true,
        .preloadAcrossClosed = true,
    }));
    assert(sparseGraph.bindResource({
        .cellId = 4000000000U,
        .resourceId = 123456U,
        .kind = xziel::StreamResourceKind::Mesh,
        .bytes = 4096U,
    }));

    std::uint32_t sparseSlot = 99U;
    assert(sparseGraph.resolveCellSlot(10U, sparseSlot));
    assert(sparseSlot == 0U);
    assert(sparseGraph.resolveCellSlot(4000000000U, sparseSlot));
    assert(sparseSlot == 1U);
    assert(!sparseGraph.resolveCellSlot(123U, sparseSlot));

    std::array<xziel::StreamCellResourceDecision, 4>
        sparseDecisions{};
    std::array<xziel::StreamCellPlanCellState, 4>
        sparseStates{};
    std::size_t sparseWritten = 0U;
    std::size_t sparseCellWritten = 0U;

    const auto sparseStats =
        sparseGraph.plan(
            {
                .currentCell = 10U,
                .preloadPortalHops = 1U,
                .memoryPressure =
                    xziel::MemoryPressure::Normal,
            },
            sparseDecisions.data(),
            sparseDecisions.size(),
            sparseWritten,
            sparseStates.data(),
            sparseStates.size(),
            &sparseCellWritten);

    assert(sparseWritten == 1U);
    assert(sparseCellWritten == 2U);
    assert(sparseStats.hotCells == 1U);
    assert(sparseStats.preloadCells == 1U);
    assert(
        sparseGraph.cellReachableThroughOpenPortals(
            10U,
            4000000000U));

    return 0;
}
