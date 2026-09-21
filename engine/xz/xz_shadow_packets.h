#ifndef XZ_SHADOW_PACKETS_H
#define XZ_SHADOW_PACKETS_H

#include "xz_render_plan.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float world_meta[4];
    float render_meta[4];
} XzShadowInstance;

unsigned int XzShadowPackets_Pack(
    const XzRenderPlan *plan,
    XzShadowInstance *instances,
    unsigned int capacity);

int XzShadowPackets_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
