#ifndef XZ_RHI_H
#define XZ_RHI_H

#include "xz_device_caps.h"
#include "xz_render_plan.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    XZ_RHI_BACKEND_NULL = 0,
    XZ_RHI_BACKEND_LEGACY_GL,
    XZ_RHI_BACKEND_GLES3,
    XZ_RHI_BACKEND_VULKAN
} XzRhiBackend;

typedef struct {
    XzRhiBackend requested_backend;
    XzRhiBackend active_backend;

    int shadow_mode;
    int initialized;

    uint64_t frame_index;
    uint64_t submitted_frames;
    uint64_t submitted_packets;
    uint64_t rejected_plans;

    unsigned int last_packet_count;
    unsigned int last_light_count;
    uint32_t last_plan_hash;
} XzRhiState;

void XzRhi_Init(
    XzRhiState *state,
    XzRhiBackend requested_backend,
    const XzDeviceCaps *caps,
    int shadow_mode);

void XzRhi_BeginFrame(XzRhiState *state);
int XzRhi_SubmitPlan(
    XzRhiState *state,
    const XzRenderPlan *plan);
void XzRhi_EndFrame(XzRhiState *state);
void XzRhi_Shutdown(XzRhiState *state);

const char *XzRhiBackend_Name(XzRhiBackend backend);
int XzRhi_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
