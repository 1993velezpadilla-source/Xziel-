#ifndef XZ_ANDROID_RUNTIME_H
#define XZ_ANDROID_RUNTIME_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    XZ_CPU_STAGE_UPDATE = 0,
    XZ_CPU_STAGE_RENDER,
    XZ_CPU_STAGE_AUDIO,
    XZ_CPU_STAGE_COUNT
} XzCpuStage;

void XzAndroidRuntime_Init(size_t engine_heap_bytes);
void XzAndroidRuntime_BeginFrame(double now_seconds);
void XzAndroidRuntime_EndFrame(double now_seconds);
void XzAndroidRuntime_BeginStage(XzCpuStage stage, double now_seconds);
void XzAndroidRuntime_EndStage(XzCpuStage stage, double now_seconds);
void XzAndroidRuntime_Shutdown(void);

#ifdef __cplusplus
}
#endif

#endif
