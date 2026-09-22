#include "xz_device_caps.h"

#include <string.h>

static int XzMaxInt(int a, int b)
{
    return a > b ? a : b;
}

static int XzGlesAtLeast(
    const XzDeviceCaps *caps,
    int major,
    int minor)
{
    if (caps->platform_gles_major > major)
        return 1;
    if (caps->platform_gles_major < major)
        return 0;
    return caps->platform_gles_minor >= minor;
}

void XzDeviceCaps_Init(XzDeviceCaps *caps)
{
    if (!caps)
        return;

    memset(caps, 0, sizeof(*caps));
    caps->tier = XZ_DEVICE_COMPAT;
}

void XzDeviceCaps_SetPlatform(
    XzDeviceCaps *caps,
    int cpu_cores,
    int system_ram_mb,
    int refresh_hz,
    int android_api,
    int packed_gles_version,
    int vulkan_hint)
{
    if (!caps)
        return;

    caps->cpu_cores = cpu_cores > 0 ? cpu_cores : 1;
    caps->system_ram_mb = system_ram_mb > 0 ? system_ram_mb : 2048;
    caps->refresh_hz = refresh_hz > 0 ? refresh_hz : 60;
    caps->android_api = android_api > 0 ? android_api : 23;

    if (packed_gles_version > 0) {
        caps->platform_gles_major =
            (packed_gles_version >> 16) & 0xffff;
        caps->platform_gles_minor =
            packed_gles_version & 0xffff;
    }

    caps->vulkan_hint = vulkan_hint ? 1 : 0;
    XzDeviceCaps_Reclassify(caps);
}

void XzDeviceCaps_SetRuntimeGl(
    XzDeviceCaps *caps,
    int gl_major,
    int gl_minor,
    int has_vao,
    int has_discard_framebuffer,
    int has_half_float_color,
    int has_timer_query)
{
    if (!caps)
        return;

    caps->runtime_gl_major = gl_major;
    caps->runtime_gl_minor = gl_minor;
    caps->has_vao = has_vao ? 1 : 0;
    caps->has_discard_framebuffer =
        has_discard_framebuffer ? 1 : 0;
    caps->has_half_float_color =
        has_half_float_color ? 1 : 0;
    caps->has_timer_query = has_timer_query ? 1 : 0;

    if (caps->platform_gles_major == 0 && gl_major > 0) {
        caps->platform_gles_major = gl_major;
        caps->platform_gles_minor = gl_minor;
    }

    XzDeviceCaps_Reclassify(caps);
}

void XzDeviceCaps_Reclassify(XzDeviceCaps *caps)
{
    int score = 0;
    int effective_cores;

    if (!caps)
        return;

    effective_cores = XzMaxInt(caps->cpu_cores, 1);

    caps->allow_gles3 = XzGlesAtLeast(caps, 3, 0);
    caps->allow_vulkan =
        caps->android_api >= 24 && caps->vulkan_hint;
    caps->allow_high_refresh =
        caps->refresh_hz >= 90;
    caps->allow_temporal_upscale =
        caps->allow_gles3 &&
        caps->system_ram_mb >= 4096;
    caps->allow_gpu_driven =
        caps->allow_vulkan &&
        XzGlesAtLeast(caps, 3, 1) &&
        caps->system_ram_mb >= 6144 &&
        effective_cores >= 6;

    /*
     * Phase 2 never enables RT. Vulkan Ray Query needs explicit extension and
     * driver validation in the future Vulkan backend, not a marketing/model
     * guess here.
     */
    caps->allow_ray_query = 0;

    if (caps->system_ram_mb >= 3072)
        score++;
    if (caps->system_ram_mb >= 4096)
        score++;
    if (caps->system_ram_mb >= 6144)
        score++;
    if (caps->system_ram_mb >= 8192)
        score++;

    if (effective_cores >= 4)
        score++;
    if (effective_cores >= 6)
        score++;
    if (effective_cores >= 8)
        score++;

    if (XzGlesAtLeast(caps, 3, 0))
        score += 2;
    if (XzGlesAtLeast(caps, 3, 1))
        score++;
    if (caps->allow_vulkan)
        score++;
    if (caps->refresh_hz >= 90)
        score++;

    if (!caps->allow_gles3 || caps->system_ram_mb < 3072) {
        caps->tier = XZ_DEVICE_COMPAT;
    } else if (score <= 4) {
        caps->tier = XZ_DEVICE_LOW;
    } else if (score <= 7) {
        caps->tier = XZ_DEVICE_MID;
    } else if (score <= 10) {
        caps->tier = XZ_DEVICE_HIGH;
    } else {
        caps->tier = XZ_DEVICE_ULTRA;
    }
}

const char *XzDeviceTier_Name(XzDeviceTier tier)
{
    switch (tier) {
    case XZ_DEVICE_COMPAT: return "COMPAT";
    case XZ_DEVICE_LOW: return "LOW";
    case XZ_DEVICE_MID: return "MID";
    case XZ_DEVICE_HIGH: return "HIGH";
    case XZ_DEVICE_ULTRA: return "ULTRA";
    default: return "UNKNOWN";
    }
}

int XzDeviceCaps_SelfTest(void)
{
    XzDeviceCaps caps;

    XzDeviceCaps_Init(&caps);
    XzDeviceCaps_SetPlatform(
        &caps,
        2,
        2048,
        60,
        23,
        (2 << 16),
        0);

    if (caps.tier != XZ_DEVICE_COMPAT)
        return 0;
    if (caps.allow_gles3 || caps.allow_vulkan)
        return 0;

    XzDeviceCaps_Init(&caps);
    XzDeviceCaps_SetPlatform(
        &caps,
        8,
        8192,
        120,
        35,
        (3 << 16) | 2,
        1);
    XzDeviceCaps_SetRuntimeGl(
        &caps, 2, 0, 1, 1, 1, 1);

    if (caps.tier != XZ_DEVICE_ULTRA)
        return 0;
    if (!caps.allow_gles3 ||
        !caps.allow_vulkan ||
        !caps.allow_gpu_driven ||
        !caps.allow_temporal_upscale ||
        !caps.allow_high_refresh)
        return 0;
    if (caps.allow_ray_query)
        return 0;

    return 1;
}
