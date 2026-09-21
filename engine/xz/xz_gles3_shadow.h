#ifndef XZ_GLES3_SHADOW_H
#define XZ_GLES3_SHADOW_H

#include "xz_render_plan.h"
#include "xz_command_stream.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int initialized;
    int available;
    int shader_ok;
    int restore_ok;

    unsigned int submit_stride;

    uint64_t submit_attempts;
    uint64_t submitted_frames;
    uint64_t skipped_frames;
    uint64_t submitted_packets;
    uint64_t draw_calls;
    uint64_t failures;
    uint64_t restore_failures;
    uint64_t readback_failures;

    uint64_t command_stream_submissions;
    uint64_t commands_executed;
    uint64_t passes_executed;
    uint64_t resource_read_commands;
    uint64_t resource_write_commands;
    uint64_t draw_commands;
    uint64_t command_failures;

    unsigned int last_packet_count;
    uint32_t last_plan_hash;
    uint32_t last_command_hash;
    unsigned int last_gl_error;
    unsigned int last_error_stage;
    uint64_t preexisting_errors;

    unsigned char last_expected_rgba[4];
    unsigned char last_readback_rgba[4];
} XzGles3ShadowState;

void XzGles3Shadow_InitState(
    XzGles3ShadowState *state);

int XzGles3Shadow_Init(
    XzGles3ShadowState *state,
    unsigned int submit_stride);

int XzGles3Shadow_Submit(
    XzGles3ShadowState *state,
    const XzRenderPlan *plan);

int XzGles3Shadow_SubmitCommands(
    XzGles3ShadowState *state,
    const XzCommandStream *commands,
    const XzRenderPlan *plan,
    XzGpuResourcePool *resources);

void XzGles3Shadow_Shutdown(
    XzGles3ShadowState *state);

#ifdef __cplusplus
}
#endif

#endif
