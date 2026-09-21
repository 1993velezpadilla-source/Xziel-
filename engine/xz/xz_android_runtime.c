#include "xz_android_runtime.h"
#include "xz_phase0.h"
#include "xz_present_world.h"
#include "xz_device_caps.h"
#include "xz_scene_budget.h"
#include "xz_render_plan.h"
#include "xz_rhi.h"
#include "xz_gles3_probe.h"
#include "xz_render_graph.h"
#include "xz_gles3_shadow.h"
#include "xz_gpu_resources.h"
#include "xz_command_stream.h"
#include "xz_gles3_resource_plan.h"
#include "xz_pass_targets.h"
#include "xz_pass_inputs.h"

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
    XzRenderPlan render_plan;
    XzRhiState rhi;
    XzGles3ProbeResult gles3_probe;
    XzRenderGraph render_graph;
    XzRenderGraphCompiled render_graph_compiled;
    XzGles3ShadowState gles3_shadow;
    XzGpuResourcePool gpu_resources;
    XzGpuHandle graph_resource_handles[XZ_RG_MAX_RESOURCES];
    XzCommandStream command_stream;
    uint64_t command_encode_failures;
    int graph_resources_ready;
    int initialized;
    int cpu_cores;
    int system_ram_mb;
    int refresh_hz;
    int display_width;
    int display_height;
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

static int XzGles3MirrorBegin(
    void *user,
    uint64_t frame_index)
{
    (void)user;
    (void)frame_index;
    return 1;
}

static int XzGles3MirrorSubmit(
    void *user,
    const XzRhiSubmission *submission)
{
    if (!submission)
        return 0;

    return XzGles3Shadow_SubmitCommands(
        (XzGles3ShadowState *)user,
        submission->commands,
        submission->plan,
        submission->resources);
}

static int XzGles3MirrorEnd(void *user)
{
    (void)user;
    return 1;
}

static void XzGles3MirrorShutdown(void *user)
{
    XzGles3Shadow_Shutdown(
        (XzGles3ShadowState *)user);
}

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
    xz_runtime.display_width = 0;
    xz_runtime.display_height = 0;

    if (SDL_GetNumVideoDisplays() > 0 &&
        SDL_GetCurrentDisplayMode(0, &mode) == 0) {
        xz_runtime.refresh_hz = mode.refresh_rate;
        xz_runtime.display_width = mode.w;
        xz_runtime.display_height = mode.h;
    }
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

static int XzBuildBootstrapRenderGraph(void)
{
    XzRgResourceDesc resource;
    XzRgPassDesc pass;
    int scene_color;
    int depth;
    int lit;
    int post;
    int swapchain;
    unsigned int width =
        xz_runtime.display_width > 0
            ? (unsigned int)xz_runtime.display_width : 1280u;
    unsigned int height =
        xz_runtime.display_height > 0
            ? (unsigned int)xz_runtime.display_height : 720u;
    XzRgFormat color_format =
        xz_runtime.caps.has_half_float_color
            ? XZ_RG_FORMAT_RGBA16F
            : XZ_RG_FORMAT_RGBA8;

    XzRenderGraph_Init(&xz_runtime.render_graph);

    memset(&resource, 0, sizeof(resource));
    resource.width = width;
    resource.height = height;
    resource.samples = 1u;
    resource.format = color_format;
    resource.flags =
        XZ_RG_RESOURCE_TRANSIENT |
        XZ_RG_RESOURCE_TILE_LOCAL;
    scene_color = XzRenderGraph_AddResource(
        &xz_runtime.render_graph, &resource);

    resource.format = XZ_RG_FORMAT_DEPTH24;
    resource.flags =
        XZ_RG_RESOURCE_TRANSIENT |
        XZ_RG_RESOURCE_TILE_LOCAL |
        XZ_RG_RESOURCE_MEMORYLESS;
    depth = XzRenderGraph_AddResource(
        &xz_runtime.render_graph, &resource);

    resource.format = color_format;
    resource.flags =
        XZ_RG_RESOURCE_TRANSIENT |
        XZ_RG_RESOURCE_TILE_LOCAL;
    lit = XzRenderGraph_AddResource(
        &xz_runtime.render_graph, &resource);
    post = XzRenderGraph_AddResource(
        &xz_runtime.render_graph, &resource);

    resource.format = XZ_RG_FORMAT_RGBA8;
    resource.flags =
        XZ_RG_RESOURCE_IMPORTED |
        XZ_RG_RESOURCE_PRESERVE;
    swapchain = XzRenderGraph_AddResource(
        &xz_runtime.render_graph, &resource);

    if (scene_color < 0 || depth < 0 || lit < 0 ||
        post < 0 || swapchain < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.write_mask =
        (1u << (unsigned int)scene_color) |
        (1u << (unsigned int)depth);
    if (XzRenderGraph_AddPass(
            &xz_runtime.render_graph, &pass) < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.read_mask =
        (1u << (unsigned int)scene_color) |
        (1u << (unsigned int)depth);
    pass.write_mask = 1u << (unsigned int)lit;
    if (XzRenderGraph_AddPass(
            &xz_runtime.render_graph, &pass) < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.read_mask = 1u << (unsigned int)lit;
    pass.write_mask = 1u << (unsigned int)post;
    if (XzRenderGraph_AddPass(
            &xz_runtime.render_graph, &pass) < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.read_mask = 1u << (unsigned int)post;
    pass.write_mask = 1u << (unsigned int)swapchain;
    if (XzRenderGraph_AddPass(
            &xz_runtime.render_graph, &pass) < 0)
        return 0;

    return XzRenderGraph_Compile(
        &xz_runtime.render_graph,
        &xz_runtime.render_graph_compiled);
}

static uint64_t XzGraphResourceSizeBytes(
    const XzRgResourceDesc *resource)
{
    uint64_t bytes_per_pixel = 4u;

    if (!resource)
        return 0u;

    switch (resource->format) {
    case XZ_RG_FORMAT_RGBA16F:
        bytes_per_pixel = 8u;
        break;
    case XZ_RG_FORMAT_RG16F:
        bytes_per_pixel = 4u;
        break;
    case XZ_RG_FORMAT_DEPTH16:
        bytes_per_pixel = 2u;
        break;
    case XZ_RG_FORMAT_DEPTH24:
        bytes_per_pixel = 4u;
        break;
    case XZ_RG_FORMAT_RGBA8:
    case XZ_RG_FORMAT_UNKNOWN:
    default:
        bytes_per_pixel = 4u;
        break;
    }

    return (uint64_t)resource->width *
           (uint64_t)resource->height *
           (uint64_t)(resource->samples ?
               resource->samples : 1u) *
           bytes_per_pixel;
}

static XzGpuResourceType XzGraphResourceType(
    const XzRgResourceDesc *resource)
{
    if (!resource)
        return XZ_GPU_RESOURCE_UNKNOWN;

    if (resource->flags & XZ_RG_RESOURCE_IMPORTED)
        return XZ_GPU_RESOURCE_EXTERNAL_SURFACE;

    if (resource->format == XZ_RG_FORMAT_DEPTH16 ||
        resource->format == XZ_RG_FORMAT_DEPTH24)
        return XZ_GPU_RESOURCE_DEPTH;

    return XZ_GPU_RESOURCE_TEXTURE;
}

static int XzInitGraphResourceHandles(void)
{
    unsigned int i;

    memset(
        xz_runtime.graph_resource_handles,
        0,
        sizeof(xz_runtime.graph_resource_handles));

    XzGpuResourcePool_Init(
        &xz_runtime.gpu_resources);

    for (i = 0u;
         i < xz_runtime.render_graph.resource_count;
         ++i) {
        const XzRgResourceDesc *source =
            &xz_runtime.render_graph.resources[i];
        XzGpuResourceDesc desc;
        XzGpuHandle handle;

        memset(&desc, 0, sizeof(desc));
        desc.type = XzGraphResourceType(source);
        desc.format = (uint32_t)source->format;
        desc.flags = source->flags;
        desc.width = source->width;
        desc.height = source->height;
        desc.samples = source->samples ?
            source->samples : 1u;
        desc.size_bytes =
            XzGraphResourceSizeBytes(source);

        handle = XzGpuResource_Create(
            &xz_runtime.gpu_resources,
            &desc);

        if (handle == XZ_GPU_INVALID_HANDLE)
            return 0;

        xz_runtime.graph_resource_handles[i] =
            handle;
    }

    xz_runtime.graph_resources_ready = 1;
    return 1;
}

static void XzDestroyGraphResourceHandles(void)
{
    unsigned int i;

    for (i = 0u;
         i < xz_runtime.render_graph.resource_count;
         ++i) {
        XzGpuHandle handle =
            xz_runtime.graph_resource_handles[i];

        if (handle != XZ_GPU_INVALID_HANDLE)
            XzGpuResource_Destroy(
                &xz_runtime.gpu_resources,
                handle);

        xz_runtime.graph_resource_handles[i] =
            XZ_GPU_INVALID_HANDLE;
    }

    xz_runtime.graph_resources_ready = 0;
}

static void XzLogSnapshot(double now_seconds)
{
    const XzGovernorRecommendation *rec =
        &xz_runtime.governor.recommendation;
    const XzPresentFrame *present =
        XzPresentWorld_GetReadFrame();
    const XzSceneBudget *scene =
        &xz_runtime.scene_budget;
    const XzRenderPlan *plan =
        &xz_runtime.render_plan;
    const XzRhiState *rhi =
        &xz_runtime.rhi;
    const XzGles3ShadowState *g3 =
        &xz_runtime.gles3_shadow;
    const XzGpuResourcePool *gpu =
        &xz_runtime.gpu_resources;
    const XzCommandStream *commands =
        &xz_runtime.command_stream;
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
        " plan(gen=%" PRIu64 " packets=%u lod=%u/%u/%u anim=%u shadow=%u vfx=%u hash=%08x)"
        " rhi(active=%s shadow=%d submitted=%" PRIu64
        " cmdStreams=%" PRIu64 " rejected=%" PRIu64
        " rejectedCmd=%" PRIu64 " cmdHash=%08x)"
        " mirror(backend=%s attached=%d attempts=%" PRIu64
        " submitted=%" PRIu64 " fail=%" PRIu64
        " beginFail=%" PRIu64 " endFail=%" PRIu64 ")"
        " g3shadow(submitted=%" PRIu64 " packets=%" PRIu64
        " draws=%" PRIu64 " fail=%" PRIu64 " readback=%" PRIu64
        " restoreFail=%" PRIu64 " restore=%d glerr=0x%x hash=%08x)"
        " g3diag(stage=%u preerr=%" PRIu64 ")"
        " g3cmd(streams=%" PRIu64 " commands=%" PRIu64
        " passes=%" PRIu64 " reads=%" PRIu64 " writes=%" PRIu64
        " draws=%" PRIu64 " fail=%" PRIu64 " hash=%08x)"
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
        plan->generation,
        plan->packet_count,
        plan->near_count,
        plan->mid_count,
        plan->far_count,
        plan->full_animation_count,
        plan->shadow_count,
        plan->premium_vfx_count,
        plan->content_hash,
        XzRhiBackend_Name(rhi->active_backend),
        rhi->shadow_mode,
        rhi->submitted_frames,
        rhi->submitted_command_streams,
        rhi->rejected_plans,
        rhi->rejected_commands,
        rhi->last_command_hash,
        XzRhiBackend_Name(rhi->mirror_backend),
        rhi->mirror_attached,
        rhi->mirror_submit_attempts,
        rhi->mirror_submitted_frames,
        rhi->mirror_failures,
        rhi->mirror_begin_failures,
        rhi->mirror_end_failures,
        g3->submitted_frames,
        g3->submitted_packets,
        g3->draw_calls,
        g3->failures,
        g3->readback_failures,
        g3->restore_failures,
        g3->restore_ok,
        g3->last_gl_error,
        g3->last_plan_hash,
        g3->last_error_stage,
        g3->preexisting_errors,
        g3->command_stream_submissions,
        g3->commands_executed,
        g3->passes_executed,
        g3->resource_read_commands,
        g3->resource_write_commands,
        g3->draw_commands,
        g3->command_failures,
        g3->last_command_hash,
        rec->render_scale,
        rec->animation_rate_scale,
        rec->shadow_budget_scale,
        rec->vfx_budget_scale,
        rec->light_budget_scale,
        rec->streaming_aggression);

    /*
     * Keep graph/resource telemetry on a dedicated short logcat record.
     * Android truncates oversized records; splitting this preserves stable
     * machine-readable gates as Xz telemetry grows.
     */
    XzAndroidLog(
        ANDROID_LOG_INFO,
        "graphio g3res(mapped=%u objects=%u create=%" PRIu64
        " reuse=%" PRIu64 " destroy=%" PRIu64
        " read=%" PRIu64 " write=%" PRIu64
        " fail=%" PRIu64 " bytes=%" PRIu64 ")"
        " g3fbo(bind=%" PRIu64 " check=%" PRIu64
        " fail=%" PRIu64 " external=%" PRIu64
        " color=%" PRIu64 " depth=%" PRIu64
        " targetFail=%" PRIu64 ")"
        " g3sample(passes=%" PRIu64 " draws=%" PRIu64
        " inputs=%" PRIu64 " fail=%" PRIu64 " max=%u)"
        " cmd(count=%u hash=%08x overflow=%u resources=%u high=%u"
        " stale=%" PRIu64 " encodeFail=%" PRIu64 ")",
        g3->physical_alive,
        g3->physical_gl_objects,
        g3->physical_creates,
        g3->physical_reuses,
        g3->physical_destroys,
        g3->physical_read_binds,
        g3->physical_write_binds,
        g3->physical_failures,
        g3->physical_bytes,
        g3->framebuffer_binds,
        g3->framebuffer_checks,
        g3->framebuffer_failures,
        g3->framebuffer_external_passes,
        g3->framebuffer_color_attachments,
        g3->framebuffer_depth_attachments,
        g3->target_plan_failures,
        g3->sampled_passes,
        g3->sampled_draws,
        g3->sampled_input_binds,
        g3->sampled_failures,
        g3->sampled_max_inputs,
        commands->count,
        commands->content_hash,
        commands->overflow_count,
        gpu->alive_count,
        gpu->high_water_count,
        gpu->stale_resolves,
        xz_runtime.command_encode_failures);

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

    XzRhi_Init(
        &xz_runtime.rhi,
        XZ_RHI_BACKEND_GLES3,
        &xz_runtime.caps,
        1);

    XzAndroidLog(
        ANDROID_LOG_INFO,
        "phase3 renderplan=%s rhi=%s requested=%s active=%s shadow=%d",
        XzRenderPlan_SelfTest() ? "PASS" : "FAIL",
        XzRhi_SelfTest() ? "PASS" : "FAIL",
        XzRhiBackend_Name(xz_runtime.rhi.requested_backend),
        XzRhiBackend_Name(xz_runtime.rhi.active_backend),
        xz_runtime.rhi.shadow_mode);

    XzGles3Probe_InitResult(&xz_runtime.gles3_probe);
    if (xz_runtime.caps.allow_gles3) {
        int probe_ok =
            XzGles3Probe_Run(&xz_runtime.gles3_probe);
        XzAndroidLog(
            probe_ok ? ANDROID_LOG_INFO : ANDROID_LOG_WARN,
            "phase4 gles3_probe=%s status=%s egl=%d.%d gl=%d.%d"
            " shader_compile=%d shader_link=%d restore=%d err=0x%x"
            " vendor='%s' renderer='%s' version='%s'",
            probe_ok ? "PASS" : "FAIL",
            XzGles3ProbeStatus_Name(
                xz_runtime.gles3_probe.status),
            xz_runtime.gles3_probe.egl_major,
            xz_runtime.gles3_probe.egl_minor,
            xz_runtime.gles3_probe.gl_major,
            xz_runtime.gles3_probe.gl_minor,
            xz_runtime.gles3_probe.shader_compile_ok,
            xz_runtime.gles3_probe.shader_link_ok,
            xz_runtime.gles3_probe.restore_ok,
            xz_runtime.gles3_probe.gl_error,
            xz_runtime.gles3_probe.vendor,
            xz_runtime.gles3_probe.renderer,
            xz_runtime.gles3_probe.version);
    } else {
        XzAndroidLog(
            ANDROID_LOG_INFO,
            "phase4 gles3_probe=SKIP status=UNAVAILABLE restore=1");
    }

    {
        int graph_ok = XzBuildBootstrapRenderGraph();
        const XzRenderGraphCompiled *compiled =
            &xz_runtime.render_graph_compiled;
        int resources_ok = 0;

        XzAndroidLog(
            graph_ok ? ANDROID_LOG_INFO : ANDROID_LOG_WARN,
            "phase5 rendergraph selftest=%s compile=%s error=%s"
            " resources=%u passes=%u alias=%u peak=%u tile=%u"
            " memoryless=%u fusion_groups=%u fused=%u size=%dx%d",
            XzRenderGraph_SelfTest() ? "PASS" : "FAIL",
            graph_ok ? "PASS" : "FAIL",
            XzRgError_Name(compiled->error),
            compiled->resource_count,
            compiled->pass_count,
            compiled->alias_slot_count,
            compiled->peak_live_transient_slots,
            compiled->tile_local_resource_count,
            compiled->memoryless_resource_count,
            compiled->fusion_group_count,
            compiled->fused_pass_count,
            xz_runtime.display_width,
            xz_runtime.display_height);

        if (graph_ok)
            resources_ok =
                XzInitGraphResourceHandles();

        XzAndroidLog(
            resources_ok ? ANDROID_LOG_INFO : ANDROID_LOG_WARN,
            "phase8 resource_cmd resources_selftest=%s commands_selftest=%s"
            " init=%s alive=%u high=%u",
            XzGpuResourcePool_SelfTest() ? "PASS" : "FAIL",
            XzCommandStream_SelfTest() ? "PASS" : "FAIL",
            resources_ok ? "PASS" : "FAIL",
            xz_runtime.gpu_resources.alive_count,
            xz_runtime.gpu_resources.high_water_count);
    }

    XzGles3Shadow_InitState(&xz_runtime.gles3_shadow);
    if (xz_runtime.caps.allow_gles3 &&
        xz_runtime.gles3_probe.status ==
            XZ_GLES3_PROBE_SHADER_OK) {
        int shadow_ok = XzGles3Shadow_Init(
            &xz_runtime.gles3_shadow,
            8u);

        XzAndroidLog(
            shadow_ok ? ANDROID_LOG_INFO : ANDROID_LOG_WARN,
            "phase6 gles3shadow init=%s available=%d shader=%d"
            " restore=%d stride=%u",
            shadow_ok ? "PASS" : "FAIL",
            xz_runtime.gles3_shadow.available,
            xz_runtime.gles3_shadow.shader_ok,
            xz_runtime.gles3_shadow.restore_ok,
            xz_runtime.gles3_shadow.submit_stride);

        if (shadow_ok) {
            XzRhiMirrorDriver mirror;
            int attach_ok;

            memset(&mirror, 0, sizeof(mirror));
            mirror.user = &xz_runtime.gles3_shadow;
            mirror.begin_frame = XzGles3MirrorBegin;
            mirror.submit_plan = XzGles3MirrorSubmit;
            mirror.end_frame = XzGles3MirrorEnd;
            mirror.shutdown = XzGles3MirrorShutdown;

            attach_ok = XzRhi_AttachMirror(
                &xz_runtime.rhi,
                XZ_RHI_BACKEND_GLES3,
                &mirror);

            XzAndroidLog(
                attach_ok ? ANDROID_LOG_INFO : ANDROID_LOG_WARN,
                "phase7 rhi_mirror attach=%s backend=%s",
                attach_ok ? "PASS" : "FAIL",
                XzRhiBackend_Name(
                    xz_runtime.rhi.mirror_backend));

            XzAndroidLog(
                (attach_ok &&
                 xz_runtime.graph_resources_ready)
                    ? ANDROID_LOG_INFO
                    : ANDROID_LOG_WARN,
                "phase9 command_executor init=%s submit=COMMAND_STREAM"
                " backend=%s resources=%d",
                (attach_ok &&
                 xz_runtime.graph_resources_ready)
                    ? "PASS" : "FAIL",
                XzRhiBackend_Name(
                    xz_runtime.rhi.mirror_backend),
                xz_runtime.graph_resources_ready);

            XzAndroidLog(
                XzGles3ResourcePlan_SelfTest()
                    ? ANDROID_LOG_INFO
                    : ANDROID_LOG_WARN,
                "phase10 gles3_resources planner=%s proxyMax=%u",
                XzGles3ResourcePlan_SelfTest()
                    ? "PASS" : "FAIL",
                128u);

            XzAndroidLog(
                XzPassTargetPlan_SelfTest()
                    ? ANDROID_LOG_INFO
                    : ANDROID_LOG_WARN,
                "phase11 pass_targets planner=%s",
                XzPassTargetPlan_SelfTest()
                    ? "PASS" : "FAIL");

            XzAndroidLog(
                XzPassInputPlan_SelfTest()
                    ? ANDROID_LOG_INFO
                    : ANDROID_LOG_WARN,
                "phase12 pass_inputs planner=%s sampledDepth=TEXTURE",
                XzPassInputPlan_SelfTest()
                    ? "PASS" : "FAIL");

            if (!attach_ok)
                XzGles3Shadow_Shutdown(
                    &xz_runtime.gles3_shadow);
        }
    } else {
        XzAndroidLog(
            ANDROID_LOG_INFO,
            "phase6 gles3shadow init=SKIP available=0 shader=0"
            " restore=1 stride=0");
    }
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

    XzRenderPlan_Build(
        &xz_runtime.render_plan,
        XzPresentWorld_GetReadFrame(),
        &xz_runtime.scene_budget,
        xz_runtime.caps.tier);

    if (xz_runtime.graph_resources_ready) {
        if (!XzCommandStream_EncodeFrame(
                &xz_runtime.command_stream,
                &xz_runtime.render_graph,
                &xz_runtime.render_graph_compiled,
                &xz_runtime.gpu_resources,
                xz_runtime.graph_resource_handles,
                &xz_runtime.render_plan))
            xz_runtime.command_encode_failures++;
    }

    XzRhi_BeginFrame(&xz_runtime.rhi);
    XzRhi_SubmitFrame(
        &xz_runtime.rhi,
        &xz_runtime.render_plan,
        &xz_runtime.command_stream,
        &xz_runtime.gpu_resources);
    XzRhi_EndFrame(&xz_runtime.rhi);

    if (xz_runtime.last_log_seconds == 0.0 ||
        now_seconds - xz_runtime.last_log_seconds >= 5.0)
        XzLogSnapshot(now_seconds);
}

void XzAndroidRuntime_Shutdown(void)
{
    if (!xz_runtime.initialized)
        return;

    XzLogSnapshot(xz_runtime.last_log_seconds + 5.0);
    XzRhi_Shutdown(&xz_runtime.rhi);
    XzDestroyGraphResourceHandles();
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
