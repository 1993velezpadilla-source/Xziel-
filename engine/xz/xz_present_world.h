#ifndef XZ_PRESENT_WORLD_H
#define XZ_PRESENT_WORLD_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_PRESENT_MAX_ENTITIES 512u

typedef enum {
    XZ_PRESENT_UNKNOWN = 0,
    XZ_PRESENT_BRUSH,
    XZ_PRESENT_SPRITE,
    XZ_PRESENT_ALIAS
} XzPresentKind;

typedef struct {
    uint32_t source_id;
    uint32_t asset_hash;
    uint32_t effects;
    int frame;
    int skin;
    int render_mode;
    unsigned char scale;
    unsigned char priority_class;
    XzPresentKind kind;
    float origin[3];
    float angles[3];
    float distance_sq;
} XzPresentEntity;

typedef struct {
    uint64_t generation;
    int source_frame;
    float camera_origin[3];

    XzPresentEntity entities[XZ_PRESENT_MAX_ENTITIES];
    unsigned int entity_count;
    unsigned int dropped_entities;

    unsigned int alias_count;
    unsigned int brush_count;
    unsigned int sprite_count;
    unsigned int unknown_count;

    unsigned int static_brush_count;
    unsigned int active_light_count;

    float nearest_distance_sq;
    float farthest_distance_sq;
} XzPresentFrame;

void XzPresentWorld_Init(void);
void XzPresentWorld_Begin(
    int source_frame,
    const float camera_origin[3]);
int XzPresentWorld_Push(const XzPresentEntity *entity);
void XzPresentWorld_SetStaticBrushCount(unsigned int count);
void XzPresentWorld_SetActiveLightCount(unsigned int count);
void XzPresentWorld_Commit(void);
const XzPresentFrame *XzPresentWorld_GetReadFrame(void);

uint32_t XzPresentWorld_HashAssetName(const char *name);
int XzPresentWorld_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
