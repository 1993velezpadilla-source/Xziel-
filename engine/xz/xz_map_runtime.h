#ifndef XZ_MAP_RUNTIME_H
#define XZ_MAP_RUNTIME_H

#include "xz_nacht_reference.h"
#include "xz_bo3_weapon_specs.h"
#include "xz_world_transform.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_MAP_RUNTIME_NAME_MAX 64u

typedef enum XzMapRuntimeKind {
    XZ_MAP_RUNTIME_NONE = 0,
    XZ_MAP_RUNTIME_NACHT_BO3 = 1
} XzMapRuntimeKind;

typedef struct XzMapRuntimeState {
    XzMapRuntimeKind kind;
    char map_id[XZ_MAP_RUNTIME_NAME_MAX];
    uint64_t generation;
    XzWorldTransform world_transform;
    XzNachtGameplayState nacht;
} XzMapRuntimeState;

void XzMapRuntime_Init(XzMapRuntimeState *state);
void XzMapRuntime_SetWorldModel(
    XzMapRuntimeState *state,
    const char *world_model_name);

XzMapRuntimeKind XzMapRuntime_Kind(
    const XzMapRuntimeState *state);

const char *XzMapRuntime_MapId(
    const XzMapRuntimeState *state);

const XzWorldTransform *XzMapRuntime_WorldTransform(
    const XzMapRuntimeState *state);

int XzMapRuntime_SetWorldTransform(
    XzMapRuntimeState *state,
    const XzWorldTransform *transform);

int XzMapRuntime_NachtPurchasePositionUnits(
    const XzMapRuntimeState *state,
    size_t index,
    XzWorldVec3 *out_position_units);

const XzBo3WeaponSpec *XzMapRuntime_NachtPurchaseWeaponSpec(
    const XzMapRuntimeState *state,
    size_t index);

int XzMapRuntime_NachtDoorPositionUnits(
    const XzMapRuntimeState *state,
    size_t index,
    XzWorldVec3 *out_position_units);

int XzMapRuntime_NachtBarricadePositionUnits(
    const XzMapRuntimeState *state,
    size_t index,
    XzWorldVec3 *out_position_units);

int XzMapRuntime_NachtSpawnPositionUnits(
    const XzMapRuntimeState *state,
    size_t index,
    XzWorldVec3 *out_position_units);

int XzMapRuntime_NachtFindNearestPurchaseUnits(
    const XzMapRuntimeState *state,
    XzWorldVec3 player_position_units,
    size_t *out_index,
    float *out_distance_m);

int XzMapRuntime_NachtFindNearestDoorUnits(
    const XzMapRuntimeState *state,
    XzWorldVec3 player_position_units,
    size_t *out_index,
    float *out_distance_m);

XzNachtResult XzMapRuntime_NachtTryPurchaseUnits(
    XzMapRuntimeState *state,
    size_t index,
    XzWorldVec3 player_position_units,
    const char **out_logical_item_id);

XzNachtResult XzMapRuntime_NachtTryOpenDoorUnits(
    XzMapRuntimeState *state,
    size_t index,
    XzWorldVec3 player_position_units);

XzNachtGameplayState *XzMapRuntime_Nacht(
    XzMapRuntimeState *state);

const XzNachtGameplayState *XzMapRuntime_NachtConst(
    const XzMapRuntimeState *state);

int XzMapRuntime_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
