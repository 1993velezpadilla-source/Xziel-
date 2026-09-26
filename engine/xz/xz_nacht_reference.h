#ifndef XZ_NACHT_REFERENCE_H
#define XZ_NACHT_REFERENCE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_NACHT_PURCHASE_COUNT 9u
#define XZ_NACHT_DOOR_COUNT 3u
#define XZ_NACHT_SPAWN_COUNT 21u
#define XZ_NACHT_BARRICADE_COUNT 12u

#define XZ_NACHT_ZONE_START (1u << 0u)
#define XZ_NACHT_ZONE_BOX (1u << 1u)
#define XZ_NACHT_ZONE_UPSTAIRS (1u << 2u)
#define XZ_NACHT_ZONE_ALL (XZ_NACHT_ZONE_START | XZ_NACHT_ZONE_BOX | XZ_NACHT_ZONE_UPSTAIRS)

typedef enum XzNachtPurchaseKind {
    XZ_NACHT_PURCHASE_WALL_WEAPON = 0,
    XZ_NACHT_PURCHASE_WEAPON_CABINET = 1,
    XZ_NACHT_PURCHASE_EQUIPMENT = 2
} XzNachtPurchaseKind;

typedef struct XzNachtVec3 {
    float x;
    float y;
    float z;
} XzNachtVec3;

typedef struct XzNachtPurchase {
    const char *id;
    const char *display_name;
    const char *logical_item_id;
    XzNachtPurchaseKind kind;
    uint32_t price;
    uint32_t required_zone_mask;
    XzNachtVec3 position_m;
    float interaction_radius_m;
} XzNachtPurchase;

typedef struct XzNachtDoor {
    const char *id;
    const char *source_actor;
    uint32_t price;
    uint32_t required_zone_mask;
    uint32_t unlock_zone_mask;
    XzNachtVec3 position_m;
    float interaction_radius_m;
} XzNachtDoor;

typedef struct XzNachtBarricade {
    const char *id;
    XzNachtVec3 position_m;
    uint8_t maximum_boards;
} XzNachtBarricade;

typedef struct XzNachtSpawn {
    const char *id;
    XzNachtVec3 position_m;
    uint32_t zone_mask;
    uint8_t active_default;
    uint8_t riser;
    uint8_t barricade_index;
} XzNachtSpawn;

typedef enum XzNachtResult {
    XZ_NACHT_RESULT_OK = 0,
    XZ_NACHT_RESULT_INVALID_INDEX,
    XZ_NACHT_RESULT_LOCKED_ZONE,
    XZ_NACHT_RESULT_OUT_OF_RANGE,
    XZ_NACHT_RESULT_INSUFFICIENT_POINTS,
    XZ_NACHT_RESULT_ALREADY_OPEN,
    XZ_NACHT_RESULT_NOT_REPAIRABLE
} XzNachtResult;

typedef struct XzNachtGameplayState {
    uint32_t points;
    uint32_t active_zone_mask;
    uint8_t door_open[XZ_NACHT_DOOR_COUNT];
    uint8_t barricade_boards[XZ_NACHT_BARRICADE_COUNT];
} XzNachtGameplayState;

const XzNachtPurchase *XzNacht_GetPurchase(size_t index);
const XzNachtDoor *XzNacht_GetDoor(size_t index);
const XzNachtBarricade *XzNacht_GetBarricade(size_t index);
const XzNachtSpawn *XzNacht_GetSpawn(size_t index);

void XzNacht_Reset(XzNachtGameplayState *state);
void XzNacht_AwardPoints(XzNachtGameplayState *state, uint32_t points);

size_t XzNacht_ActiveSpawnCount(const XzNachtGameplayState *state);
int XzNacht_FindNearestPurchase(
    const XzNachtGameplayState *state,
    XzNachtVec3 player_position_m,
    size_t *out_index,
    float *out_distance_m);
int XzNacht_FindNearestDoor(
    const XzNachtGameplayState *state,
    XzNachtVec3 player_position_m,
    size_t *out_index,
    float *out_distance_m);

XzNachtResult XzNacht_TryPurchase(
    XzNachtGameplayState *state,
    size_t index,
    XzNachtVec3 player_position_m,
    const char **out_logical_item_id);

XzNachtResult XzNacht_TryOpenDoor(
    XzNachtGameplayState *state,
    size_t index,
    XzNachtVec3 player_position_m);

XzNachtResult XzNacht_BreakBarricadeBoard(
    XzNachtGameplayState *state,
    size_t index);

XzNachtResult XzNacht_RepairBarricadeBoard(
    XzNachtGameplayState *state,
    size_t index);

#ifdef __cplusplus
}
#endif

#endif
