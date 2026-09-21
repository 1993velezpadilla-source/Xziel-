#ifndef XZ_GLES3_SHADOW_H
#define XZ_GLES3_SHADOW_H

#include "xz_render_plan.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int initialized;
    int available;
    int last_restore_ok;

    uint64_t attempted_frames;
    uint64_t rendered_frames;
    uint64_t draw_calls;
    uint64_t submitted_instances;
    uint64_t restore_failures;
    uint64_t gl_failures;

    unsigned int last_instance_count;
    unsigned int last_gl_error;
    uint32_t last_plan_hash;
    uint32_t last_pixel_hash;
    unsigned int last_pixel_spread;

    int surface_width;
    int surface_height;
} XzGles3ShadowStats;

int XzGles3Shadow_Init(XzGles3ShadowStats *stats);
int XzGles3Shadow_RenderPlan(
    XzGles3ShadowStats *stats,
    const XzRenderPlan *plan);
void XzGles3Shadow_Shutdown(
    XzGles3ShadowStats *stats);

#ifdef __cplusplus
}
#endif

#endif
