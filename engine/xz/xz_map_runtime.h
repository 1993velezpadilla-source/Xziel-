#ifndef XZ_MAP_RUNTIME_H
#define XZ_MAP_RUNTIME_H

#include "xz_nacht_reference.h"

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

XzNachtGameplayState *XzMapRuntime_Nacht(
    XzMapRuntimeState *state);

const XzNachtGameplayState *XzMapRuntime_NachtConst(
    const XzMapRuntimeState *state);

int XzMapRuntime_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
