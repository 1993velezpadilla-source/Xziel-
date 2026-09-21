#include "xz_scene_budget.h"

#include <string.h>

static unsigned int XzScaleBudget(
    unsigned int base,
    float scale,
    unsigned int minimum)
{
    unsigned int value;

    if (scale < 0.0f)
        scale = 0.0f;
    if (scale > 1.25f)
        scale = 1.25f;

    value = (unsigned int)((float)base * scale + 0.5f);
    if (value < minimum)
        value = minimum;

    return value;
}

static void XzTierBaseBudgets(
    XzDeviceTier tier,
    unsigned int *animation,
    unsigned int *shadows,
    unsigned int *vfx,
    unsigned int *lights)
{
    switch (tier) {
    case XZ_DEVICE_ULTRA:
        *animation = 48u;
        *shadows = 24u;
        *vfx = 96u;
        *lights = 24u;
        break;
    case XZ_DEVICE_HIGH:
        *animation = 32u;
        *shadows = 16u;
        *vfx = 64u;
        *lights = 16u;
        break;
    case XZ_DEVICE_MID:
        *animation = 20u;
        *shadows = 8u;
        *vfx = 40u;
        *lights = 8u;
        break;
    case XZ_DEVICE_LOW:
        *animation = 12u;
        *shadows = 4u;
        *vfx = 24u;
        *lights = 6u;
        break;
    case XZ_DEVICE_COMPAT:
    default:
        *animation = 8u;
        *shadows = 2u;
        *vfx = 16u;
        *lights = 4u;
        break;
    }
}

void XzSceneBudget_Build(
    XzSceneBudget *budget,
    const XzPresentFrame *frame,
    XzDeviceTier tier,
    const XzGovernorRecommendation *recommendation)
{
    unsigned int base_animation;
    unsigned int base_shadows;
    unsigned int base_vfx;
    unsigned int base_lights;
    float animation_scale = 1.0f;
    float shadow_scale = 1.0f;
    float vfx_scale = 1.0f;
    float light_scale = 1.0f;
    unsigned int i;

    if (!budget)
        return;

    memset(budget, 0, sizeof(*budget));

    XzTierBaseBudgets(
        tier,
        &base_animation,
        &base_shadows,
        &base_vfx,
        &base_lights);

    if (recommendation) {
        animation_scale = recommendation->animation_rate_scale;
        shadow_scale = recommendation->shadow_budget_scale;
        vfx_scale = recommendation->vfx_budget_scale;
        light_scale = recommendation->light_budget_scale;
    }

    budget->full_animation_budget =
        XzScaleBudget(base_animation, animation_scale, 4u);
    budget->shadowed_entity_budget =
        XzScaleBudget(base_shadows, shadow_scale, 1u);
    budget->premium_vfx_budget =
        XzScaleBudget(base_vfx, vfx_scale, 4u);
    budget->dynamic_light_budget =
        XzScaleBudget(base_lights, light_scale, 1u);

    if (!frame)
        return;

    for (i = 0u; i < frame->entity_count; ++i) {
        const XzPresentEntity *entity = &frame->entities[i];

        if (entity->distance_sq <= 65536.0f)
            budget->near_entities++;
        else if (entity->distance_sq <= 589824.0f)
            budget->mid_entities++;
        else
            budget->far_entities++;

        if (entity->priority_class >= 3u)
            budget->critical_entities++;
        else if (entity->priority_class >= 1u)
            budget->important_entities++;
        else
            budget->background_entities++;
    }

    budget->requested_lights = frame->active_light_count;
    budget->admitted_lights =
        budget->requested_lights < budget->dynamic_light_budget
            ? budget->requested_lights
            : budget->dynamic_light_budget;

    if (budget->full_animation_budget > 0u)
        budget->entity_load =
            (float)frame->alias_count /
            (float)budget->full_animation_budget;

    if (budget->dynamic_light_budget > 0u)
        budget->light_load =
            (float)budget->requested_lights /
            (float)budget->dynamic_light_budget;
}

int XzSceneBudget_SelfTest(void)
{
    XzPresentEntity entity;
    XzPresentFrame frame;
    XzSceneBudget budget;
    XzGovernorRecommendation recommendation;
    unsigned int i;

    memset(&frame, 0, sizeof(frame));
    memset(&recommendation, 0, sizeof(recommendation));

    recommendation.animation_rate_scale = 1.0f;
    recommendation.shadow_budget_scale = 0.5f;
    recommendation.vfx_budget_scale = 1.0f;
    recommendation.light_budget_scale = 0.5f;

    for (i = 0u; i < 12u; ++i) {
        memset(&entity, 0, sizeof(entity));
        entity.kind = XZ_PRESENT_ALIAS;
        entity.distance_sq = i < 4u
            ? 4096.0f
            : (i < 8u ? 262144.0f : 1048576.0f);
        entity.priority_class =
            i < 2u ? 3u : (i < 8u ? 1u : 0u);
        frame.entities[frame.entity_count++] = entity;
        frame.alias_count++;
    }
    frame.active_light_count = 10u;

    XzSceneBudget_Build(
        &budget,
        &frame,
        XZ_DEVICE_MID,
        &recommendation);

    if (budget.near_entities != 4u ||
        budget.mid_entities != 4u ||
        budget.far_entities != 4u)
        return 0;
    if (budget.critical_entities != 2u ||
        budget.important_entities != 6u ||
        budget.background_entities != 4u)
        return 0;
    if (budget.full_animation_budget != 20u)
        return 0;
    if (budget.shadowed_entity_budget != 4u)
        return 0;
    if (budget.dynamic_light_budget != 4u)
        return 0;
    if (budget.admitted_lights != 4u)
        return 0;

    return 1;
}
