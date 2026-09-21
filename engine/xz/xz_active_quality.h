#ifndef XZ_ACTIVE_QUALITY_H
#define XZ_ACTIVE_QUALITY_H

#include "xz_phase0.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float applied_render_scale;
    float requested_render_scale;
    unsigned int width;
    unsigned int height;
    uint64_t changes;
    uint64_t suppressed_changes;
    uint64_t last_change_frame;
    unsigned int cooldown_frames;
    int initialized;
} XzActiveQualityState;

void XzActiveQuality_Init(
    XzActiveQualityState *state,
    unsigned int display_width,
    unsigned int display_height);

int XzActiveQuality_Update(
    XzActiveQualityState *state,
    const XzGovernorRecommendation *recommendation,
    uint64_t frame_index,
    unsigned int display_width,
    unsigned int display_height);

int XzActiveQuality_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
