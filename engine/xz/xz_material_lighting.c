#include "xz_material_lighting.h"

#include <string.h>

#define XZ_TEX_COLOR    1
#define XZ_TEX_TEXTURE  2
#define XZ_TEX_GLOW     3
#define XZ_TEX_SOLID    4
#define XZ_TEX_ADDITIVE 5
#define XZ_TEX_LMPOINT  6

static float XzClamp01(float v)
{
    if (v < 0.0f)
        return 0.0f;
    if (v > 1.0f)
        return 1.0f;
    return v;
}

static float XzDistanceSq3(
    const float a[3],
    const float b[3])
{
    const float x = a[0] - b[0];
    const float y = a[1] - b[1];
    const float z = a[2] - b[2];
    return x * x + y * y + z * z;
}

static float XzLightScore(
    const XzPresentLight *light,
    const float camera[3])
{
    const float radius_sq =
        light->radius * light->radius;
    const float distance_sq =
        XzDistanceSq3(light->origin, camera);

    return radius_sq /
        (1.0f + distance_sq * 0.0025f);
}

static unsigned int XzMaterialFlags(
    const XzPresentEntity *entity)
{
    unsigned int flags = 0u;

    switch (entity->render_mode) {
    case XZ_TEX_COLOR:
        flags |= XZ_MATERIAL_COLOR;
        break;
    case XZ_TEX_TEXTURE:
        flags |= XZ_MATERIAL_TEXTURE;
        break;
    case XZ_TEX_GLOW:
        flags |= XZ_MATERIAL_GLOW;
        break;
    case XZ_TEX_SOLID:
        flags |= XZ_MATERIAL_SOLID;
        break;
    case XZ_TEX_ADDITIVE:
        flags |= XZ_MATERIAL_ADDITIVE;
        break;
    case XZ_TEX_LMPOINT:
        flags |= XZ_MATERIAL_LMPOINT;
        break;
    default:
        flags |= XZ_MATERIAL_TEXTURE;
        break;
    }

    if (entity->render_amount > 0.0f &&
        entity->render_amount < 0.999f)
        flags |= XZ_MATERIAL_TRANSLUCENT;

    return flags;
}

static void XzBaseColor(
    const XzPresentEntity *entity,
    unsigned int flags,
    float rgba[4])
{
    int use_color =
        (flags & (XZ_MATERIAL_COLOR |
                  XZ_MATERIAL_GLOW |
                  XZ_MATERIAL_ADDITIVE |
                  XZ_MATERIAL_LMPOINT)) != 0u;

    rgba[0] = 1.0f;
    rgba[1] = 1.0f;
    rgba[2] = 1.0f;
    rgba[3] = 1.0f;

    if (use_color) {
        const float sum =
            entity->render_color[0] +
            entity->render_color[1] +
            entity->render_color[2];

        if (sum > 0.001f) {
            rgba[0] = XzClamp01(entity->render_color[0]);
            rgba[1] = XzClamp01(entity->render_color[1]);
            rgba[2] = XzClamp01(entity->render_color[2]);
        }
    }

    if ((flags & XZ_MATERIAL_TRANSLUCENT) != 0u)
        rgba[3] = XzClamp01(entity->render_amount);
}

void XzMaterialLighting_Select(
    XzMaterialLightSet *set,
    const XzPresentFrame *frame,
    const XzSceneBudget *budget)
{
    unsigned int i;
    unsigned int limit;

    if (!set)
        return;

    memset(set, 0, sizeof(*set));

    if (!frame || !budget)
        return;

    set->requested_count = frame->active_light_count;
    limit = budget->admitted_lights;
    if (limit > XZ_MATERIAL_MAX_LIGHTS)
        limit = XZ_MATERIAL_MAX_LIGHTS;
    if (limit > frame->active_light_count)
        limit = frame->active_light_count;

    for (i = 0u; i < frame->active_light_count; ++i) {
        XzMaterialLight candidate;
        unsigned int insert_at;
        unsigned int j;

        memset(&candidate, 0, sizeof(candidate));
        candidate.light = frame->lights[i];
        candidate.camera_distance_sq =
            XzDistanceSq3(
                candidate.light.origin,
                frame->camera_origin);
        candidate.score =
            XzLightScore(
                &candidate.light,
                frame->camera_origin);

        insert_at = set->count;
        for (j = 0u; j < set->count; ++j) {
            if (candidate.score > set->lights[j].score) {
                insert_at = j;
                break;
            }
        }

        if (insert_at >= limit && set->count >= limit)
            continue;

        if (set->count < limit)
            set->count++;

        for (j = set->count - 1u; j > insert_at; --j)
            set->lights[j] = set->lights[j - 1u];

        set->lights[insert_at] = candidate;
    }

    for (i = 0u; i < set->count; ++i) {
        if (set->lights[i].light.dark)
            set->dark_count++;
    }
}

void XzMaterialLighting_Shade(
    XzMaterialSample *sample,
    const XzPresentEntity *entity,
    const XzMaterialLightSet *set)
{
    unsigned int i;
    float lighting[3] = {0.32f, 0.32f, 0.32f};

    if (!sample)
        return;

    memset(sample, 0, sizeof(*sample));

    if (!entity)
        return;

    sample->flags = XzMaterialFlags(entity);
    XzBaseColor(
        entity,
        sample->flags,
        sample->base_rgba);

    if (set) {
        for (i = 0u; i < set->count; ++i) {
            const XzPresentLight *light =
                &set->lights[i].light;
            const float radius_sq =
                light->radius * light->radius;
            const float distance_sq =
                XzDistanceSq3(
                    light->origin,
                    entity->origin);
            float attenuation;
            float sign;

            if (radius_sq <= 0.0f ||
                distance_sq >= radius_sq)
                continue;

            attenuation =
                1.0f - distance_sq / radius_sq;
            if (attenuation <= 0.0f)
                continue;

            sign = light->dark ? -1.0f : 1.0f;

            lighting[0] +=
                sign * XzClamp01(light->color[0]) *
                attenuation * 0.75f;
            lighting[1] +=
                sign * XzClamp01(light->color[1]) *
                attenuation * 0.75f;
            lighting[2] +=
                sign * XzClamp01(light->color[2]) *
                attenuation * 0.75f;

            sample->contributing_lights++;
        }
    }

    if ((sample->flags &
         (XZ_MATERIAL_GLOW |
          XZ_MATERIAL_ADDITIVE)) != 0u) {
        if (lighting[0] < 1.0f) lighting[0] = 1.0f;
        if (lighting[1] < 1.0f) lighting[1] = 1.0f;
        if (lighting[2] < 1.0f) lighting[2] = 1.0f;
    }

    sample->lit_rgba[0] =
        XzClamp01(sample->base_rgba[0] * XzClamp01(lighting[0]));
    sample->lit_rgba[1] =
        XzClamp01(sample->base_rgba[1] * XzClamp01(lighting[1]));
    sample->lit_rgba[2] =
        XzClamp01(sample->base_rgba[2] * XzClamp01(lighting[2]));
    sample->lit_rgba[3] = sample->base_rgba[3];
}

int XzMaterialLighting_SelfTest(void)
{
    XzPresentFrame frame;
    XzSceneBudget budget;
    XzPresentEntity entity;
    XzMaterialLightSet set;
    XzMaterialSample sample;

    memset(&frame, 0, sizeof(frame));
    memset(&budget, 0, sizeof(budget));
    memset(&entity, 0, sizeof(entity));

    frame.active_light_count = 2u;

    frame.lights[0].origin[0] = 10.0f;
    frame.lights[0].radius = 100.0f;
    frame.lights[0].color[0] = 1.0f;

    frame.lights[1].origin[0] = 20.0f;
    frame.lights[1].radius = 40.0f;
    frame.lights[1].color[1] = 1.0f;
    frame.lights[1].dark = 1;

    budget.admitted_lights = 2u;

    XzMaterialLighting_Select(
        &set, &frame, &budget);

    if (set.count != 2u ||
        set.requested_count != 2u ||
        set.dark_count != 1u)
        return 0;

    entity.render_mode = XZ_TEX_COLOR;
    entity.render_amount = 0.5f;
    entity.render_color[0] = 0.8f;
    entity.render_color[1] = 0.4f;
    entity.render_color[2] = 0.2f;

    XzMaterialLighting_Shade(
        &sample, &entity, &set);

    if ((sample.flags & XZ_MATERIAL_COLOR) == 0u ||
        (sample.flags & XZ_MATERIAL_TRANSLUCENT) == 0u)
        return 0;

    if (sample.base_rgba[3] < 0.49f ||
        sample.base_rgba[3] > 0.51f)
        return 0;

    if (sample.contributing_lights == 0u)
        return 0;

    return 1;
}
