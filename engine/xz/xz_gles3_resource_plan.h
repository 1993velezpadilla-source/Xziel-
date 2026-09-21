#ifndef XZ_GLES3_RESOURCE_PLAN_H
#define XZ_GLES3_RESOURCE_PLAN_H

#include "xz_gpu_resources.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    XZ_G3_RESOURCE_INVALID = 0,
    XZ_G3_RESOURCE_TEXTURE_2D,
    XZ_G3_RESOURCE_DEPTH_TEXTURE,
    XZ_G3_RESOURCE_EXTERNAL_SURFACE
} XzGles3ResourceKind;

typedef struct {
    XzGles3ResourceKind kind;
    uint32_t logical_format;
    uint32_t flags;

    unsigned int logical_width;
    unsigned int logical_height;
    unsigned int physical_width;
    unsigned int physical_height;
    unsigned int samples;

    unsigned int bytes_per_pixel;
    uint64_t logical_bytes;
    uint64_t physical_bytes;
} XzGles3ResourceSpec;

int XzGles3ResourcePlan_Build(
    const XzGpuResourceDesc *desc,
    unsigned int max_shadow_dimension,
    XzGles3ResourceSpec *spec);

int XzGles3ResourcePlan_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
