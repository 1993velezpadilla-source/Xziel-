#include "xz_map_runtime.h"

#include <assert.h>
#include <math.h>
#include <string.h>

int main(void)
{
    XzMapRuntimeState state;
    XzWorldVec3 position_units;
    size_t index = 999u;
    float distance_m = -1.0f;
    const char *item_id = 0;
    size_t purchase_index;
    size_t firearm_specs = 0u;

    assert(XzMapRuntime_SelfTest());
    assert(XzBo3WeaponSpec_SelfTest());

    XzMapRuntime_Init(&state);
    XzMapRuntime_SetWorldModel(&state, "maps/ndu.bsp");

    assert(XzMapRuntime_Kind(&state) == XZ_MAP_RUNTIME_NONE);
    assert(strcmp(XzMapRuntime_MapId(&state), "ndu") == 0);
    assert(XzMapRuntime_Nacht(&state) == 0);

    XzMapRuntime_SetWorldModel(
        &state,
        "maps/community_test.bsp");
    assert(XzMapRuntime_Kind(&state) == XZ_MAP_RUNTIME_NONE);
    assert(XzMapRuntime_IsVerifiedPackage(&state) == 0);

    XzMapRuntime_SetVerifiedPackageMode(&state, 1);
    assert(XzMapRuntime_IsVerifiedPackage(&state) == 1);
    assert(
        XzMapRuntime_Kind(&state) ==
        XZ_MAP_RUNTIME_XZIEL_PACKAGE);
    assert(
        strcmp(
            XzMapRuntime_KindName(XzMapRuntime_Kind(&state)),
            "XZIEL_PACKAGE") == 0);
    assert(XzMapRuntime_Nacht(&state) == 0);

    XzMapRuntime_SetVerifiedPackageMode(&state, 0);
    assert(XzMapRuntime_Kind(&state) == XZ_MAP_RUNTIME_NONE);

    XzMapRuntime_SetWorldModel(
        &state,
        "maps/xziel_nacht_bo3.bsp");

    assert(XzMapRuntime_Kind(&state) == XZ_MAP_RUNTIME_NACHT_BO3);
    assert(XzMapRuntime_Nacht(&state) != 0);
    assert(XzMapRuntime_Nacht(&state)->points == 500u);
    assert(XzNacht_ActiveSpawnCount(XzMapRuntime_Nacht(&state)) == 10u);

    for (purchase_index = 0u;
         purchase_index < XZ_NACHT_PURCHASE_COUNT;
         ++purchase_index) {
        const XzNachtPurchase *purchase =
            XzNacht_GetPurchase(purchase_index);
        const XzBo3WeaponSpec *spec =
            XzMapRuntime_NachtPurchaseWeaponSpec(
                &state,
                purchase_index);

        assert(purchase != 0);

        if (strcmp(
                purchase->logical_item_id,
                "frag_grenade") == 0) {
            assert(spec == 0);
            continue;
        }

        assert(spec != 0);
        assert(strcmp(
            spec->logical_item_id,
            purchase->logical_item_id) == 0);
        assert(strcmp(
            spec->display_name,
            purchase->display_name) == 0);
        assert(spec->wall_cost == purchase->price);
        firearm_specs++;
    }

    assert(firearm_specs == 8u);

    /* Exact RK5 reference position must survive meters -> runtime -> meters. */
    assert(XzMapRuntime_NachtPurchasePositionUnits(&state, 8u, &position_units));
    assert(fabsf(position_units.x - (-2.489199f * XZ_WORLD_UNITS_PER_METER)) < 0.002f);
    assert(fabsf(position_units.y - (-10.343102f * XZ_WORLD_UNITS_PER_METER)) < 0.002f);
    assert(fabsf(position_units.z - (1.411515f * XZ_WORLD_UNITS_PER_METER)) < 0.002f);

    assert(XzMapRuntime_NachtFindNearestPurchaseUnits(
        &state,
        position_units,
        &index,
        &distance_m));
    assert(index == 8u);
    assert(distance_m < 0.001f);

    assert(XzMapRuntime_NachtTryPurchaseUnits(
        &state,
        index,
        position_units,
        &item_id) == XZ_NACHT_RESULT_OK);
    assert(item_id != 0);
    assert(strcmp(item_id, "pistol_burst") == 0);
    assert(XzMapRuntime_Nacht(&state)->points == 0u);

    XzNacht_AwardPoints(XzMapRuntime_Nacht(&state), 1000u);
    assert(XzMapRuntime_NachtDoorPositionUnits(&state, 0u, &position_units));
    assert(XzMapRuntime_NachtFindNearestDoorUnits(
        &state,
        position_units,
        &index,
        &distance_m));
    assert(index == 0u);
    assert(XzMapRuntime_NachtTryOpenDoorUnits(
        &state,
        index,
        position_units) == XZ_NACHT_RESULT_OK);
    assert((XzMapRuntime_Nacht(&state)->active_zone_mask & XZ_NACHT_ZONE_BOX) != 0u);
    assert(XzNacht_ActiveSpawnCount(XzMapRuntime_Nacht(&state)) == 15u);

    XzNacht_AwardPoints(XzMapRuntime_Nacht(&state), 250u);
    assert(XzMapRuntime_Nacht(&state)->points == 250u);

    XzMapRuntime_SetWorldModel(
        &state,
        "maps/xziel_nacht_bo3.bsp");
    assert(XzMapRuntime_Nacht(&state)->points == 500u);

    return 0;
}
