#ifndef XZ_PASS_INPUTS_H
#define XZ_PASS_INPUTS_H

#include "xz_command_stream.h"
#include "xz_gpu_resources.h"

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_PASS_INPUT_MAX XZ_RG_MAX_PASSES
#define XZ_PASS_INPUTS_PER_PASS 4u

typedef struct {
    unsigned int pass_index;
    XzGpuHandle handles[XZ_PASS_INPUTS_PER_PASS];
    XzGpuResourceType types[XZ_PASS_INPUTS_PER_PASS];
    unsigned int count;
} XzPassInput;

typedef struct {
    XzPassInput passes[XZ_PASS_INPUT_MAX];
    unsigned int count;
    unsigned int total_inputs;
    unsigned int max_inputs_per_pass;
    unsigned int invalid_resource_count;
    unsigned int overflow_count;
    unsigned int external_read_count;
} XzPassInputPlan;

int XzPassInputPlan_Build(
    XzPassInputPlan *plan,
    const XzCommandStream *commands,
    XzGpuResourcePool *resources);

int XzPassInputPlan_Validate(
    const XzPassInputPlan *plan);

const XzPassInput *XzPassInputPlan_Find(
    const XzPassInputPlan *plan,
    unsigned int pass_index);

int XzPassInputPlan_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
