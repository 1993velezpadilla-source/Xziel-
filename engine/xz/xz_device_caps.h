#ifndef XZ_DEVICE_CAPS_H
#define XZ_DEVICE_CAPS_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    XZ_DEVICE_COMPAT = 0,
    XZ_DEVICE_LOW,
    XZ_DEVICE_MID,
    XZ_DEVICE_HIGH,
    XZ_DEVICE_ULTRA
} XzDeviceTier;

typedef struct {
    int cpu_cores;
    int system_ram_mb;
    int refresh_hz;
    int android_api;

    int platform_gles_major;
    int platform_gles_minor;
    int runtime_gl_major;
    int runtime_gl_minor;

    int vulkan_hint;
    int has_vao;
    int has_discard_framebuffer;
    int has_half_float_color;
    int has_timer_query;

    int allow_gles3;
    int allow_vulkan;
    int allow_gpu_driven;
    int allow_temporal_upscale;
    int allow_high_refresh;
    int allow_ray_query;

    XzDeviceTier tier;
} XzDeviceCaps;

void XzDeviceCaps_Init(XzDeviceCaps *caps);
void XzDeviceCaps_SetPlatform(
    XzDeviceCaps *caps,
    int cpu_cores,
    int system_ram_mb,
    int refresh_hz,
    int android_api,
    int packed_gles_version,
    int vulkan_hint);
void XzDeviceCaps_SetRuntimeGl(
    XzDeviceCaps *caps,
    int gl_major,
    int gl_minor,
    int has_vao,
    int has_discard_framebuffer,
    int has_half_float_color,
    int has_timer_query);
void XzDeviceCaps_Reclassify(XzDeviceCaps *caps);

const char *XzDeviceTier_Name(XzDeviceTier tier);
int XzDeviceCaps_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
