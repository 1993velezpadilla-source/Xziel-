#include "xz_android_runtime.h"
#include "xz_phase0.h"
#include "xz_present_world.h"
#include "xz_device_caps.h"
#include "xz_scene_budget.h"

#include <SDL.h>

#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __ANDROID__
#include <android/log.h>
#include <sys/system_properties.h>
#endif

#define XZ_MIB (1024ull * 1024ull)

typedef struct {
    XzFrameMetrics frame;
    XzMemoryBudget memory;
    XzPerformanceGovernor governor;
    XzDeviceCaps caps;
    XzSceneBudget scene_budget;
    int initialized;
    int cpu_cores;
    int system_ram_mb;
    int refresh_hz;
    int android_api;
    int packed_gles_version;
    size_t engine_heap_bytes;
    uint64_t last_memory_sample_frame;
    double last_log_seconds;
    char board_platform[PROP_VALUE_MAX];
    char egl_driver[PROP_VALUE_MAX];
    char vulkan_driver[PROP_VALUE_MAX];
    char device_model[PROP_VALUE_MAX];
} XzAndroidRuntimeState;

static XzAndroidRuntimeState xz_runtime;

static uint64_t XzClampU64(uint64_t value, uint64_t lo, uint64_t hi)
{
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

#ifdef __ANDROID__
static void XzAndroidLog(
    android_LogPriority priority,
    const char *format,
    ...)
{
    va_list args;
    va_start(args, format);
    __android_log_vprint(priority, "XZIEL-XZ", format, args);
    va_end(args);
}

static void XzReadProperty(
    const char *name,
    char *output,
    size_t output_size)
{
    char temp[PROP_VALUE_MAX];
    int length;

    if (!output || !output_size)
        return;

    output[0] = '\0';
    temp[0] = '\0';
    length = __system_property_get(name, temp);
    if (length <= 0)
        return;

    snprintf(output, output_size, "%s", temp);
}
#else
static void XzAndroidLog(int priority, const char *format, ...)
{
    va_list args;
    (void)priority;
    va_start(args, format);
    vfprintf(stderr, format, args);
    fputc('\n', stderr);
    va_end(args);
}

static void XzReadProperty(
    const char *name,
    char *output,
    size_t output_size)
{
    (void)name;
    if (output && output_size)
        output[0] = '\0';
}
#define ANDROID_LOG_INFO 4
#define ANDROID_LOG_WARN 5
#endif

static uint64_t XzReadProcessRssBytes(void)
{
    FILE *file;
    char line[256];
    uint64_t kb = 0;

    file = fopen("/proc/self/status", "rb");
    if (!file)
        return 0;

    while (fgets(line, sizeof(line), file)) {
        if (sscanf(line, "VmRSS: %" SCNu64 " kB", &kb) == 1) {
            fclose(file);
            return kb * 1024ull;
        }
    }

    fclose(file);
    return 0;
}

static void XzChooseMemoryBudget(
    int system_ram_mb,
    uint64_t *soft_bytes,
    uint64_t *hard_bytes)
{
    uint64_t total;
    uint64_t soft;
    uint64_t hard;

    if (system_ram_mb <= 0)
        system_ram_mb = 4096;

    total = (uint64_t)system_ram_mb * XZ_MIB;
    soft = (uint64_t)((double)total * 0.18);
    hard = (uint64_t)((double)total * 0.26);

    soft = XzClampU64(soft, 256ull * XZ_MIB, 1024ull * XZ_MIB);
    hard = XzClampU64(hard, 384ull * XZ_MIB, 1536ull * XZ_MIB);
    if (hard <= soft)
        hard = soft + 128ull * XZ_MIB;

    *soft_bytes = soft;
    *hard_bytes = hard;
}

static void XzDetectDisplay(void)
{
    SDL_DisplayMode mode;

    memset(&mode, 0, sizeof(mode));
    xz_runtime.refresh_hz = 0;

    if (SDL_GetNumVideoDisplays() > 0 &&
        SDL_GetCurrentDisplayMode(0, &mode) == 0)
        xz_runtime.refresh_hz = mode.refresh_rate;
}

static void XzDetectRuntimeGlCaps(void)
{
    int major = 0;
    int minor = 0;

    if (SDL_GL_GetCurrentContext() != NULL) {
        SDL_GL_GetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, &major);
        SDL_GL_GetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, &minor);
    }

    XzDeviceCaps_SetRuntimeGl(
        &xz_runtime.caps,
        major,
        minor,
        SDL_GL_ExtensionSupported("GL_OES_vertex_array_object"),
        SDL_GL_ExtensionSupported("GL_EXT_discard_framebuffer"),
        SDL_GL_ExtensionSupported("GL_EXT_color_buffer_half_float") ||
            SDL_GL_ExtensionSupported("GL_EXT_color_buffer_float"),
        SDL_GL_ExtensionSupported("GL_EXT_disjoint_timer_query"));
}

static void XzLogSnapshot(double now_seconds)
{
    const XzGovernorRecommendation *rec =
        &xz_runtime.governor.recommendation;
    const XzPresentFrame *present =
        XzPresentWorld_GetReadFrame();
    const XzSceneBudget *scene =
        &xz_runtime.scene_budget;
    const uint64_t present_generation =
        present ? present->generation : 0u;
    const unsigned int present_entities =
        present ? present->entity_count : 0u;
    const unsigned int present_alias =
        present ? present->alias_count : 0u;
    const unsigned int present_brush =
        present ? present->brush_count : 0u;
    const unsigned int present_sprite =
        present ? present->sprite_count : 0u;
    const unsigned int present_static =
        present ? present->static_brush_count : 0u;
    const unsigned int present_lights =
        present ? present->active_light_count : 0u;
    const unsigned int present_dropped =
        present ? present->dropped_entities : 0u;

    XzAndroidLog(
        ANDROID_LOG_INFO,
        "perf processed_frames=%" PRIu64
        " last=%.2fms avg=%.2f p50=%.2f p95=%.2f p99=%.2f max=%.2f"
        " rss=%.1fMiB high=%.1fMiB state=%s passive=%d"
        " present_gen=%" PRIu64
        " present=%u alias=%u brush=%u sprite=%u static=%u lights=%u dropped=%u"
        " budget(near=%u mid=%u far=%u crit=%u imp=%u bg=%u"
        " anim=%u shadow=%u vfx=%u light=%u/%u)"
        " advice(render=%.2f anim=%.2f shadow=%.2f vfx=%.2f light=%.2f stream=%.2f)",
        xz_runtime.frame.total_frames,
        xz_runtime.frame.last_ms,
        xz_runtime.frame.average_ms,
        xz_runtime.frame.p50_ms,
        xz_runtime.frame.p95_ms,
        xz_runtime.frame.p99_ms,
        xz_runtime.frame.max_ms,
        (double)xz_runtime.memory.current_bytes / (double)XZ_MIB,
        (double)xz_runtime.memory.high_water_bytes / (double)XZ_MIB,
        XzGovernorState_Name(xz_runtime.governor.state),
        xz_runtime.governor.passive,
        present_generation,
        present_entities,
        present_alias,
        present_brush,
        present_sprite,
        present_static,
        present_lights,
        present_dropped,
        scene->near_entities,
        scene->mid_entities,
        scene->far_entities,
        scene->critical_entities,
        scene->important_entities,
        scene->background_entities,
        scene->full_animation_budget,
        scene->shadowed_entity_budget,
        scene->premium_vfx_budget,
        scene->admitted_lights,
        scene->dynamic_light_budget,
        rec->render_scale,
        rec->animation_rate_scale,
        rec->shadow_budget_scale,
        rec->vfx_budget_scale,
        rec->light_budget_scale,
        rec->streaming_aggression);

    xz_runtime.last_log_seconds = now_seconds;
}

void XzAndroidRuntime_Init(size_t engine_heap_bytes)
{
    uint64_t soft_bytes;
    uint64_t hard_bytes;
    char api[PROP_VALUE_MAX];
    char gles[PROP_VALUE_MAX];

    memset(&xz_runtime, 0, sizeof(xz_runtime));

    xz_runtime.cpu_cores = SDL_GetCPUCount();
    xz_runtime.system_ram_mb = SDL_GetSystemRAM();
    xz_runtime.engine_heap_bytes = engine_heap_bytes;

    XzDetectDisplay();

    XzReadProperty(
        "ro.board.platform",
        xz_runtime.board_platform,
        sizeof(xz_runtime.board_platform));
    XzReadProperty(
        "ro.hardware.egl",
        xz_runtime.egl_driver,
        sizeof(xz_runtime.egl_driver));
    XzReadProperty(
        "ro.hardware.vulkan",
        xz_runtime.vulkan_driver,
        sizeof(xz_runtime.vulkan_driver));
    XzReadProperty(
        "ro.product.model",
        xz_runtime.device_model,
        sizeof(xz_runtime.device_model));
    XzReadProperty("ro.build.version.sdk", api, sizeof(api));
    XzReadProperty("ro.opengles.version", gles, sizeof(gles));
    xz_runtime.android_api = api[0] ? atoi(api) : 0;
    xz_runtime.packed_gles_version = gles[0] ? atoi(gles) : 0;

    XzDeviceCaps_Init(&xz_runtime.caps);
    XzDeviceCaps_SetPlatform(
        &xz_runtime.caps,
        xz_runtime.cpu_cores,
        xz_runtime.system_ram_mb,
        xz_runtime.refresh_hz,
        xz_runtime.android_api,
        xz_runtime.packed_gles_version,
        xz_runtime.vulkan_driver[0] != '\0');
    XzDetectRuntimeGlCaps();

    XzFrameMetrics_Init(&xz_runtime.frame);
    XzChooseMemoryBudget(
        xz_runtime.system_ram_mb, &soft_bytes, &hard_bytes);
    XzMemoryBudget_Init(&xz_runtime.memory, soft_bytes, hard_bytes);

    /*
     * Phase 0 is deliberately advisory-only. It measures and computes quality
     * recommendations but cannot alter render scale, shadows, animation, VFX,
     * lights or streaming yet. That makes this safe to land before those
     * systems exist.
     */
    XzPerformanceGovernor_Init(
        &xz_runtime.governor, 1000.0 / 60.0, 1);

    xz_runtime.initialized = 1;

    XzAndroidLog(
        ANDROID_LOG_INFO,
        "phase0 init passive=1 selftest=%s model='%s' board='%s'"
        " egl='%s' vk='%s' sdk=%d cores=%d ram=%dMiB refresh=%dHz"
        " engine_heap=%.1fMiB mem_soft=%.1fMiB mem_hard=%.1fMiB",
        XzPhase0_SelfTest() ? "PASS" : "FAIL",
        xz_runtime.device_model[0] ? xz_runtime.device_model : "unknown",
        xz_runtime.board_platform[0] ? xz_runtime.board_platform : "unknown",
        xz_runtime.egl_driver[0] ? xz_runtime.egl_driver : "unknown",
        xz_runtime.vulkan_driver[0] ? xz_runtime.vulkan_driver : "unknown",
        xz_runtime.android_api,
        xz_runtime.cpu_cores,
        xz_runtime.system_ram_mb,
        xz_runtime.refresh_hz,
        (double)xz_runtime.engine_heap_bytes / (double)XZ_MIB,
        (double)soft_bytes / (double)XZ_MIB,
        (double)hard_bytes / (double)XZ_MIB);

    XzAndroidLog(
        ANDROID_LOG_INFO,
        "phase2 caps selftest=%s tier=%s platform_gles=%d.%d runtime_gl=%d.%d"
        " vulkan_hint=%d allow(gles3=%d vk=%d gpuDriven=%d temporal=%d highHz=%d rt=%d)"
        " ext(vao=%d discard=%d halfFloat=%d timer=%d)",
        XzDeviceCaps_SelfTest() ? "PASS" : "FAIL",
        XzDeviceTier_Name(xz_runtime.caps.tier),
        xz_runtime.caps.platform_gles_major,
        xz_runtime.caps.platform_gles_minor,
        xz_runtime.caps.runtime_gl_major,
        xz_runtime.caps.runtime_gl_minor,
        xz_runtime.caps.vulkan_hint,
        xz_runtime.caps.allow_gles3,
        xz_runtime.caps.allow_vulkan,
        xz_runtime.caps.allow_gpu_driven,
        xz_runtime.caps.allow_temporal_upscale,
        xz_runtime.caps.allow_high_refresh,
        xz_runtime.caps.allow_ray_query,
        xz_runtime.caps.has_vao,
        xz_runtime.caps.has_discard_framebuffer,
        xz_runtime.caps.has_half_float_color,
        xz_runtime.caps.has_timer_query);
}

void XzAndroidRuntime_BeginFrame(double now_seconds)
{
    if (!xz_runtime.initialized)
        return;
    XzFrameMetrics_Begin(&xz_runtime.frame, now_seconds);
}

void XzAndroidRuntime_EndFrame(double now_seconds)
{
    uint64_t rss;

    if (!xz_runtime.initialized)
        return;

    XzFrameMetrics_End(&xz_runtime.frame, now_seconds);

    if (xz_runtime.frame.total_frames -
            xz_runtime.last_memory_sample_frame >= 60u) {
        rss = XzReadProcessRssBytes();
        if (rss)
            XzMemoryBudget_Sample(&xz_runtime.memory, rss);
        xz_runtime.last_memory_sample_frame =
            xz_runtime.frame.total_frames;
    }

    XzPerformanceGovernor_Update(
        &xz_runtime.governor,
        &xz_runtime.frame,
        &xz_runtime.memory,
        -1);

    XzSceneBudget_Build(
        &xz_runtime.scene_budget,
        XzPresentWorld_GetReadFrame(),
        xz_runtime.caps.tier,
        &xz_runtime.governor.recommendation);

    if (xz_runtime.last_log_seconds == 0.0 ||
        now_seconds - xz_runtime.last_log_seconds >= 5.0)
        XzLogSnapshot(now_seconds);
}

void XzAndroidRuntime_Shutdown(void)
{
    if (!xz_runtime.initialized)
        return;

    XzLogSnapshot(xz_runtime.last_log_seconds + 5.0);
    XzAndroidLog(
        ANDROID_LOG_INFO,
        "phase0 shutdown processed_frames=%" PRIu64
        " spikes25=%" PRIu64 " spikes33=%" PRIu64
        " spikes50=%" PRIu64,
        xz_runtime.frame.total_frames,
        xz_runtime.frame.spikes_over_25ms,
        xz_runtime.frame.spikes_over_33ms,
        xz_runtime.frame.spikes_over_50ms);

    xz_runtime.initialized = 0;
}
