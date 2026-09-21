#ifndef XZ_PASS_TARGETS_H
#define XZ_PASS_TARGETS_H

#include "xz_command_stream.h"
#include "xz_gpu_resources.h"

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_PASS_TARGET_MAX XZ_RG_MAX_PASSES

typedef struct {
    unsigned int pass_index;
    XzGpuHandle color;
    XzGpuHandle depth;
    XzGpuHandle external;
    unsigned int read_count;
    unsigned int write_count;
    unsigned int draw_count;
} XzPassTarget;

typedef struct {
    XzPassTarget passes[XZ_PASS_TARGET_MAX];
    unsigned int count;
    unsigned int invalid_resource_count;
    unsigned int multiple_color_count;
    unsigned int multiple_depth_count;
    unsigned int multiple_external_count;
} XzPassTargetPlan;

int XzPassTargetPlan_Build(
    XzPassTargetPlan *plan,
    const XzCommandStream *commands,
    XzGpuResourcePool *resources);

int XzPassTargetPlan_Validate(
    const XzPassTargetPlan *plan);

int XzPassTargetPlan_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
