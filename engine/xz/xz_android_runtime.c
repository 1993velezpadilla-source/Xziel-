#include "xz_android_runtime.h"
#include "xz_phase0.h"
#include "xz_present_world.h"

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
    XzFrameMetrics stage[XZ_CPU_STAGE_COUNT];
    XzMemoryBudget memory;
    XzPerformanceGovernor governor;
    int initialized;
    int cpu_cores;
    int system_ram_mb;
    int refresh_hz;
    int android_api;
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

static void XzLogSnapshot(double now_seconds)
{
    const XzGovernorRecommendation *rec =
        &xz_runtime.governor.recommendation;
    const XzPresentFrame *present =
        XzPresentWorld_GetReadFrame();
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
        " stage_p95(update=%.2f render=%.2f audio=%.2f)"
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
        xz_runtime.stage[XZ_CPU_STAGE_UPDATE].p95_ms,
        xz_runtime.stage[XZ_CPU_STAGE_RENDER].p95_ms,
        xz_runtime.stage[XZ_CPU_STAGE_AUDIO].p95_ms,
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
    xz_runtime.android_api = api[0] ? atoi(api) : 0;

    XzFrameMetrics_Init(&xz_runtime.frame);
    XzFrameMetrics_Init(&xz_runtime.stage[XZ_CPU_STAGE_UPDATE]);
    XzFrameMetrics_Init(&xz_runtime.stage[XZ_CPU_STAGE_RENDER]);
    XzFrameMetrics_Init(&xz_runtime.stage[XZ_CPU_STAGE_AUDIO]);
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
}

void XzAndroidRuntime_BeginFrame(double now_seconds)
{
    if (!xz_runtime.initialized)
        return;
    XzFrameMetrics_Begin(&xz_runtime.frame, now_seconds);
}

void XzAndroidRuntime_EndStage(XzCpuStage stage, double now_seconds)
{
    if (!xz_runtime.initialized)
        return;
    if (stage < 0 || stage >= XZ_CPU_STAGE_COUNT)
        return;

    XzFrameMetrics_End(&xz_runtime.stage[stage], now_seconds);
}

void XzAndroidRuntime_BeginStage(XzCpuStage stage, double now_seconds)
{
    if (!xz_runtime.initialized)
        return;
    if (stage < 0 || stage >= XZ_CPU_STAGE_COUNT)
        return;

    XzFrameMetrics_Begin(&xz_runtime.stage[stage], now_seconds);
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
