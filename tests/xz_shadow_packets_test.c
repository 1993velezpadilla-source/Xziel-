#include "../engine/xz/xz_shadow_packets.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    XzRenderPlan plan;
    XzShadowInstance instance;
    unsigned int count;

    assert(XzShadowPackets_SelfTest());

    memset(&plan, 0, sizeof(plan));
    memset(&instance, 0, sizeof(instance));

    plan.packet_count = 1u;
    plan.packets[0].origin[0] = 1.0f;
    plan.packets[0].origin[1] = 2.0f;
    plan.packets[0].origin[2] = 3.0f;
    plan.packets[0].priority_class = 2u;
    plan.packets[0].lod = XZ_RENDER_LOD_MID;
    plan.packets[0].feature_mask =
        XZ_RENDER_FEATURE_SHADOW;
    plan.packets[0].asset_hash = 100u;
    plan.packets[0].source_id = 200u;

    count = XzShadowPackets_Pack(
        &plan, &instance, 1u);

    assert(count == 1u);
    assert(instance.world_meta[0] == 1.0f);
    assert(instance.world_meta[1] == 2.0f);
    assert(instance.world_meta[2] == 3.0f);
    assert(instance.render_meta[0] == 0.5f);
    assert(instance.render_meta[1] > 0.0f);

    puts("xz_shadow_packets_test: PASS");
    return 0;
}
