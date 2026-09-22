#ifndef XZ_MATERIAL_LIGHTING_H
#define XZ_MATERIAL_LIGHTING_H

#include "xz_present_world.h"
#include "xz_scene_budget.h"

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_MATERIAL_MAX_LIGHTS XZ_PRESENT_MAX_LIGHTS

enum {
    XZ_MATERIAL_COLOR       = 1u << 0,
    XZ_MATERIAL_TEXTURE     = 1u << 1,
    XZ_MATERIAL_GLOW        = 1u << 2,
    XZ_MATERIAL_SOLID       = 1u << 3,
    XZ_MATERIAL_ADDITIVE    = 1u << 4,
    XZ_MATERIAL_LMPOINT     = 1u << 5,
    XZ_MATERIAL_TRANSLUCENT = 1u << 6
};

typedef struct {
    XzPresentLight light;
    float camera_distance_sq;
    float score;
} XzMaterialLight;

typedef struct {
    XzMaterialLight lights[XZ_MATERIAL_MAX_LIGHTS];
    unsigned int count;
    unsigned int requested_count;
    unsigned int dark_count;
} XzMaterialLightSet;

typedef struct {
    unsigned int flags;
    float base_rgba[4];
    float lit_rgba[4];
    unsigned int contributing_lights;
} XzMaterialSample;

void XzMaterialLighting_Select(
    XzMaterialLightSet *set,
    const XzPresentFrame *frame,
    const XzSceneBudget *budget);

void XzMaterialLighting_Shade(
    XzMaterialSample *sample,
    const XzPresentEntity *entity,
    const XzMaterialLightSet *set);

int XzMaterialLighting_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
