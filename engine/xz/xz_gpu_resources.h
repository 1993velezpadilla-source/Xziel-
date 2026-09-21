#ifndef XZ_GPU_RESOURCES_H
#define XZ_GPU_RESOURCES_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_GPU_MAX_RESOURCES 64u
#define XZ_GPU_INVALID_HANDLE 0u

typedef uint32_t XzGpuHandle;

typedef enum {
    XZ_GPU_RESOURCE_UNKNOWN = 0,
    XZ_GPU_RESOURCE_BUFFER,
    XZ_GPU_RESOURCE_TEXTURE,
    XZ_GPU_RESOURCE_DEPTH,
    XZ_GPU_RESOURCE_EXTERNAL_SURFACE
} XzGpuResourceType;

enum {
    XZ_GPU_RESOURCE_IMPORTED   = 1u << 0,
    XZ_GPU_RESOURCE_TRANSIENT  = 1u << 1,
    XZ_GPU_RESOURCE_TILE_LOCAL = 1u << 2,
    XZ_GPU_RESOURCE_MEMORYLESS = 1u << 3,
    XZ_GPU_RESOURCE_PRESERVE   = 1u << 4
};

typedef struct {
    XzGpuResourceType type;
    uint32_t format;
    uint32_t flags;
    unsigned int width;
    unsigned int height;
    unsigned int samples;
    uint64_t size_bytes;
} XzGpuResourceDesc;

typedef struct {
    XzGpuResourceDesc desc;
    uint16_t generation;
    unsigned char alive;
} XzGpuResourceSlot;

typedef struct {
    XzGpuResourceSlot slots[XZ_GPU_MAX_RESOURCES];

    unsigned int alive_count;
    unsigned int high_water_count;

    uint64_t creates;
    uint64_t destroys;
    uint64_t resolves;
    uint64_t invalid_resolves;
    uint64_t stale_resolves;
} XzGpuResourcePool;

void XzGpuResourcePool_Init(
    XzGpuResourcePool *pool);

XzGpuHandle XzGpuResource_Create(
    XzGpuResourcePool *pool,
    const XzGpuResourceDesc *desc);

int XzGpuResource_Destroy(
    XzGpuResourcePool *pool,
    XzGpuHandle handle);

const XzGpuResourceDesc *XzGpuResource_Resolve(
    XzGpuResourcePool *pool,
    XzGpuHandle handle);

int XzGpuResource_IsAlive(
    const XzGpuResourcePool *pool,
    XzGpuHandle handle);

unsigned int XzGpuHandle_Index(
    XzGpuHandle handle);

unsigned int XzGpuHandle_Generation(
    XzGpuHandle handle);

int XzGpuResourcePool_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
