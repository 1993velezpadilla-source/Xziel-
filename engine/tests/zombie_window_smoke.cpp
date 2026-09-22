#include "xziel/zombie_window.hpp"

#include <cassert>

int main() {
    xziel::HordeDirector horde;
    xziel::ScoreSystem score;
    xziel::FpsPlayerController player;
    xziel::ZombieWindowSystem windows;

    assert(windows.addWindow(
        {
            .id = 101,
            .blocker = {
                .minimum = {-0.8f, -1.6f, 0.5f},
                .maximum = { 0.8f,  0.9f, 0.8f},
            },
            .barricade = {
                .maximumPlanks = 2,
                .zombieTearSeconds = 0.10f,
                .rebuildSeconds = 0.10f,
                .rebuildPointsPerPlank = 10,
                .maximumRebuildPointsPerRound = 10,
            },
            .visual = {
                .plankMaterialId = 41U,
                .debrisMaterialId = 42U,
                .plankMeshSetId = 7U,
                .visualSeed = 123456U,
            },
        },
        horde,
        player));
    assert(!windows.addWindow({.id = 101}, horde, player));

    const auto* visual = windows.visual(101U);
    assert(visual != nullptr);
    assert(visual->plankMaterialId == 41U);
    assert(visual->debrisMaterialId == 42U);
    assert(visual->plankMeshSetId == 7U);
    assert(visual->visualSeed == 123456U);

    xziel::ZombieWindowFrame frame{};
    for (int plank = 0; plank < 2; ++plank) {
        for (int tick = 0; tick < 2; ++tick) {
            frame = windows.step(101, true, false, 0.05f, horde, player, score);
        }
    }
    assert(frame.barricade.breachedThisTick);
    assert(!frame.navigationBlocked);

    for (int tick = 0; tick < 2; ++tick) {
        frame = windows.step(101, false, true, 0.05f, horde, player, score);
    }
    assert(frame.navigationBlocked);
    assert(frame.barricade.intactPlanks == 1);
    assert(score.frame().total == 10);

    // The per-round cap prevents farming the same window indefinitely.
    for (int tick = 0; tick < 2; ++tick) {
        frame = windows.step(101, false, true, 0.05f, horde, player, score);
    }
    assert(score.frame().total == 10);

    windows.beginRound();
    for (int tick = 0; tick < 2; ++tick) {
        frame = windows.step(101, true, false, 0.05f, horde, player, score);
    }
    for (int tick = 0; tick < 2; ++tick) {
        frame = windows.step(101, false, true, 0.05f, horde, player, score);
    }
    assert(score.frame().total == 20);

    for (int plank = 0; plank < 2; ++plank) {
        for (int tick = 0; tick < 2; ++tick) {
            frame = windows.step(
                101,
                true,
                false,
                0.05f,
                horde,
                player,
                score);
        }
    }
    assert(!frame.navigationBlocked);

    const auto beforeRepairScore = score.frame().total;
    assert(windows.repairAll(horde, player) == 1U);
    frame = *windows.frame(101U);
    assert(frame.navigationBlocked);
    assert(frame.barricade.intactPlanks == 2U);
    assert(score.frame().total == beforeRepairScore);

    return 0;
}
