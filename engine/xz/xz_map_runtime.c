#include "xz_map_runtime.h"

#include <stddef.h>
#include <string.h>

static const char *XzMapRuntime_BaseName(const char *name)
{
    const char *base = name;
    const char *cursor;

    if (!name)
        return "";

    for (cursor = name; *cursor; ++cursor) {
        if (*cursor == '/' || *cursor == '\\')
            base = cursor + 1;
    }

    return base;
}

static void XzMapRuntime_CopyMapId(
    char *destination,
    size_t destination_size,
    const char *world_model_name)
{
    const char *base;
    size_t length;

    if (!destination || destination_size == 0u)
        return;

    destination[0] = '\0';
    base = XzMapRuntime_BaseName(world_model_name);
    length = strlen(base);

    if (length >= 4u &&
        strcmp(base + length - 4u, ".bsp") == 0) {
        length -= 4u;
    }

    if (length >= destination_size)
        length = destination_size - 1u;

    if (length > 0u)
        memcpy(destination, base, length);

    destination[length] = '\0';
}

static XzMapRuntimeKind XzMapRuntime_Classify(
    const char *map_id)
{
    if (!map_id || !map_id[0])
        return XZ_MAP_RUNTIME_NONE;

    /*
     * Deliberately DO NOT treat stock "ndu" as the new BO3 reference.
     * That is the old NZ:P/Quake Nacht map and must remain isolated.
     */
    if (strcmp(map_id, "xziel_nacht_bo3") == 0 ||
        strcmp(map_id, "bo3_nacht_reference") == 0)
        return XZ_MAP_RUNTIME_NACHT_BO3;

    return XZ_MAP_RUNTIME_NONE;
}

void XzMapRuntime_Init(XzMapRuntimeState *state)
{
    if (!state)
        return;

    memset(state, 0, sizeof(*state));
    state->kind = XZ_MAP_RUNTIME_NONE;
    XzNacht_Reset(&state->nacht);
}

void XzMapRuntime_SetWorldModel(
    XzMapRuntimeState *state,
    const char *world_model_name)
{
    char next_id[XZ_MAP_RUNTIME_NAME_MAX];
    XzMapRuntimeKind next_kind;

    if (!state)
        return;

    XzMapRuntime_CopyMapId(
        next_id,
        sizeof(next_id),
        world_model_name);

    next_kind = XzMapRuntime_Classify(next_id);

    if (strcmp(state->map_id, next_id) == 0 &&
        state->kind == next_kind)
        return;

    memcpy(state->map_id, next_id, sizeof(state->map_id));
    state->kind = next_kind;
    state->generation++;

    XzNacht_Reset(&state->nacht);
}

XzMapRuntimeKind XzMapRuntime_Kind(
    const XzMapRuntimeState *state)
{
    return state ? state->kind : XZ_MAP_RUNTIME_NONE;
}

const char *XzMapRuntime_MapId(
    const XzMapRuntimeState *state)
{
    return state ? state->map_id : "";
}

XzNachtGameplayState *XzMapRuntime_Nacht(
    XzMapRuntimeState *state)
{
    if (!state || state->kind != XZ_MAP_RUNTIME_NACHT_BO3)
        return NULL;

    return &state->nacht;
}

const XzNachtGameplayState *XzMapRuntime_NachtConst(
    const XzMapRuntimeState *state)
{
    if (!state || state->kind != XZ_MAP_RUNTIME_NACHT_BO3)
        return NULL;

    return &state->nacht;
}

int XzMapRuntime_SelfTest(void)
{
    XzMapRuntimeState state;
    uint64_t generation;

    XzMapRuntime_Init(&state);

    if (state.kind != XZ_MAP_RUNTIME_NONE ||
        state.generation != 0u ||
        state.nacht.points != 500u ||
        state.nacht.active_zone_mask != XZ_NACHT_ZONE_START)
        return 0;

    /* Old Quake/NZ:P Nacht must never alias the XZIEL BO3 runtime. */
    XzMapRuntime_SetWorldModel(&state, "maps/ndu.bsp");
    if (state.kind != XZ_MAP_RUNTIME_NONE ||
        strcmp(state.map_id, "ndu") != 0 ||
        XzMapRuntime_Nacht(&state) != NULL)
        return 0;

    generation = state.generation;

    XzMapRuntime_SetWorldModel(
        &state,
        "maps/xziel_nacht_bo3.bsp");

    if (state.kind != XZ_MAP_RUNTIME_NACHT_BO3 ||
        strcmp(state.map_id, "xziel_nacht_bo3") != 0 ||
        XzMapRuntime_Nacht(&state) == NULL ||
        state.nacht.points != 500u ||
        XzNacht_ActiveSpawnCount(&state.nacht) != 10u ||
        state.generation != generation + 1u)
        return 0;

    XzNacht_AwardPoints(&state.nacht, 250u);
    if (state.nacht.points != 750u)
        return 0;

    /* Reloading the same world does not reset state accidentally. */
    generation = state.generation;
    XzMapRuntime_SetWorldModel(
        &state,
        "maps/xziel_nacht_bo3.bsp");
    if (state.generation != generation ||
        state.nacht.points != 750u)
        return 0;

    XzMapRuntime_SetWorldModel(&state, "maps/ndu.bsp");
    if (state.kind != XZ_MAP_RUNTIME_NONE ||
        state.nacht.points != 500u ||
        state.generation != generation + 1u)
        return 0;

    return 1;
}
