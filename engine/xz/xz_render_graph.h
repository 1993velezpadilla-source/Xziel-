#ifndef XZ_RENDER_GRAPH_H
#define XZ_RENDER_GRAPH_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_RG_MAX_RESOURCES 32u
#define XZ_RG_MAX_PASSES 32u
#define XZ_RG_INVALID_INDEX 0xffffffffu

typedef enum {
    XZ_RG_FORMAT_UNKNOWN = 0,
    XZ_RG_FORMAT_RGBA8,
    XZ_RG_FORMAT_RGBA16F,
    XZ_RG_FORMAT_RG16F,
    XZ_RG_FORMAT_DEPTH16,
    XZ_RG_FORMAT_DEPTH24
} XzRgFormat;

enum {
    XZ_RG_RESOURCE_IMPORTED      = 1u << 0,
    XZ_RG_RESOURCE_TRANSIENT     = 1u << 1,
    XZ_RG_RESOURCE_TILE_LOCAL    = 1u << 2,
    XZ_RG_RESOURCE_MEMORYLESS    = 1u << 3,
    XZ_RG_RESOURCE_PRESERVE      = 1u << 4
};

enum {
    XZ_RG_PASS_CURRENT_PIXEL_ONLY = 1u << 0,
    XZ_RG_PASS_NEEDS_NEIGHBORHOOD = 1u << 1,
    XZ_RG_PASS_NEEDS_HISTORY      = 1u << 2,
    XZ_RG_PASS_FRAMEBUFFER_FETCH  = 1u << 3,
    XZ_RG_PASS_CAN_FUSE_PREVIOUS  = 1u << 4
};

typedef enum {
    XZ_RG_OK = 0,
    XZ_RG_ERROR_TOO_MANY_RESOURCES,
    XZ_RG_ERROR_TOO_MANY_PASSES,
    XZ_RG_ERROR_INVALID_MASK,
    XZ_RG_ERROR_READ_BEFORE_WRITE,
    XZ_RG_ERROR_CYCLE
} XzRgError;

typedef struct {
    uint32_t name_hash;
    unsigned int width;
    unsigned int height;
    unsigned int samples;
    XzRgFormat format;
    uint32_t flags;
} XzRgResourceDesc;

typedef struct {
    uint32_t name_hash;
    uint32_t read_mask;
    uint32_t write_mask;
    uint32_t flags;
} XzRgPassDesc;

typedef struct {
    XzRgResourceDesc resources[XZ_RG_MAX_RESOURCES];
    XzRgPassDesc passes[XZ_RG_MAX_PASSES];
    unsigned int resource_count;
    unsigned int pass_count;
} XzRenderGraph;

typedef struct {
    int valid;
    XzRgError error;

    unsigned int resource_count;
    unsigned int pass_count;
    unsigned int execution_order[XZ_RG_MAX_PASSES];

    int first_use[XZ_RG_MAX_RESOURCES];
    int last_use[XZ_RG_MAX_RESOURCES];
    int alias_slot[XZ_RG_MAX_RESOURCES];

    unsigned int alias_slot_count;
    unsigned int peak_live_transient_slots;
    unsigned int tile_local_resource_count;
    unsigned int memoryless_resource_count;

    unsigned int fusion_group[XZ_RG_MAX_PASSES];
    unsigned int fusion_group_count;
    unsigned int fused_pass_count;
} XzRenderGraphCompiled;

void XzRenderGraph_Init(XzRenderGraph *graph);

int XzRenderGraph_AddResource(
    XzRenderGraph *graph,
    const XzRgResourceDesc *desc);

int XzRenderGraph_AddPass(
    XzRenderGraph *graph,
    const XzRgPassDesc *desc);

int XzRenderGraph_Compile(
    const XzRenderGraph *graph,
    XzRenderGraphCompiled *compiled);

const char *XzRgError_Name(XzRgError error);
int XzRenderGraph_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
