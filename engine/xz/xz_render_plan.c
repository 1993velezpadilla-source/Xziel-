#include "xz_render_plan.h"

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    unsigned int packet_index;
    unsigned char priority;
    float distance_sq;
    uint32_t source_id;
} XzRenderRank;

static int XzRenderRankCompare(const void *a, const void *b)
{
    const XzRenderRank *ra = (const XzRenderRank *)a;
    const XzRenderRank *rb = (const XzRenderRank *)b;

    if (ra->priority > rb->priority) return -1;
    if (ra->priority < rb->priority) return 1;
    if (ra->distance_sq < rb->distance_sq) return -1;
    if (ra->distance_sq > rb->distance_sq) return 1;
    if (ra->source_id < rb->source_id) return -1;
    if (ra->source_id > rb->source_id) return 1;
    return 0;
}

static uint32_t XzHashU32(uint32_t hash, uint32_t value)
{
    hash ^= value;
    hash *= 16777619u;
    return hash;
}

static XzRenderLod XzChooseLod(const XzPresentEntity *entity)
{
    if (entity->priority_class >= 3u ||
        entity->distance_sq <= 65536.0f)
        return XZ_RENDER_LOD_NEAR;

    if (entity->priority_class >= 1u ||
        entity->distance_sq <= 589824.0f)
        return XZ_RENDER_LOD_MID;

    return XZ_RENDER_LOD_FAR;
}

void XzRenderPlan_Init(XzRenderPlan *plan)
{
    if (!plan)
        return;
    memset(plan, 0, sizeof(*plan));
}

void XzRenderPlan_Build(
    XzRenderPlan *plan,
    const XzPresentFrame *frame,
    const XzSceneBudget *budget,
    XzDeviceTier tier)
{
    XzRenderRank ranks[XZ_RENDER_MAX_PACKETS];
    unsigned int rank_count = 0u;
    unsigned int i;
    uint32_t hash = 2166136261u;

    if (!plan)
        return;

    XzRenderPlan_Init(plan);
    plan->device_tier = tier;

    if (!frame || !budget)
        return;

    plan->generation = frame->generation;
    plan->source_frame = frame->source_frame;
    plan->requested_lights = frame->active_light_count;
    plan->admitted_lights = budget->admitted_lights;

    for (i = 0u; i < frame->entity_count; ++i) {
        const XzPresentEntity *src = &frame->entities[i];
        XzRenderPacket *dst;

        if (plan->packet_count >= XZ_RENDER_MAX_PACKETS) {
            plan->dropped_packets++;
            continue;
        }

        dst = &plan->packets[plan->packet_count];
        memset(dst, 0, sizeof(*dst));

        dst->source_id = src->source_id;
        dst->asset_hash = src->asset_hash;
        dst->effects = src->effects;
        dst->frame = src->frame;
        dst->skin = src->skin;
        dst->render_mode = src->render_mode;
        dst->scale = src->scale;
        dst->priority_class = src->priority_class;
        dst->kind = (unsigned char)src->kind;
        dst->lod = (unsigned char)XzChooseLod(src);
        dst->distance_sq = src->distance_sq;

        dst->origin[0] = src->origin[0];
        dst->origin[1] = src->origin[1];
        dst->origin[2] = src->origin[2];
        dst->angles[0] = src->angles[0];
        dst->angles[1] = src->angles[1];
        dst->angles[2] = src->angles[2];

        if (dst->lod == XZ_RENDER_LOD_NEAR)
            plan->near_count++;
        else if (dst->lod == XZ_RENDER_LOD_MID)
            plan->mid_count++;
        else
            plan->far_count++;

        ranks[rank_count].packet_index = plan->packet_count;
        ranks[rank_count].priority = dst->priority_class;
        ranks[rank_count].distance_sq = dst->distance_sq;
        ranks[rank_count].source_id = dst->source_id;
        rank_count++;

        plan->packet_count++;
    }

    qsort(
        ranks,
        rank_count,
        sizeof(ranks[0]),
        XzRenderRankCompare);

    for (i = 0u; i < rank_count; ++i) {
        XzRenderPacket *packet =
            &plan->packets[ranks[i].packet_index];

        if (packet->kind == (unsigned char)XZ_PRESENT_ALIAS &&
            plan->full_animation_count <
                budget->full_animation_budget) {
            packet->feature_mask |=
                XZ_RENDER_FEATURE_FULL_ANIMATION;
            plan->full_animation_count++;
        }

        if (packet->priority_class >= 1u &&
            plan->shadow_count <
                budget->shadowed_entity_budget) {
            packet->feature_mask |=
                XZ_RENDER_FEATURE_SHADOW;
            plan->shadow_count++;
        }

        if ((packet->effects != 0u ||
             packet->priority_class >= 2u) &&
            plan->premium_vfx_count <
                budget->premium_vfx_budget) {
            packet->feature_mask |=
                XZ_RENDER_FEATURE_PREMIUM_VFX;
            plan->premium_vfx_count++;
        }
    }

    hash = XzHashU32(hash, (uint32_t)plan->generation);
    hash = XzHashU32(hash, (uint32_t)plan->source_frame);
    hash = XzHashU32(hash, (uint32_t)plan->packet_count);
    hash = XzHashU32(hash, (uint32_t)plan->admitted_lights);

    for (i = 0u; i < plan->packet_count; ++i) {
        const XzRenderPacket *packet = &plan->packets[i];
        hash = XzHashU32(hash, packet->source_id);
        hash = XzHashU32(hash, packet->asset_hash);
        hash = XzHashU32(hash, packet->feature_mask);
        hash = XzHashU32(hash, (uint32_t)packet->lod);
    }

    plan->content_hash = hash;
}

int XzRenderPlan_Validate(const XzRenderPlan *plan)
{
    unsigned int i;
    unsigned int near_count = 0u;
    unsigned int mid_count = 0u;
    unsigned int far_count = 0u;
    unsigned int animation_count = 0u;
    unsigned int shadow_count = 0u;
    unsigned int vfx_count = 0u;

    if (!plan)
        return 0;
    if (plan->packet_count > XZ_RENDER_MAX_PACKETS)
        return 0;
    if (plan->admitted_lights > plan->requested_lights)
        return 0;

    for (i = 0u; i < plan->packet_count; ++i) {
        const XzRenderPacket *packet = &plan->packets[i];

        if (packet->kind > (unsigned char)XZ_PRESENT_ALIAS)
            return 0;
        if (packet->lod > (unsigned char)XZ_RENDER_LOD_FAR)
            return 0;

        if (packet->lod == (unsigned char)XZ_RENDER_LOD_NEAR)
            near_count++;
        else if (packet->lod == (unsigned char)XZ_RENDER_LOD_MID)
            mid_count++;
        else
            far_count++;

        if (packet->feature_mask &
            XZ_RENDER_FEATURE_FULL_ANIMATION)
            animation_count++;
        if (packet->feature_mask &
            XZ_RENDER_FEATURE_SHADOW)
            shadow_count++;
        if (packet->feature_mask &
            XZ_RENDER_FEATURE_PREMIUM_VFX)
            vfx_count++;
    }

    return near_count == plan->near_count &&
           mid_count == plan->mid_count &&
           far_count == plan->far_count &&
           animation_count == plan->full_animation_count &&
           shadow_count == plan->shadow_count &&
           vfx_count == plan->premium_vfx_count;
}

int XzRenderPlan_SelfTest(void)
{
    XzPresentFrame frame;
    XzSceneBudget budget;
    XzRenderPlan plan;
    unsigned int i;

    memset(&frame, 0, sizeof(frame));
    memset(&budget, 0, sizeof(budget));

    frame.generation = 9u;
    frame.source_frame = 77;
    frame.active_light_count = 5u;

    for (i = 0u; i < 6u; ++i) {
        XzPresentEntity *entity = &frame.entities[i];

        entity->source_id = i + 1u;
        entity->asset_hash = 100u + i;
        entity->kind = XZ_PRESENT_ALIAS;
        entity->priority_class =
            i < 2u ? 3u : (i < 4u ? 1u : 0u);
        entity->distance_sq =
            i < 2u ? 4096.0f :
            (i < 4u ? 262144.0f : 1048576.0f);
        if (i == 0u)
            entity->effects = 1u;
        frame.entity_count++;
        frame.alias_count++;
    }

    budget.full_animation_budget = 3u;
    budget.shadowed_entity_budget = 2u;
    budget.premium_vfx_budget = 2u;
    budget.admitted_lights = 3u;

    XzRenderPlan_Build(
        &plan, &frame, &budget, XZ_DEVICE_MID);

    if (!XzRenderPlan_Validate(&plan))
        return 0;
    if (plan.packet_count != 6u)
        return 0;
    if (plan.full_animation_count != 3u)
        return 0;
    if (plan.shadow_count != 2u)
        return 0;
    if (plan.premium_vfx_count != 2u)
        return 0;
    if (plan.admitted_lights != 3u)
        return 0;
    if (plan.content_hash == 0u)
        return 0;

    return 1;
}
