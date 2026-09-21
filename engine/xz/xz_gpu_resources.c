#include "xz_gpu_resources.h"

#include <string.h>

#define XZ_GPU_INDEX_BITS 16u
#define XZ_GPU_INDEX_MASK 0xffffu

static XzGpuHandle XzMakeHandle(
    unsigned int index,
    unsigned int generation)
{
    return ((XzGpuHandle)generation << XZ_GPU_INDEX_BITS) |
           (XzGpuHandle)(index + 1u);
}

unsigned int XzGpuHandle_Index(
    XzGpuHandle handle)
{
    unsigned int encoded =
        (unsigned int)(handle & XZ_GPU_INDEX_MASK);

    if (encoded == 0u)
        return XZ_GPU_MAX_RESOURCES;

    return encoded - 1u;
}

unsigned int XzGpuHandle_Generation(
    XzGpuHandle handle)
{
    return (unsigned int)(handle >> XZ_GPU_INDEX_BITS);
}

void XzGpuResourcePool_Init(
    XzGpuResourcePool *pool)
{
    unsigned int i;

    if (!pool)
        return;

    memset(pool, 0, sizeof(*pool));

    for (i = 0u; i < XZ_GPU_MAX_RESOURCES; ++i)
        pool->slots[i].generation = 1u;
}

XzGpuHandle XzGpuResource_Create(
    XzGpuResourcePool *pool,
    const XzGpuResourceDesc *desc)
{
    unsigned int i;

    if (!pool || !desc)
        return XZ_GPU_INVALID_HANDLE;

    for (i = 0u; i < XZ_GPU_MAX_RESOURCES; ++i) {
        XzGpuResourceSlot *slot = &pool->slots[i];

        if (slot->alive)
            continue;

        slot->desc = *desc;
        if (slot->desc.samples == 0u)
            slot->desc.samples = 1u;
        if (slot->generation == 0u)
            slot->generation = 1u;
        slot->alive = 1u;

        pool->alive_count++;
        pool->creates++;

        if (pool->alive_count > pool->high_water_count)
            pool->high_water_count = pool->alive_count;

        return XzMakeHandle(i, slot->generation);
    }

    return XZ_GPU_INVALID_HANDLE;
}

static XzGpuResourceSlot *XzGpuResourceResolveSlot(
    XzGpuResourcePool *pool,
    XzGpuHandle handle,
    int count_stats)
{
    unsigned int index;
    unsigned int generation;
    XzGpuResourceSlot *slot;

    if (!pool || handle == XZ_GPU_INVALID_HANDLE) {
        if (pool && count_stats)
            pool->invalid_resolves++;
        return NULL;
    }

    index = XzGpuHandle_Index(handle);
    generation = XzGpuHandle_Generation(handle);

    if (index >= XZ_GPU_MAX_RESOURCES ||
        generation == 0u) {
        if (count_stats)
            pool->invalid_resolves++;
        return NULL;
    }

    slot = &pool->slots[index];

    if (!slot->alive ||
        slot->generation != generation) {
        if (count_stats)
            pool->stale_resolves++;
        return NULL;
    }

    if (count_stats)
        pool->resolves++;

    return slot;
}

const XzGpuResourceDesc *XzGpuResource_Resolve(
    XzGpuResourcePool *pool,
    XzGpuHandle handle)
{
    XzGpuResourceSlot *slot =
        XzGpuResourceResolveSlot(
            pool, handle, 1);

    return slot ? &slot->desc : NULL;
}

int XzGpuResource_IsAlive(
    const XzGpuResourcePool *pool,
    XzGpuHandle handle)
{
    unsigned int index;
    unsigned int generation;
    const XzGpuResourceSlot *slot;

    if (!pool || handle == XZ_GPU_INVALID_HANDLE)
        return 0;

    index = XzGpuHandle_Index(handle);
    generation = XzGpuHandle_Generation(handle);

    if (index >= XZ_GPU_MAX_RESOURCES ||
        generation == 0u)
        return 0;

    slot = &pool->slots[index];

    return slot->alive &&
           slot->generation == generation;
}

int XzGpuResource_Destroy(
    XzGpuResourcePool *pool,
    XzGpuHandle handle)
{
    XzGpuResourceSlot *slot =
        XzGpuResourceResolveSlot(
            pool, handle, 0);

    if (!slot)
        return 0;

    memset(&slot->desc, 0, sizeof(slot->desc));
    slot->alive = 0u;
    slot->generation++;
    if (slot->generation == 0u)
        slot->generation = 1u;

    if (pool->alive_count > 0u)
        pool->alive_count--;

    pool->destroys++;
    return 1;
}

int XzGpuResourcePool_SelfTest(void)
{
    XzGpuResourcePool pool;
    XzGpuResourceDesc desc;
    XzGpuHandle a;
    XzGpuHandle b;
    XzGpuHandle a2;

    XzGpuResourcePool_Init(&pool);
    memset(&desc, 0, sizeof(desc));

    desc.type = XZ_GPU_RESOURCE_TEXTURE;
    desc.width = 128u;
    desc.height = 128u;
    desc.samples = 1u;
    desc.size_bytes = 128u * 128u * 4u;

    a = XzGpuResource_Create(&pool, &desc);
    b = XzGpuResource_Create(&pool, &desc);

    if (a == XZ_GPU_INVALID_HANDLE ||
        b == XZ_GPU_INVALID_HANDLE ||
        a == b)
        return 0;

    if (!XzGpuResource_Resolve(&pool, a) ||
        !XzGpuResource_Resolve(&pool, b))
        return 0;

    if (pool.alive_count != 2u ||
        pool.high_water_count != 2u)
        return 0;

    if (!XzGpuResource_Destroy(&pool, a))
        return 0;

    if (XzGpuResource_Resolve(&pool, a) != NULL)
        return 0;
    if (pool.stale_resolves != 1u)
        return 0;

    a2 = XzGpuResource_Create(&pool, &desc);
    if (a2 == XZ_GPU_INVALID_HANDLE)
        return 0;

    if (XzGpuHandle_Index(a2) !=
        XzGpuHandle_Index(a))
        return 0;
    if (XzGpuHandle_Generation(a2) ==
        XzGpuHandle_Generation(a))
        return 0;

    if (!XzGpuResource_IsAlive(&pool, a2))
        return 0;
    if (XzGpuResource_IsAlive(&pool, a))
        return 0;

    return 1;
}
