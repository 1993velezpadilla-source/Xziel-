#ifndef XZ_ANDROID_RUNTIME_H
#define XZ_ANDROID_RUNTIME_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

void XzAndroidRuntime_Init(size_t engine_heap_bytes);
void XzAndroidRuntime_BeginFrame(double now_seconds);
void XzAndroidRuntime_EndFrame(double now_seconds);
void XzAndroidRuntime_Shutdown(void);

#ifdef __cplusplus
}
#endif

#endif
