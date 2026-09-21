#include "xz_shadow_packets.h"

#include <string.h>

static float XzU32Unit(unsigned int value)
{
    return (float)(value & 0xffffu) / 65535.0f;
}

unsigned int XzShadowPackets_Pack(
    const XzRenderPlan *plan,
    XzShadowInstance *instances,
    unsigned int capacity)
{
    unsigned int count;
    unsigned int i;

    if (!plan || !instances || capacity == 0u)
        return 0u;

    count = plan->packet_count < capacity
        ? plan->packet_count
        : capacity;

    for (i = 0u; i < count; ++i) {
        const XzRenderPacket *packet = &plan->packets[i];
        XzShadowInstance *instance = &instances[i];

        memset(instance, 0, sizeof(*instance));

        instance->world_meta[0] = packet->origin[0];
        instance->world_meta[1] = packet->origin[1];
        instance->world_meta[2] = packet->origin[2];
        instance->world_meta[3] =
            (float)packet->priority_class / 3.0f;

        instance->render_meta[0] =
            (float)packet->lod / 2.0f;
        instance->render_meta[1] =
            (float)(packet->feature_mask & 7u) / 7.0f;
        instance->render_meta[2] =
            XzU32Unit(packet->asset_hash);
        instance->render_meta[3] =
            XzU32Unit(packet->source_id);
    }

    return count;
}

int XzShadowPackets_SelfTest(void)
{
    XzRenderPlan plan;
    XzShadowInstance instances[2];
    unsigned int count;

    memset(&plan, 0, sizeof(plan));
    memset(instances, 0, sizeof(instances));

    plan.packet_count = 2u;

    plan.packets[0].origin[0] = 10.0f;
    plan.packets[0].origin[1] = -20.0f;
    plan.packets[0].origin[2] = 30.0f;
    plan.packets[0].priority_class = 3u;
    plan.packets[0].lod = XZ_RENDER_LOD_NEAR;
    plan.packets[0].feature_mask =
        XZ_RENDER_FEATURE_FULL_ANIMATION |
        XZ_RENDER_FEATURE_SHADOW;
    plan.packets[0].asset_hash = 0x1234u;
    plan.packets[0].source_id = 7u;

    plan.packets[1].priority_class = 0u;
    plan.packets[1].lod = XZ_RENDER_LOD_FAR;
    plan.packets[1].feature_mask =
        XZ_RENDER_FEATURE_PREMIUM_VFX;
    plan.packets[1].asset_hash = 0xffffu;
    plan.packets[1].source_id = 0xffffu;

    count = XzShadowPackets_Pack(
        &plan, instances, 2u);

    if (count != 2u)
        return 0;

    if (instances[0].world_meta[0] != 10.0f ||
        instances[0].world_meta[1] != -20.0f ||
        instances[0].world_meta[2] != 30.0f ||
        instances[0].world_meta[3] != 1.0f)
        return 0;

    if (instances[0].render_meta[0] != 0.0f)
        return 0;
    if (instances[0].render_meta[1] <= 0.0f ||
        instances[0].render_meta[1] >= 1.0f)
        return 0;

    if (instances[1].render_meta[0] != 1.0f ||
        instances[1].render_meta[2] != 1.0f ||
        instances[1].render_meta[3] != 1.0f)
        return 0;

    return 1;
}
