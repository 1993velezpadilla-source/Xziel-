#include "xz_nacht_reference.h"

#include <assert.h>
#include <stddef.h>
#include <string.h>

int main(void)
{
    XzNachtGameplayState state;
    const XzNachtPurchase *rk5;
    const XzNachtSpawn *spawn;
    const char *item_id = NULL;
    size_t index = 999u;
    float distance = -1.0f;
    size_t i;

    assert(XZ_NACHT_PURCHASE_COUNT == 9u);
    assert(XZ_NACHT_DOOR_COUNT == 3u);
    assert(XZ_NACHT_SPAWN_COUNT == 21u);
    assert(XZ_NACHT_BARRICADE_COUNT == 12u);

    XzNacht_Reset(&state);
    assert(state.points == 500u);
    assert(state.active_zone_mask == XZ_NACHT_ZONE_START);
    assert(XzNacht_ActiveSpawnCount(&state) == 10u);

    for (i = 0; i < XZ_NACHT_BARRICADE_COUNT; ++i)
        assert(state.barricade_boards[i] == 6u);

    rk5 = XzNacht_GetPurchase(8u);
    assert(rk5 != NULL);
    assert(strcmp(rk5->display_name, "RK5") == 0);
    assert(rk5->price == 500u);

    assert(XzNacht_FindNearestPurchase(
        &state,
        rk5->position_m,
        &index,
        &distance));
    assert(index == 8u);
    assert(distance < 0.001f);

    assert(XzNacht_TryPurchase(
        &state,
        8u,
        rk5->position_m,
        &item_id) == XZ_NACHT_RESULT_OK);
    assert(item_id != NULL);
    assert(strcmp(item_id, "pistol_burst") == 0);
    assert(state.points == 0u);

    /* Kuda belongs to the Help/box zone and must remain gated. */
    assert(!XzNacht_FindNearestPurchase(
        &state,
        XzNacht_GetPurchase(4u)->position_m,
        &index,
        &distance));

    XzNacht_AwardPoints(&state, 2500u);
    assert(state.points == 2500u);

    assert(XzNacht_TryOpenDoor(
        &state,
        0u,
        XzNacht_GetDoor(0u)->position_m) == XZ_NACHT_RESULT_OK);
    assert(state.points == 1500u);
    assert((state.active_zone_mask & XZ_NACHT_ZONE_BOX) != 0u);
    assert(XzNacht_ActiveSpawnCount(&state) == 15u);

    assert(XzNacht_FindNearestPurchase(
        &state,
        XzNacht_GetPurchase(4u)->position_m,
        &index,
        &distance));
    assert(index == 4u);

    assert(XzNacht_TryOpenDoor(
        &state,
        2u,
        XzNacht_GetDoor(2u)->position_m) == XZ_NACHT_RESULT_OK);
    assert(state.points == 500u);
    assert(state.active_zone_mask == XZ_NACHT_ZONE_ALL);
    assert(XzNacht_ActiveSpawnCount(&state) == 21u);

    spawn = XzNacht_GetSpawn(12u);
    assert(spawn != NULL);
    assert(spawn->barricade_index == 0u);

    for (i = 0; i < 6u; ++i)
        assert(XzNacht_BreakBarricadeBoard(&state, 0u) == XZ_NACHT_RESULT_OK);
    assert(state.barricade_boards[0] == 0u);
    assert(XzNacht_RepairBarricadeBoard(&state, 0u) == XZ_NACHT_RESULT_OK);
    assert(state.barricade_boards[0] == 1u);

    return 0;
}
