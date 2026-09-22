#include "xz_rhi.h"
#include "xz_command_stream.h"

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
    const XzRhiSubmission *submission)
{
    XzRhiSelfTestMirror *mirror =
        (XzRhiSelfTestMirror *)user;
    mirror->submit_calls++;

    return submission &&
           submission->plan &&
           submission->plan->packet_count == 1u &&
           submission->commands &&
           submission->commands->count == 2u &&
           submission->resources != NULL &&
           submission->geometry != NULL;
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
    state->last_command_hash = 0u;

    if (state->mirror_attached &&
        state->mirror_driver.begin_frame) {
        if (!state->mirror_driver.begin_frame(
                state->mirror_driver.user,
                state->frame_index))
            state->mirror_begin_failures++;
    }
}

static int XzRhiCommandsLookValid(
    const XzCommandStream *commands)
{
    if (!commands ||
        commands->count < 2u ||
        commands->count > XZ_COMMAND_MAX ||
        commands->overflow_count != 0u ||
        commands->content_hash == 0u)
        return 0;

    if (commands->commands[0].op !=
            XZ_CMD_BEGIN_FRAME ||
        commands->commands[
            commands->count - 1u].op !=
            XZ_CMD_END_FRAME)
        return 0;

    return 1;
}

int XzRhi_SubmitFrame(
    XzRhiState *state,
    const XzRenderPlan *plan,
    const XzCommandStream *commands,
    XzGpuResourcePool *resources,
    const XzGeometryFrame *geometry)
{
    XzRhiSubmission submission;

    if (!state || !state->initialized || !plan)
        return 0;

    if (!XzRenderPlan_Validate(plan)) {
        state->rejected_plans++;
        return 0;
    }

    if (!XzRhiCommandsLookValid(commands)) {
        state->rejected_commands++;
        return 0;
    }

    submission.plan = plan;
    submission.commands = commands;
    submission.resources = resources;
    submission.geometry = geometry;

    state->submitted_frames++;
    state->submitted_packets += plan->packet_count;
    state->submitted_command_streams++;
    state->last_packet_count = plan->packet_count;
    state->last_light_count = plan->admitted_lights;
    state->last_plan_hash = plan->content_hash;
    state->last_command_hash = commands->content_hash;

    if (state->mirror_attached) {
        int mirror_ok;

        state->mirror_submit_attempts++;
        mirror_ok = state->mirror_driver.submit_plan(
            state->mirror_driver.user,
            &submission);

        if (mirror_ok)
            state->mirror_submitted_frames++;
        else
            state->mirror_failures++;
    }

    return state->mirror_failures == 0u;
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
     * Compatibility path for callers that have not yet adopted Phase 9.
     * Mirror execution intentionally requires XzRhi_SubmitFrame so a backend
     * can never silently bypass the command stream.
     */
    return state->mirror_attached ? 0 : 1;
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
    XzCommandStream commands;
    XzGpuResourcePool resources;
    static const uint64_t geometry_token = 1u;
    const XzGeometryFrame *geometry =
        (const XzGeometryFrame *)(const void *)&geometry_token;
    XzRhiMirrorDriver mirror_driver;
    XzRhiSelfTestMirror mirror_state;

    memset(&frame, 0, sizeof(frame));
    memset(&budget, 0, sizeof(budget));
    memset(&commands, 0, sizeof(commands));
    XzGpuResourcePool_Init(&resources);
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

    commands.count = 2u;
    commands.content_hash = 0x5aa55aa5u;
    commands.commands[0].op = XZ_CMD_BEGIN_FRAME;
    commands.commands[1].op = XZ_CMD_END_FRAME;

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
    if (!XzRhi_SubmitFrame(
            &rhi,
            &plan,
            &commands,
            &resources,
            geometry))
        return 0;
    XzRhi_EndFrame(&rhi);

    if (rhi.submitted_frames != 1u)
        return 0;
    if (rhi.submitted_packets != 1u)
        return 0;
    if (rhi.last_plan_hash != plan.content_hash)
        return 0;
    if (rhi.rejected_plans != 0u ||
        rhi.rejected_commands != 0u)
        return 0;
    if (rhi.submitted_command_streams != 1u ||
        rhi.last_command_hash != commands.content_hash)
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
