#include "xz_cutover.h"

#include <string.h>

static uint32_t XzCutoverCapabilityMask(
    const XzCutoverEvidence *evidence)
{
    uint32_t mask = 0u;

    if (!evidence)
        return 0u;

    if (evidence->backend_healthy)
        mask |= XZ_CUTOVER_CAP_BACKEND_HEALTH;
    if (evidence->commands_healthy)
        mask |= XZ_CUTOVER_CAP_COMMAND_HEALTH;
    if (evidence->graph_healthy)
        mask |= XZ_CUTOVER_CAP_GRAPH_HEALTH;
    if (evidence->residency_healthy)
        mask |= XZ_CUTOVER_CAP_RESIDENCY;
    if (evidence->active_quality_healthy)
        mask |= XZ_CUTOVER_CAP_ACTIVE_QUALITY;

    if (evidence->real_geometry_ready)
        mask |= XZ_CUTOVER_CAP_REAL_GEOMETRY;
    if (evidence->real_textures_ready)
        mask |= XZ_CUTOVER_CAP_REAL_TEXTURES;
    if (evidence->visible_present_ready)
        mask |= XZ_CUTOVER_CAP_VISIBLE_PRESENT;

    return mask;
}

void XzCutover_Init(
    XzCutoverState *state)
{
    if (!state)
        return;

    memset(state, 0, sizeof(*state));
    state->requested_mode =
        XZ_CUTOVER_MODE_MIRROR;
    state->active_mode =
        XZ_CUTOVER_MODE_LEGACY;
    state->blocker_mask =
        XZ_CUTOVER_PARITY_MASK;
}

void XzCutover_RequestMode(
    XzCutoverState *state,
    XzCutoverMode mode)
{
    if (!state)
        return;

    if (mode < XZ_CUTOVER_MODE_LEGACY ||
        mode > XZ_CUTOVER_MODE_MODERN)
        mode = XZ_CUTOVER_MODE_LEGACY;

    state->requested_mode = mode;
}

void XzCutover_Evaluate(
    XzCutoverState *state,
    const XzCutoverEvidence *evidence)
{
    XzCutoverMode next_mode;
    uint32_t mask;

    if (!state || !evidence)
        return;

    mask = XzCutoverCapabilityMask(evidence);

    state->capability_mask = mask;
    state->blocker_mask =
        XZ_CUTOVER_PARITY_MASK & ~mask;

    state->candidate_ready =
        (mask & XZ_CUTOVER_OPERATIONAL_MASK) ==
            XZ_CUTOVER_OPERATIONAL_MASK &&
        evidence->healthy_frames >= 1u;

    state->cutover_allowed =
        state->candidate_ready &&
        (mask & XZ_CUTOVER_PARITY_MASK) ==
            XZ_CUTOVER_PARITY_MASK;

    if (state->requested_mode ==
        XZ_CUTOVER_MODE_LEGACY) {
        next_mode = XZ_CUTOVER_MODE_LEGACY;
    } else if (state->requested_mode ==
               XZ_CUTOVER_MODE_MIRROR) {
        next_mode = state->candidate_ready
            ? XZ_CUTOVER_MODE_MIRROR
            : XZ_CUTOVER_MODE_LEGACY;
    } else {
        if (state->cutover_allowed)
            next_mode = XZ_CUTOVER_MODE_MODERN;
        else if (state->candidate_ready)
            next_mode = XZ_CUTOVER_MODE_MIRROR;
        else
            next_mode = XZ_CUTOVER_MODE_LEGACY;

        if (!state->cutover_allowed)
            state->blocked_modern_evaluations++;
    }

    if (next_mode != state->active_mode) {
        state->active_mode = next_mode;
        state->mode_changes++;
    }

    state->last_healthy_frames =
        evidence->healthy_frames;
    state->evaluations++;
}

const char *XzCutoverMode_Name(
    XzCutoverMode mode)
{
    switch (mode) {
    case XZ_CUTOVER_MODE_LEGACY:
        return "LEGACY";
    case XZ_CUTOVER_MODE_MIRROR:
        return "MIRROR";
    case XZ_CUTOVER_MODE_MODERN:
        return "MODERN";
    default:
        return "UNKNOWN";
    }
}

int XzCutover_SelfTest(void)
{
    XzCutoverState state;
    XzCutoverEvidence evidence;

    XzCutover_Init(&state);
    XzCutover_RequestMode(
        &state,
        XZ_CUTOVER_MODE_MODERN);

    memset(&evidence, 0, sizeof(evidence));
    evidence.backend_healthy = 1;
    evidence.commands_healthy = 1;
    evidence.graph_healthy = 1;
    evidence.residency_healthy = 1;
    evidence.active_quality_healthy = 1;
    evidence.healthy_frames = 120u;

    XzCutover_Evaluate(
        &state,
        &evidence);

    if (!state.candidate_ready ||
        state.cutover_allowed ||
        state.active_mode !=
            XZ_CUTOVER_MODE_MIRROR)
        return 0;

    if (state.blocker_mask !=
        (XZ_CUTOVER_CAP_REAL_GEOMETRY |
         XZ_CUTOVER_CAP_REAL_TEXTURES |
         XZ_CUTOVER_CAP_VISIBLE_PRESENT))
        return 0;

    evidence.real_geometry_ready = 1;
    evidence.real_textures_ready = 1;

    XzCutover_Evaluate(
        &state,
        &evidence);

    if (state.cutover_allowed ||
        state.active_mode !=
            XZ_CUTOVER_MODE_MIRROR ||
        state.blocker_mask !=
            XZ_CUTOVER_CAP_VISIBLE_PRESENT)
        return 0;

    evidence.visible_present_ready = 1;

    XzCutover_Evaluate(
        &state,
        &evidence);

    if (!state.cutover_allowed ||
        state.active_mode !=
            XZ_CUTOVER_MODE_MODERN ||
        state.blocker_mask != 0u)
        return 0;

    return 1;
}
