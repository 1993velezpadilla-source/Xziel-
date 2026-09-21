#include "../engine/xz/xz_present_world.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_snapshot(void)
{
    XzPresentEntity e;
    const XzPresentFrame *frame;
    float camera[3] = {10.0f, 20.0f, 30.0f};

    XzPresentWorld_Init();
    XzPresentWorld_Begin(100, camera);

    memset(&e, 0, sizeof(e));
    e.source_id = 1u;
    e.kind = XZ_PRESENT_ALIAS;
    e.origin[0] = 13.0f;
    e.origin[1] = 24.0f;
    e.origin[2] = 30.0f;
    assert(XzPresentWorld_Push(&e));

    memset(&e, 0, sizeof(e));
    e.source_id = 2u;
    e.kind = XZ_PRESENT_BRUSH;
    e.origin[0] = 10.0f;
    e.origin[1] = 20.0f;
    e.origin[2] = 40.0f;
    assert(XzPresentWorld_Push(&e));

    XzPresentWorld_SetStaticBrushCount(9u);
    XzPresentWorld_SetActiveLightCount(3u);
    XzPresentWorld_Commit();

    frame = XzPresentWorld_GetReadFrame();
    assert(frame != NULL);
    assert(frame->source_frame == 100);
    assert(frame->entity_count == 2u);
    assert(frame->alias_count == 1u);
    assert(frame->brush_count == 1u);
    assert(frame->static_brush_count == 9u);
    assert(frame->active_light_count == 3u);
    assert(frame->nearest_distance_sq > 24.99f);
    assert(frame->nearest_distance_sq < 25.01f);
    assert(frame->farthest_distance_sq > 99.99f);
    assert(frame->farthest_distance_sq < 100.01f);
}

static void test_double_buffer_generation(void)
{
    const XzPresentFrame *a;
    const XzPresentFrame *b;
    float camera[3] = {0.0f, 0.0f, 0.0f};

    XzPresentWorld_Init();

    XzPresentWorld_Begin(1, camera);
    XzPresentWorld_Commit();
    a = XzPresentWorld_GetReadFrame();
    assert(a != NULL);
    assert(a->generation == 1u);

    XzPresentWorld_Begin(2, camera);
    XzPresentWorld_Commit();
    b = XzPresentWorld_GetReadFrame();
    assert(b != NULL);
    assert(b->generation == 2u);
    assert(b->source_frame == 2);
}

static void test_hash(void)
{
    uint32_t a = XzPresentWorld_HashAssetName("progs/zombie.mdl");
    uint32_t b = XzPresentWorld_HashAssetName("progs/zombie.mdl");
    uint32_t c = XzPresentWorld_HashAssetName("progs/player.mdl");

    assert(a != 0u);
    assert(a == b);
    assert(a != c);
}

int main(void)
{
    test_snapshot();
    test_double_buffer_generation();
    test_hash();
    assert(XzPresentWorld_SelfTest());

    puts("xz_present_world_test: PASS");
    return 0;
}
