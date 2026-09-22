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
    uint32_t material_flags;

    int frame;
    int skin;
    int render_mode;

    unsigned char scale;
    unsigned char priority_class;
    unsigned char lod;
    unsigned char kind;
    unsigned char visibility_class;

    float origin[3];
    float angles[3];
    float distance_sq;
    float view_forward;
    float view_right;
    float view_up;
    float base_rgba[4];
    float lit_rgba[4];
    unsigned int contributing_lights;
} XzRenderPacket;

typedef struct {
    uint64_t generation;
    int source_frame;
    XzDeviceTier device_tier;

    XzRenderPacket packets[XZ_RENDER_MAX_PACKETS];
    unsigned int source_packet_count;
    unsigned int packet_count;
    unsigned int culled_packets;
    unsigned int dropped_packets;

    unsigned int visibility_front_count;
    unsigned int visibility_edge_count;
    unsigned int visibility_behind_count;

    unsigned int near_count;
    unsigned int mid_count;
    unsigned int far_count;

    unsigned int full_animation_count;
    unsigned int shadow_count;
    unsigned int premium_vfx_count;

    unsigned int requested_lights;
    unsigned int admitted_lights;
    unsigned int dark_lights;

    unsigned int material_color_count;
    unsigned int material_translucent_count;
    unsigned int material_glow_count;
    unsigned int material_additive_count;
    unsigned int lit_packet_count;

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
