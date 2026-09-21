#include "xz_rhi.h"

#include <string.h>

typedef struct {
    int begin_calls;
    int submit_calls;
    int end_calls;
    int shutdown_calls;
} XzRhiSelfTestMirror;

static int XzRhiSelfTestBegin(
    void *user,
    uint64_t frame_index)
{
    XzRhiSelfTestMirror *mirror =
        (XzRhiSelfTestMirror *)user;
    (void)frame_index;
    mirror->begin_calls++;
    return 1;
}

static int XzRhiSelfTestSubmit(
    void *user,
    const XzRenderPlan *plan)
{
    XzRhiSelfTestMirror *mirror =
        (XzRhiSelfTestMirror *)user;
    mirror->submit_calls++;
    return plan && plan->packet_count == 1u;
}

static int XzRhiSelfTestEnd(void *user)
{
    XzRhiSelfTestMirror *mirror =
        (XzRhiSelfTestMirror *)user;
    mirror->end_calls++;
    return 1;
}

static void XzRhiSelfTestShutdown(void *user)
{
    XzRhiSelfTestMirror *mirror =
        (XzRhiSelfTestMirror *)user;
    mirror->shutdown_calls++;
}

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

int XzRhi_AttachMirror(
    XzRhiState *state,
    XzRhiBackend backend,
    const XzRhiMirrorDriver *driver)
{
    if (!state || !state->initialized ||
        !driver || !driver->submit_plan)
        return 0;

    state->mirror_backend = backend;
    state->mirror_driver = *driver;
    state->mirror_attached = 1;
    return 1;
}

void XzRhi_DetachMirror(XzRhiState *state)
{
    if (!state)
        return;

    memset(
        &state->mirror_driver,
        0,
        sizeof(state->mirror_driver));
    state->mirror_attached = 0;
    state->mirror_backend = XZ_RHI_BACKEND_NULL;
}

void XzRhi_BeginFrame(XzRhiState *state)
{
    if (!state || !state->initialized)
        return;

    state->frame_index++;
    state->last_packet_count = 0u;
    state->last_light_count = 0u;
    state->last_plan_hash = 0u;

    if (state->mirror_attached &&
        state->mirror_driver.begin_frame) {
        if (!state->mirror_driver.begin_frame(
                state->mirror_driver.user,
                state->frame_index))
            state->mirror_begin_failures++;
    }
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

    if (state->mirror_attached) {
        int mirror_ok;

        state->mirror_submit_attempts++;
        mirror_ok = state->mirror_driver.submit_plan(
            state->mirror_driver.user,
            plan);

        if (mirror_ok)
            state->mirror_submitted_frames++;
        else
            state->mirror_failures++;
    }

    /*
     * The active backend remains NULL in shadow mode. Mirror backends are
     * validation/execution sidecars owned by XzRHI, never by AndroidRuntime.
     */
    return state->mirror_failures == 0u;
}

void XzRhi_EndFrame(XzRhiState *state)
{
    if (!state || !state->initialized)
        return;

    if (state->mirror_attached &&
        state->mirror_driver.end_frame) {
        if (!state->mirror_driver.end_frame(
                state->mirror_driver.user))
            state->mirror_end_failures++;
    }
}

void XzRhi_Shutdown(XzRhiState *state)
{
    if (!state)
        return;

    if (state->mirror_attached &&
        state->mirror_driver.shutdown)
        state->mirror_driver.shutdown(
            state->mirror_driver.user);

    XzRhi_DetachMirror(state);
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
    XzRhiMirrorDriver mirror_driver;
    XzRhiSelfTestMirror mirror_state;

    memset(&frame, 0, sizeof(frame));
    memset(&budget, 0, sizeof(budget));
    memset(&mirror_driver, 0, sizeof(mirror_driver));
    memset(&mirror_state, 0, sizeof(mirror_state));

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

    mirror_driver.user = &mirror_state;
    mirror_driver.begin_frame = XzRhiSelfTestBegin;
    mirror_driver.submit_plan = XzRhiSelfTestSubmit;
    mirror_driver.end_frame = XzRhiSelfTestEnd;
    mirror_driver.shutdown = XzRhiSelfTestShutdown;

    if (!XzRhi_AttachMirror(
            &rhi,
            XZ_RHI_BACKEND_GLES3,
            &mirror_driver))
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
    if (!rhi.mirror_attached ||
        rhi.mirror_backend != XZ_RHI_BACKEND_GLES3)
        return 0;
    if (rhi.mirror_submit_attempts != 1u ||
        rhi.mirror_submitted_frames != 1u ||
        rhi.mirror_failures != 0u)
        return 0;
    if (mirror_state.begin_calls != 1 ||
        mirror_state.submit_calls != 1 ||
        mirror_state.end_calls != 1)
        return 0;

    XzRhi_Shutdown(&rhi);

    if (mirror_state.shutdown_calls != 1)
        return 0;
    if (rhi.mirror_attached)
        return 0;

    return 1;
}
