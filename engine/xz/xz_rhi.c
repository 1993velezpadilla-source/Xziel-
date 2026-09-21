#include "xz_rhi.h"

#include <string.h>

static XzRhiBackend XzRhiResolveBackend(
    XzRhiBackend requested,
    const XzDeviceCaps *caps,
    int shadow_mode)
{
    if (shadow_mode)
        return XZ_RHI_BACKEND_NULL;

    if (!caps)
        return XZ_RHI_BACKEND_LEGACY_GL;

    switch (requested) {
    case XZ_RHI_BACKEND_VULKAN:
        return caps->allow_vulkan
            ? XZ_RHI_BACKEND_VULKAN
            : (caps->allow_gles3
                ? XZ_RHI_BACKEND_GLES3
                : XZ_RHI_BACKEND_LEGACY_GL);

    case XZ_RHI_BACKEND_GLES3:
        return caps->allow_gles3
            ? XZ_RHI_BACKEND_GLES3
            : XZ_RHI_BACKEND_LEGACY_GL;

    case XZ_RHI_BACKEND_LEGACY_GL:
        return XZ_RHI_BACKEND_LEGACY_GL;

    case XZ_RHI_BACKEND_NULL:
    default:
        return XZ_RHI_BACKEND_NULL;
    }
}

void XzRhi_Init(
    XzRhiState *state,
    XzRhiBackend requested_backend,
    const XzDeviceCaps *caps,
    int shadow_mode)
{
    if (!state)
        return;

    memset(state, 0, sizeof(*state));
    state->requested_backend = requested_backend;
    state->shadow_mode = shadow_mode ? 1 : 0;
    state->active_backend =
        XzRhiResolveBackend(
            requested_backend,
            caps,
            state->shadow_mode);
    state->initialized = 1;
}

void XzRhi_BeginFrame(XzRhiState *state)
{
    if (!state || !state->initialized)
        return;

    state->frame_index++;
    state->last_packet_count = 0u;
    state->last_light_count = 0u;
    state->last_plan_hash = 0u;
}

int XzRhi_SubmitPlan(
    XzRhiState *state,
    const XzRenderPlan *plan)
{
    if (!state || !state->initialized || !plan)
        return 0;

    if (!XzRenderPlan_Validate(plan)) {
        state->rejected_plans++;
        return 0;
    }

    state->submitted_frames++;
    state->submitted_packets += plan->packet_count;
    state->last_packet_count = plan->packet_count;
    state->last_light_count = plan->admitted_lights;
    state->last_plan_hash = plan->content_hash;

    /*
     * Phase 3 intentionally does not issue GPU commands. The Null backend
     * validates exactly the data boundary that GLES3/Vulkan will consume.
     * The legacy renderer continues drawing the actual frame.
     */
    return 1;
}

void XzRhi_EndFrame(XzRhiState *state)
{
    (void)state;
}

void XzRhi_Shutdown(XzRhiState *state)
{
    if (!state)
        return;
    state->initialized = 0;
}

const char *XzRhiBackend_Name(XzRhiBackend backend)
{
    switch (backend) {
    case XZ_RHI_BACKEND_NULL: return "NULL";
    case XZ_RHI_BACKEND_LEGACY_GL: return "LEGACY_GL";
    case XZ_RHI_BACKEND_GLES3: return "GLES3";
    case XZ_RHI_BACKEND_VULKAN: return "VULKAN";
    default: return "UNKNOWN";
    }
}

int XzRhi_SelfTest(void)
{
    XzDeviceCaps caps;
    XzPresentFrame frame;
    XzSceneBudget budget;
    XzRenderPlan plan;
    XzRhiState rhi;

    memset(&frame, 0, sizeof(frame));
    memset(&budget, 0, sizeof(budget));

    XzDeviceCaps_Init(&caps);
    XzDeviceCaps_SetPlatform(
        &caps,
        8,
        8192,
        120,
        35,
        (3 << 16) | 2,
        1);

    frame.generation = 1u;
    frame.source_frame = 5;
    frame.entity_count = 1u;
    frame.alias_count = 1u;
    frame.entities[0].source_id = 7u;
    frame.entities[0].asset_hash = 99u;
    frame.entities[0].kind = XZ_PRESENT_ALIAS;
    frame.entities[0].priority_class = 3u;
    frame.entities[0].distance_sq = 100.0f;

    budget.full_animation_budget = 1u;
    budget.shadowed_entity_budget = 1u;
    budget.premium_vfx_budget = 1u;

    XzRenderPlan_Build(
        &plan,
        &frame,
        &budget,
        XZ_DEVICE_HIGH);

    XzRhi_Init(
        &rhi,
        XZ_RHI_BACKEND_GLES3,
        &caps,
        1);

    if (rhi.active_backend != XZ_RHI_BACKEND_NULL)
        return 0;

    XzRhi_BeginFrame(&rhi);
    if (!XzRhi_SubmitPlan(&rhi, &plan))
        return 0;
    XzRhi_EndFrame(&rhi);

    if (rhi.submitted_frames != 1u)
        return 0;
    if (rhi.submitted_packets != 1u)
        return 0;
    if (rhi.last_plan_hash != plan.content_hash)
        return 0;
    if (rhi.rejected_plans != 0u)
        return 0;

    return 1;
}
