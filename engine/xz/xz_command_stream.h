#ifndef XZ_COMMAND_STREAM_H
#define XZ_COMMAND_STREAM_H

#include "xz_gpu_resources.h"
#include "xz_render_graph.h"
#include "xz_render_plan.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_COMMAND_MAX 1024u

typedef enum {
    XZ_CMD_NOP = 0,
    XZ_CMD_BEGIN_FRAME,
    XZ_CMD_BEGIN_PASS,
    XZ_CMD_RESOURCE_READ,
    XZ_CMD_RESOURCE_WRITE,
    XZ_CMD_DRAW_PACKETS,
    XZ_CMD_END_PASS,
    XZ_CMD_END_FRAME
} XzCommandOp;

typedef struct {
    XzCommandOp op;
    uint32_t a;
    uint32_t b;
    uint32_t c;
    uint32_t d;
    uint64_t value64;
} XzCommand;

typedef struct {
    XzCommand commands[XZ_COMMAND_MAX];
    unsigned int count;
    unsigned int overflow_count;
    uint32_t content_hash;
} XzCommandStream;

void XzCommandStream_Reset(
    XzCommandStream *stream);

int XzCommandStream_EncodeFrame(
    XzCommandStream *stream,
    const XzRenderGraph *graph,
    const XzRenderGraphCompiled *compiled,
    XzGpuResourcePool *resources,
    const XzGpuHandle resource_handles[XZ_RG_MAX_RESOURCES],
    const XzRenderPlan *plan);

int XzCommandStream_Validate(
    const XzCommandStream *stream);

const char *XzCommandOp_Name(
    XzCommandOp op);

int XzCommandStream_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
