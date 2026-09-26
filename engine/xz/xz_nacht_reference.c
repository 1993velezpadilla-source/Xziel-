#include "xz_nacht_reference.h"

#include <float.h>
#include <math.h>

static const XzNachtPurchase kPurchases[XZ_NACHT_PURCHASE_COUNT] = {
    {"purchase_arak", "KN-44", "ar_standard", XZ_NACHT_PURCHASE_WALL_WEAPON, 1400u, XZ_NACHT_ZONE_START, {-5.709419f, 26.457163f, 4.990672f}, 1.5f},
    {"purchase_argus", "Argus", "shotgun_precision", XZ_NACHT_PURCHASE_WALL_WEAPON, 1100u, XZ_NACHT_ZONE_UPSTAIRS, {18.624508f, 25.683310f, 5.707007f}, 1.5f},
    {"purchase_frag", "Fragmentation Grenades", "frag_grenade", XZ_NACHT_PURCHASE_EQUIPMENT, 250u, XZ_NACHT_ZONE_UPSTAIRS, {-3.960460f, -3.098613f, 5.046703f}, 1.5f},
    {"purchase_krm", "KRM-262", "shotgun_pump", XZ_NACHT_PURCHASE_WALL_WEAPON, 750u, XZ_NACHT_ZONE_BOX, {26.352487f, 19.632632f, 1.440421f}, 1.5f},
    {"purchase_kuda", "Kuda", "smg_standard", XZ_NACHT_PURCHASE_WALL_WEAPON, 1250u, XZ_NACHT_ZONE_BOX, {24.049902f, 25.628601f, 1.360282f}, 1.5f},
    {"purchase_locus_decal", "Locus", "sniper_fastbolt", XZ_NACHT_PURCHASE_WEAPON_CABINET, 5000u, XZ_NACHT_ZONE_UPSTAIRS, {14.256981f, 22.525286f, 4.376229f}, 1.5f},
    {"purchase_pharaoh", "Pharo", "smg_burst", XZ_NACHT_PURCHASE_WALL_WEAPON, 700u, XZ_NACHT_ZONE_UPSTAIRS, {5.424384f, 11.316592f, 5.046703f}, 1.5f},
    {"purchase_shiva", "Sheiva", "ar_marksman", XZ_NACHT_PURCHASE_WALL_WEAPON, 500u, XZ_NACHT_ZONE_START, {-5.232187f, 6.058283f, 1.440421f}, 1.5f},
    {"purchase_triton", "RK5", "pistol_burst", XZ_NACHT_PURCHASE_WALL_WEAPON, 500u, XZ_NACHT_ZONE_START, {-2.489199f, -10.343102f, 1.411515f}, 1.5f}
};

static const XzNachtDoor kDoors[XZ_NACHT_DOOR_COUNT] = {
    /*
     * Canonical Nacht progression contains three 1000-point routes.
     * Source transforms are mapped from the port actors by DoorFlag topology.
     * The unflagged 10000-point port actor is deliberately excluded.
     */
    {"door_start_to_box", "BuyableDoor_2", 1000u, XZ_NACHT_ZONE_START, XZ_NACHT_ZONE_BOX, {4.343400f, 14.884401f, 1.244600f}, 1.6f},
    {"door_start_to_upstairs", "BuyableDoor_Child2", 1000u, XZ_NACHT_ZONE_START, XZ_NACHT_ZONE_UPSTAIRS, {4.290648f, 2.219196f, 4.073596f}, 1.6f},
    {"door_box_to_upstairs", "BuyableDoor_Child_2", 1000u, XZ_NACHT_ZONE_BOX, XZ_NACHT_ZONE_UPSTAIRS, {-1.153160f, 26.810671f, 4.003040f}, 1.6f}
};

static const XzNachtBarricade kBarricades[XZ_NACHT_BARRICADE_COUNT] = {
    {"barricade_barricade_2", {-5.481379f, 12.309495f, 0.025401f}, 6u},
    {"barricade_barricade2", {-5.481376f, -4.917536f, 0.025401f}, 6u},
    {"barricade_barricade3", {-5.481377f, -19.173562f, 0.025401f}, 6u},
    {"barricade_barricade4", {4.326169f, -22.417964f, 0.025401f}, 6u},
    {"barricade_barricade5", {5.845164f, -6.443779f, 0.025401f}, 6u},
    {"barricade_barricade6", {16.195526f, 15.702350f, 0.025390f}, 6u},
    {"barricade_barricade7", {26.659043f, 22.807122f, 0.025390f}, 6u},
    {"barricade_barricade8", {11.449548f, 25.872959f, 0.025390f}, 6u},
    {"barricade_barricade9", {5.632709f, 6.218766f, 3.683001f}, 6u},
    {"barricade_barricade10", {7.165343f, 14.786189f, 3.683001f}, 6u},
    {"barricade_barricade11", {5.965834f, 28.830867f, 3.683001f}, 6u},
    {"barricade_barricade12", {23.085383f, 25.925994f, 3.683001f}, 6u}
};

static const XzNachtSpawn kSpawns[XZ_NACHT_SPAWN_COUNT] = {
    {"zspawn_zombiespawner10", {12.877046f, -2.727291f, 0.001000f}, XZ_NACHT_ZONE_START, 1u, 1u, 4u},
    {"zspawn_zombiespawner11", {14.172050f, 6.879191f, 0.125601f}, XZ_NACHT_ZONE_BOX, 0u, 1u, 5u},
    {"zspawn_zombiespawner12", {20.629141f, 10.613967f, 0.168620f}, XZ_NACHT_ZONE_BOX, 0u, 1u, 5u},
    {"zspawn_zombiespawner13", {15.286886f, 33.425278f, -0.120566f}, XZ_NACHT_ZONE_BOX, 0u, 0u, 7u},
    {"zspawn_zombiespawner14", {38.909851f, 15.198732f, -0.648941f}, XZ_NACHT_ZONE_BOX, 0u, 1u, 6u},
    {"zspawn_zombiespawner15", {37.457021f, 16.985983f, -0.498080f}, XZ_NACHT_ZONE_BOX, 0u, 1u, 6u},
    {"zspawn_zombiespawner16", {14.516221f, -0.836329f, -0.038027f}, XZ_NACHT_ZONE_UPSTAIRS, 0u, 1u, 8u},
    {"zspawn_zombiespawner17", {12.062819f, -6.670211f, -0.095225f}, XZ_NACHT_ZONE_UPSTAIRS, 0u, 1u, 9u},
    {"zspawn_zombiespawner18", {10.492319f, 40.282625f, 3.810003f}, XZ_NACHT_ZONE_UPSTAIRS, 0u, 1u, 10u},
    {"zspawn_zombiespawner19", {10.631847f, 28.723784f, 3.810002f}, XZ_NACHT_ZONE_UPSTAIRS, 0u, 1u, 10u},
    {"zspawn_zombiespawner20", {15.181989f, 27.959873f, 3.903218f}, XZ_NACHT_ZONE_UPSTAIRS, 0u, 1u, 11u},
    {"zspawn_zombiespawner21", {25.405664f, 38.515093f, 3.408246f}, XZ_NACHT_ZONE_UPSTAIRS, 0u, 1u, 11u},
    {"zspawn_zombiespawner2_20", {-14.535648f, 4.694192f, -0.271532f}, XZ_NACHT_ZONE_START, 1u, 1u, 0u},
    {"zspawn_zombiespawner3_23", {-15.354806f, -0.237418f, -0.333972f}, XZ_NACHT_ZONE_START, 1u, 1u, 1u},
    {"zspawn_zombiespawner4", {-7.490383f, -15.384512f, -0.129635f}, XZ_NACHT_ZONE_START, 1u, 1u, 2u},
    {"zspawn_zombiespawner5", {-15.101215f, -22.086555f, -0.774332f}, XZ_NACHT_ZONE_START, 1u, 1u, 2u},
    {"zspawn_zombiespawner6", {-14.392579f, -11.247102f, -0.474903f}, XZ_NACHT_ZONE_START, 1u, 1u, 1u},
    {"zspawn_zombiespawner7", {10.037568f, -33.212349f, 0.230940f}, XZ_NACHT_ZONE_START, 1u, 1u, 3u},
    {"zspawn_zombiespawner8", {8.901859f, -25.665203f, 0.020444f}, XZ_NACHT_ZONE_START, 1u, 1u, 3u},
    {"zspawn_zombiespawner9", {12.994844f, -12.927321f, -0.221694f}, XZ_NACHT_ZONE_START, 1u, 1u, 4u},
    {"zspawn_zombiespawner_16", {-16.258293f, 16.088809f, -0.130339f}, XZ_NACHT_ZONE_START, 1u, 0u, 0u}
};

static float distance_m(XzNachtVec3 a, XzNachtVec3 b)
{
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    const float dz = a.z - b.z;
    return sqrtf(dx * dx + dy * dy + dz * dz);
}

const XzNachtPurchase *XzNacht_GetPurchase(size_t index)
{
    return index < XZ_NACHT_PURCHASE_COUNT ? &kPurchases[index] : NULL;
}

const XzNachtDoor *XzNacht_GetDoor(size_t index)
{
    return index < XZ_NACHT_DOOR_COUNT ? &kDoors[index] : NULL;
}

const XzNachtBarricade *XzNacht_GetBarricade(size_t index)
{
    return index < XZ_NACHT_BARRICADE_COUNT ? &kBarricades[index] : NULL;
}

const XzNachtSpawn *XzNacht_GetSpawn(size_t index)
{
    return index < XZ_NACHT_SPAWN_COUNT ? &kSpawns[index] : NULL;
}

void XzNacht_Reset(XzNachtGameplayState *state)
{
    size_t i;

    if (state == NULL)
        return;

    state->points = 500u;
    state->active_zone_mask = XZ_NACHT_ZONE_START;

    for (i = 0; i < XZ_NACHT_DOOR_COUNT; ++i)
        state->door_open[i] = 0u;

    for (i = 0; i < XZ_NACHT_BARRICADE_COUNT; ++i)
        state->barricade_boards[i] = kBarricades[i].maximum_boards;
}

void XzNacht_AwardPoints(XzNachtGameplayState *state, uint32_t points)
{
    if (state == NULL)
        return;

    if (UINT32_MAX - state->points < points)
        state->points = UINT32_MAX;
    else
        state->points += points;
}

size_t XzNacht_ActiveSpawnCount(const XzNachtGameplayState *state)
{
    size_t i;
    size_t count = 0u;

    if (state == NULL)
        return 0u;

    for (i = 0; i < XZ_NACHT_SPAWN_COUNT; ++i) {
        if ((state->active_zone_mask & kSpawns[i].zone_mask) != 0u)
            ++count;
    }

    return count;
}

int XzNacht_FindNearestPurchase(
    const XzNachtGameplayState *state,
    XzNachtVec3 player_position_m,
    size_t *out_index,
    float *out_distance_m)
{
    size_t i;
    size_t best_index = 0u;
    float best_distance = FLT_MAX;
    int found = 0;

    if (state == NULL)
        return 0;

    for (i = 0; i < XZ_NACHT_PURCHASE_COUNT; ++i) {
        const XzNachtPurchase *purchase = &kPurchases[i];
        float d;

        if ((state->active_zone_mask & purchase->required_zone_mask) == 0u)
            continue;

        d = distance_m(player_position_m, purchase->position_m);
        if (d > purchase->interaction_radius_m || d >= best_distance)
            continue;

        found = 1;
        best_index = i;
        best_distance = d;
    }

    if (!found)
        return 0;

    if (out_index != NULL)
        *out_index = best_index;
    if (out_distance_m != NULL)
        *out_distance_m = best_distance;

    return 1;
}

int XzNacht_FindNearestDoor(
    const XzNachtGameplayState *state,
    XzNachtVec3 player_position_m,
    size_t *out_index,
    float *out_distance_m)
{
    size_t i;
    size_t best_index = 0u;
    float best_distance = FLT_MAX;
    int found = 0;

    if (state == NULL)
        return 0;

    for (i = 0; i < XZ_NACHT_DOOR_COUNT; ++i) {
        const XzNachtDoor *door = &kDoors[i];
        float d;

        if (state->door_open[i])
            continue;
        if ((state->active_zone_mask & door->required_zone_mask) == 0u)
            continue;
        if ((state->active_zone_mask & door->unlock_zone_mask) == door->unlock_zone_mask)
            continue;

        d = distance_m(player_position_m, door->position_m);
        if (d > door->interaction_radius_m || d >= best_distance)
            continue;

        found = 1;
        best_index = i;
        best_distance = d;
    }

    if (!found)
        return 0;

    if (out_index != NULL)
        *out_index = best_index;
    if (out_distance_m != NULL)
        *out_distance_m = best_distance;

    return 1;
}

XzNachtResult XzNacht_TryPurchase(
    XzNachtGameplayState *state,
    size_t index,
    XzNachtVec3 player_position_m,
    const char **out_logical_item_id)
{
    const XzNachtPurchase *purchase;

    if (state == NULL || index >= XZ_NACHT_PURCHASE_COUNT)
        return XZ_NACHT_RESULT_INVALID_INDEX;

    purchase = &kPurchases[index];

    if ((state->active_zone_mask & purchase->required_zone_mask) == 0u)
        return XZ_NACHT_RESULT_LOCKED_ZONE;

    if (distance_m(player_position_m, purchase->position_m) > purchase->interaction_radius_m)
        return XZ_NACHT_RESULT_OUT_OF_RANGE;

    if (state->points < purchase->price)
        return XZ_NACHT_RESULT_INSUFFICIENT_POINTS;

    state->points -= purchase->price;

    if (out_logical_item_id != NULL)
        *out_logical_item_id = purchase->logical_item_id;

    return XZ_NACHT_RESULT_OK;
}

XzNachtResult XzNacht_TryOpenDoor(
    XzNachtGameplayState *state,
    size_t index,
    XzNachtVec3 player_position_m)
{
    const XzNachtDoor *door;

    if (state == NULL || index >= XZ_NACHT_DOOR_COUNT)
        return XZ_NACHT_RESULT_INVALID_INDEX;

    door = &kDoors[index];

    if (state->door_open[index] ||
        (state->active_zone_mask & door->unlock_zone_mask) == door->unlock_zone_mask)
        return XZ_NACHT_RESULT_ALREADY_OPEN;

    if ((state->active_zone_mask & door->required_zone_mask) == 0u)
        return XZ_NACHT_RESULT_LOCKED_ZONE;

    if (distance_m(player_position_m, door->position_m) > door->interaction_radius_m)
        return XZ_NACHT_RESULT_OUT_OF_RANGE;

    if (state->points < door->price)
        return XZ_NACHT_RESULT_INSUFFICIENT_POINTS;

    state->points -= door->price;
    state->door_open[index] = 1u;
    state->active_zone_mask |= door->unlock_zone_mask;

    return XZ_NACHT_RESULT_OK;
}

XzNachtResult XzNacht_BreakBarricadeBoard(
    XzNachtGameplayState *state,
    size_t index)
{
    if (state == NULL || index >= XZ_NACHT_BARRICADE_COUNT)
        return XZ_NACHT_RESULT_INVALID_INDEX;

    if (state->barricade_boards[index] == 0u)
        return XZ_NACHT_RESULT_NOT_REPAIRABLE;

    --state->barricade_boards[index];
    return XZ_NACHT_RESULT_OK;
}

XzNachtResult XzNacht_RepairBarricadeBoard(
    XzNachtGameplayState *state,
    size_t index)
{
    if (state == NULL || index >= XZ_NACHT_BARRICADE_COUNT)
        return XZ_NACHT_RESULT_INVALID_INDEX;

    if (state->barricade_boards[index] >= kBarricades[index].maximum_boards)
        return XZ_NACHT_RESULT_NOT_REPAIRABLE;

    ++state->barricade_boards[index];
    return XZ_NACHT_RESULT_OK;
}
