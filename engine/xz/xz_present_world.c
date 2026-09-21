#include "xz_present_world.h"

#include <float.h>
#include <stddef.h>
#include <string.h>

typedef struct {
    XzPresentFrame frames[2];
    unsigned int write_index;
    unsigned int read_index;
    uint64_t next_generation;
    int initialized;
} XzPresentWorldState;

static XzPresentWorldState xz_present_world;

static float XzDistanceSq(
    const float a[3],
    const float b[3])
{
    const float x = a[0] - b[0];
    const float y = a[1] - b[1];
    const float z = a[2] - b[2];
    return x * x + y * y + z * z;
}

void XzPresentWorld_Init(void)
{
    memset(&xz_present_world, 0, sizeof(xz_present_world));
    xz_present_world.write_index = 1u;
    xz_present_world.read_index = 0u;
    xz_present_world.next_generation = 1u;
    xz_present_world.initialized = 1;
}

void XzPresentWorld_Begin(
    int source_frame,
    const float camera_origin[3])
{
    XzPresentFrame *frame;

    if (!xz_present_world.initialized)
        XzPresentWorld_Init();

    xz_present_world.write_index =
        1u - __atomic_load_n(
            &xz_present_world.read_index,
            __ATOMIC_ACQUIRE);

    frame = &xz_present_world.frames[xz_present_world.write_index];
    memset(frame, 0, sizeof(*frame));

    frame->source_frame = source_frame;
    frame->nearest_distance_sq = FLT_MAX;
    frame->farthest_distance_sq = 0.0f;

    if (camera_origin) {
        frame->camera_origin[0] = camera_origin[0];
        frame->camera_origin[1] = camera_origin[1];
        frame->camera_origin[2] = camera_origin[2];
    }
}

int XzPresentWorld_Push(const XzPresentEntity *entity)
{
    XzPresentFrame *frame;
    XzPresentEntity *dst;

    if (!entity)
        return 0;

    frame = &xz_present_world.frames[xz_present_world.write_index];

    if (frame->entity_count >= XZ_PRESENT_MAX_ENTITIES) {
        frame->dropped_entities++;
        return 0;
    }

    dst = &frame->entities[frame->entity_count++];
    *dst = *entity;
    dst->distance_sq =
        XzDistanceSq(dst->origin, frame->camera_origin);

    if (dst->effects != 0u || dst->distance_sq <= 16384.0f)
        dst->priority_class = 3u;
    else if (dst->distance_sq <= 65536.0f)
        dst->priority_class = 2u;
    else if (dst->distance_sq <= 589824.0f)
        dst->priority_class = 1u;
    else
        dst->priority_class = 0u;

    if (dst->distance_sq < frame->nearest_distance_sq)
        frame->nearest_distance_sq = dst->distance_sq;
    if (dst->distance_sq > frame->farthest_distance_sq)
        frame->farthest_distance_sq = dst->distance_sq;

    switch (dst->kind) {
    case XZ_PRESENT_ALIAS:
        frame->alias_count++;
        break;
    case XZ_PRESENT_BRUSH:
        frame->brush_count++;
        break;
    case XZ_PRESENT_SPRITE:
        frame->sprite_count++;
        break;
    default:
        frame->unknown_count++;
        break;
    }

    return 1;
}

void XzPresentWorld_SetCameraBasis(
    const float forward[3],
    const float right[3],
    const float up[3],
    float fov_x,
    float fov_y)
{
    XzPresentFrame *frame =
        &xz_present_world.frames[xz_present_world.write_index];

    if (!forward || !right || !up)
        return;

    frame->camera_forward[0] = forward[0];
    frame->camera_forward[1] = forward[1];
    frame->camera_forward[2] = forward[2];

    frame->camera_right[0] = right[0];
    frame->camera_right[1] = right[1];
    frame->camera_right[2] = right[2];

    frame->camera_up[0] = up[0];
    frame->camera_up[1] = up[1];
    frame->camera_up[2] = up[2];

    frame->fov_x = fov_x;
    frame->fov_y = fov_y;
    frame->camera_basis_valid =
        fov_x > 0.0f && fov_y > 0.0f ? 1 : 0;
}

void XzPresentWorld_SetStaticBrushCount(unsigned int count)
{
    XzPresentFrame *frame =
        &xz_present_world.frames[xz_present_world.write_index];
    frame->static_brush_count = count;
}

void XzPresentWorld_SetActiveLightCount(unsigned int count)
{
    XzPresentFrame *frame =
        &xz_present_world.frames[xz_present_world.write_index];
    frame->active_light_count = count;
}

void XzPresentWorld_Commit(void)
{
    XzPresentFrame *frame;
    unsigned int index;

    if (!xz_present_world.initialized)
        return;

    index = xz_present_world.write_index;
    frame = &xz_present_world.frames[index];

    if (frame->entity_count == 0u)
        frame->nearest_distance_sq = 0.0f;

    frame->generation = xz_present_world.next_generation++;

    __atomic_store_n(
        &xz_present_world.read_index,
        index,
        __ATOMIC_RELEASE);
}

const XzPresentFrame *XzPresentWorld_GetReadFrame(void)
{
    unsigned int index;

    if (!xz_present_world.initialized)
        return NULL;

    index = __atomic_load_n(
        &xz_present_world.read_index,
        __ATOMIC_ACQUIRE);

    return &xz_present_world.frames[index];
}

uint32_t XzPresentWorld_HashAssetName(const char *name)
{
    uint32_t hash = 2166136261u;

    if (!name)
        return 0u;

    while (*name) {
        hash ^= (unsigned char)*name++;
        hash *= 16777619u;
    }

    return hash;
}

int XzPresentWorld_SelfTest(void)
{
    XzPresentEntity entity;
    const XzPresentFrame *frame;
    float camera[3] = {0.0f, 0.0f, 0.0f};

    XzPresentWorld_Init();
    XzPresentWorld_Begin(42, camera);

    memset(&entity, 0, sizeof(entity));
    entity.source_id = 7u;
    entity.asset_hash = XzPresentWorld_HashAssetName("progs/zombie.mdl");
    entity.kind = XZ_PRESENT_ALIAS;
    entity.origin[0] = 3.0f;
    entity.origin[1] = 4.0f;
    entity.origin[2] = 0.0f;

    if (!XzPresentWorld_Push(&entity))
        return 0;

    memset(&entity, 0, sizeof(entity));
    entity.source_id = 8u;
    entity.kind = XZ_PRESENT_SPRITE;
    entity.origin[0] = 10.0f;

    if (!XzPresentWorld_Push(&entity))
        return 0;

    XzPresentWorld_SetStaticBrushCount(5u);
    XzPresentWorld_SetActiveLightCount(2u);
    XzPresentWorld_Commit();

    frame = XzPresentWorld_GetReadFrame();
    if (!frame)
        return 0;
    if (frame->source_frame != 42)
        return 0;
    if (frame->entity_count != 2u)
        return 0;
    if (frame->alias_count != 1u || frame->sprite_count != 1u)
        return 0;
    if (frame->static_brush_count != 5u)
        return 0;
    if (frame->active_light_count != 2u)
        return 0;
    if (frame->nearest_distance_sq < 24.99f ||
        frame->nearest_distance_sq > 25.01f)
        return 0;
    if (frame->farthest_distance_sq < 99.99f ||
        frame->farthest_distance_sq > 100.01f)
        return 0;
    if (frame->generation == 0u)
        return 0;

    return 1;
}
