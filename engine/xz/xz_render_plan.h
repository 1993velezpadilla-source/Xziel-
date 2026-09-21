#ifndef XZ_RENDER_PLAN_H
#define XZ_RENDER_PLAN_H

#include "xz_device_caps.h"
#include "xz_present_world.h"
#include "xz_scene_budget.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_RENDER_MAX_PACKETS XZ_PRESENT_MAX_ENTITIES

enum {
    XZ_RENDER_FEATURE_FULL_ANIMATION = 1u << 0,
    XZ_RENDER_FEATURE_SHADOW         = 1u << 1,
    XZ_RENDER_FEATURE_PREMIUM_VFX    = 1u << 2
};

typedef enum {
    XZ_RENDER_LOD_NEAR = 0,
    XZ_RENDER_LOD_MID,
    XZ_RENDER_LOD_FAR
} XzRenderLod;

typedef struct {
    uint32_t source_id;
    uint32_t asset_hash;
    uint32_t effects;
    uint32_t feature_mask;

    int frame;
    int skin;
    int render_mode;

    unsigned char scale;
    unsigned char priority_class;
    unsigned char lod;
    unsigned char kind;

    float origin[3];
    float angles[3];
    float distance_sq;
} XzRenderPacket;

typedef struct {
    uint64_t generation;
    int source_frame;
    XzDeviceTier device_tier;

    XzRenderPacket packets[XZ_RENDER_MAX_PACKETS];
    unsigned int packet_count;
    unsigned int dropped_packets;

    unsigned int near_count;
    unsigned int mid_count;
    unsigned int far_count;

    unsigned int full_animation_count;
    unsigned int shadow_count;
    unsigned int premium_vfx_count;

    unsigned int requested_lights;
    unsigned int admitted_lights;

    uint32_t content_hash;
} XzRenderPlan;

void XzRenderPlan_Init(XzRenderPlan *plan);
void XzRenderPlan_Build(
    XzRenderPlan *plan,
    const XzPresentFrame *frame,
    const XzSceneBudget *budget,
    XzDeviceTier tier);

int XzRenderPlan_Validate(const XzRenderPlan *plan);
int XzRenderPlan_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
