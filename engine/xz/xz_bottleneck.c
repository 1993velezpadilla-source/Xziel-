#include "xz_bottleneck.h"

#include <math.h>
#include <string.h>

#define XZ_BOTTLENECK_WARMUP_FRAMES 120ull
#define XZ_BOTTLENECK_MIN_TOTAL_MS 0.10
#define XZ_BOTTLENECK_MIN_SHARE 0.50f
#define XZ_BOTTLENECK_MIN_RATIO 1.35f

static double XzPositive(double value)
{
    return value > 0.0 ? value : 0.0;
}

static float XzSafeShare(double value, double total)
{
    if (total <= 0.0)
        return 0.0f;
    return (float)(value / total);
}

XzBottleneckAnalysis XzBottleneck_Analyze(
    unsigned long long accepted_frames,
    double update_p95_ms,
    double render_p95_ms,
    double audio_p95_ms)
{
    XzBottleneckAnalysis result;
    double values[3];
    double total;
    double largest;
    double second;
    int largest_index;
    int i;

    memset(&result, 0, sizeof(result));
    result.kind = XZ_BOTTLENECK_UNKNOWN;

    if (accepted_frames < XZ_BOTTLENECK_WARMUP_FRAMES)
        return result;

    values[0] = XzPositive(update_p95_ms);
    values[1] = XzPositive(render_p95_ms);
    values[2] = XzPositive(audio_p95_ms);

    total = values[0] + values[1] + values[2];
    result.measured_total_ms = (float)total;

    if (total < XZ_BOTTLENECK_MIN_TOTAL_MS)
        return result;

    result.update_share = XzSafeShare(values[0], total);
    result.render_share = XzSafeShare(values[1], total);
    result.audio_share = XzSafeShare(values[2], total);

    largest = values[0];
    second = 0.0;
    largest_index = 0;

    for (i = 1; i < 3; ++i) {
        if (values[i] > largest) {
            second = largest;
            largest = values[i];
            largest_index = i;
        } else if (values[i] > second) {
            second = values[i];
        }
    }

    if (second <= 0.0001)
        result.dominant_ratio = largest > 0.0 ? 999.0f : 0.0f;
    else
        result.dominant_ratio = (float)(largest / second);

    if (largest / total < XZ_BOTTLENECK_MIN_SHARE ||
        result.dominant_ratio < XZ_BOTTLENECK_MIN_RATIO) {
        result.kind = XZ_BOTTLENECK_BALANCED;
        return result;
    }

    switch (largest_index) {
    case 0:
        result.kind = XZ_BOTTLENECK_UPDATE;
        break;
    case 1:
        result.kind = XZ_BOTTLENECK_RENDER;
        break;
    case 2:
        result.kind = XZ_BOTTLENECK_AUDIO;
        break;
    default:
        result.kind = XZ_BOTTLENECK_UNKNOWN;
        break;
    }

    return result;
}

const char *XzBottleneck_Name(XzBottleneckKind kind)
{
    switch (kind) {
    case XZ_BOTTLENECK_UNKNOWN: return "UNKNOWN";
    case XZ_BOTTLENECK_BALANCED: return "BALANCED";
    case XZ_BOTTLENECK_UPDATE: return "UPDATE_BOUND";
    case XZ_BOTTLENECK_RENDER: return "RENDER_BOUND";
    case XZ_BOTTLENECK_AUDIO: return "AUDIO_BOUND";
    default: return "INVALID";
    }
}

int XzBottleneck_SelfTest(void)
{
    XzBottleneckAnalysis a;

    a = XzBottleneck_Analyze(119ull, 3.0, 20.0, 1.0);
    if (a.kind != XZ_BOTTLENECK_UNKNOWN)
        return 0;

    a = XzBottleneck_Analyze(120ull, 3.0, 20.0, 0.1);
    if (a.kind != XZ_BOTTLENECK_RENDER)
        return 0;

    a = XzBottleneck_Analyze(120ull, 20.0, 3.0, 0.1);
    if (a.kind != XZ_BOTTLENECK_UPDATE)
        return 0;

    a = XzBottleneck_Analyze(120ull, 1.0, 1.0, 8.0);
    if (a.kind != XZ_BOTTLENECK_AUDIO)
        return 0;

    a = XzBottleneck_Analyze(120ull, 8.0, 7.0, 1.0);
    if (a.kind != XZ_BOTTLENECK_BALANCED)
        return 0;

    if (fabs(a.update_share + a.render_share + a.audio_share - 1.0f) > 0.001f)
        return 0;

    return 1;
}
