#ifndef XZ_PRESENT_WORLD_H
#define XZ_PRESENT_WORLD_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_PRESENT_MAX_ENTITIES 512u
#define XZ_PRESENT_MAX_LIGHTS 32u

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
    float render_amount;
    float render_color[3];
    unsigned char scale;
    unsigned char priority_class;
    XzPresentKind kind;
    float origin[3];
    float angles[3];
    float distance_sq;
} XzPresentEntity;

typedef struct {
    float origin[3];
    float color[3];
    float radius;
    float minlight;
    int type;
    int dark;
} XzPresentLight;

typedef struct {
    uint64_t generation;
    int source_frame;
    float camera_origin[3];
    float camera_forward[3];
    float camera_right[3];
    float camera_up[3];
    float fov_x;
    float fov_y;
    int camera_basis_valid;

    XzPresentEntity entities[XZ_PRESENT_MAX_ENTITIES];
    unsigned int entity_count;
    unsigned int dropped_entities;

    unsigned int alias_count;
    unsigned int brush_count;
    unsigned int sprite_count;
    unsigned int unknown_count;

    unsigned int static_brush_count;
    XzPresentLight lights[XZ_PRESENT_MAX_LIGHTS];
    unsigned int active_light_count;
    unsigned int dropped_lights;

    float nearest_distance_sq;
    float farthest_distance_sq;
} XzPresentFrame;

void XzPresentWorld_Init(void);
void XzPresentWorld_Begin(
    int source_frame,
    const float camera_origin[3]);
int XzPresentWorld_Push(const XzPresentEntity *entity);
void XzPresentWorld_SetCameraBasis(
    const float forward[3],
    const float right[3],
    const float up[3],
    float fov_x,
    float fov_y);
void XzPresentWorld_SetStaticBrushCount(unsigned int count);
int XzPresentWorld_PushLight(const XzPresentLight *light);
void XzPresentWorld_SetActiveLightCount(unsigned int count);
void XzPresentWorld_Commit(void);
const XzPresentFrame *XzPresentWorld_GetReadFrame(void);

uint32_t XzPresentWorld_HashAssetName(const char *name);
int XzPresentWorld_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
