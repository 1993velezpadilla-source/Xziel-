#ifndef XZ_RHI_H
#define XZ_RHI_H

#include "xz_device_caps.h"
#include "xz_render_plan.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct XzCommandStream XzCommandStream;

typedef enum {
    XZ_RHI_BACKEND_NULL = 0,
    XZ_RHI_BACKEND_LEGACY_GL,
    XZ_RHI_BACKEND_GLES3,
    XZ_RHI_BACKEND_VULKAN
} XzRhiBackend;

typedef struct {
    const XzRenderPlan *plan;
    const XzCommandStream *commands;
} XzRhiSubmission;

typedef int (*XzRhiMirrorBeginFn)(
    void *user,
    uint64_t frame_index);

typedef int (*XzRhiMirrorSubmitFn)(
    void *user,
    const XzRhiSubmission *submission);

typedef int (*XzRhiMirrorEndFn)(
    void *user);

typedef void (*XzRhiMirrorShutdownFn)(
    void *user);

typedef struct {
    void *user;
    XzRhiMirrorBeginFn begin_frame;
    XzRhiMirrorSubmitFn submit_plan;
    XzRhiMirrorEndFn end_frame;
    XzRhiMirrorShutdownFn shutdown;
} XzRhiMirrorDriver;

typedef struct {
    XzRhiBackend requested_backend;
    XzRhiBackend active_backend;

    int shadow_mode;
    int initialized;

    uint64_t frame_index;
    uint64_t submitted_frames;
    uint64_t submitted_packets;
    uint64_t submitted_command_streams;
    uint64_t rejected_plans;
    uint64_t rejected_commands;

    int mirror_attached;
    XzRhiBackend mirror_backend;
    XzRhiMirrorDriver mirror_driver;
    uint64_t mirror_begin_failures;
    uint64_t mirror_submit_attempts;
    uint64_t mirror_submitted_frames;
    uint64_t mirror_failures;
    uint64_t mirror_end_failures;

    unsigned int last_packet_count;
    unsigned int last_light_count;
    uint32_t last_plan_hash;
    uint32_t last_command_hash;
} XzRhiState;

void XzRhi_Init(
    XzRhiState *state,
    XzRhiBackend requested_backend,
    const XzDeviceCaps *caps,
    int shadow_mode);

int XzRhi_AttachMirror(
    XzRhiState *state,
    XzRhiBackend backend,
    const XzRhiMirrorDriver *driver);

void XzRhi_DetachMirror(XzRhiState *state);

void XzRhi_BeginFrame(XzRhiState *state);

int XzRhi_SubmitFrame(
    XzRhiState *state,
    const XzRenderPlan *plan,
    const XzCommandStream *commands);

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
