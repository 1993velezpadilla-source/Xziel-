#include "xz_active_quality.h"

#include <string.h>

static float XzQuantizeScale(float value)
{
    if (value <= 0.825f)
        return 0.80f;
    if (value <= 0.875f)
        return 0.85f;
    if (value <= 0.95f)
        return 0.90f;
    return 1.0f;
}

static unsigned int XzScaledDimension(
    unsigned int base,
    float scale)
{
    unsigned int value;

    if (base == 0u)
        base = 1u;

    value = (unsigned int)((float)base * scale + 0.5f);

    if (value < 64u)
        value = 64u;

    /* Keep 2x2 alignment for tile-friendly render targets. */
    value &= ~1u;
    if (value == 0u)
        value = 2u;

    return value;
}

void XzActiveQuality_Init(
    XzActiveQualityState *state,
    unsigned int display_width,
    unsigned int display_height)
{
    if (!state)
        return;

    memset(state, 0, sizeof(*state));
    state->applied_render_scale = 1.0f;
    state->requested_render_scale = 1.0f;
    state->width = XzScaledDimension(
        display_width, 1.0f);
    state->height = XzScaledDimension(
        display_height, 1.0f);
    state->cooldown_frames = 30u;
    state->initialized = 1;
}

int XzActiveQuality_Update(
    XzActiveQualityState *state,
    const XzGovernorRecommendation *recommendation,
    uint64_t frame_index,
    unsigned int display_width,
    unsigned int display_height)
{
    float requested;
    unsigned int next_width;
    unsigned int next_height;

    if (!state || !recommendation)
        return 0;

    if (!state->initialized)
        XzActiveQuality_Init(
            state, display_width, display_height);

    requested =
        XzQuantizeScale(
            recommendation->render_scale);

    state->requested_render_scale = requested;

    if (requested == state->applied_render_scale)
        return 0;

    if (state->last_change_frame != 0u &&
        frame_index - state->last_change_frame <
            (uint64_t)state->cooldown_frames) {
        state->suppressed_changes++;
        return 0;
    }

    next_width =
        XzScaledDimension(display_width, requested);
    next_height =
        XzScaledDimension(display_height, requested);

    if (next_width == state->width &&
        next_height == state->height) {
        state->applied_render_scale = requested;
        return 0;
    }

    state->applied_render_scale = requested;
    state->width = next_width;
    state->height = next_height;
    state->last_change_frame = frame_index;
    state->changes++;

    return 1;
}

int XzActiveQuality_SelfTest(void)
{
    XzActiveQualityState state;
    XzGovernorRecommendation rec;

    memset(&rec, 0, sizeof(rec));
    XzActiveQuality_Init(
        &state, 2400u, 1080u);

    if (state.width != 2400u ||
        state.height != 1080u ||
        state.applied_render_scale != 1.0f)
        return 0;

    rec.render_scale = 0.85f;

    if (!XzActiveQuality_Update(
            &state,
            &rec,
            120u,
            2400u,
            1080u))
        return 0;

    if (state.applied_render_scale != 0.85f ||
        state.width != 2040u ||
        state.height != 918u ||
        state.changes != 1u)
        return 0;

    rec.render_scale = 1.0f;

    if (XzActiveQuality_Update(
            &state,
            &rec,
            130u,
            2400u,
            1080u))
        return 0;

    if (state.suppressed_changes != 1u)
        return 0;

    if (!XzActiveQuality_Update(
            &state,
            &rec,
            151u,
            2400u,
            1080u))
        return 0;

    if (state.width != 2400u ||
        state.height != 1080u ||
        state.changes != 2u)
        return 0;

    return 1;
}
