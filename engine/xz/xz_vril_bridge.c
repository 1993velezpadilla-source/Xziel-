#include "nzportable_def.h"
#include "xz_present_world.h"
#include "xz_vril_bridge.h"

#include <stdint.h>
#include <string.h>

static uint32_t XzVrilBridge_SourceId(const entity_t *entity)
{
    uintptr_t p;
    uintptr_t first;
    uintptr_t end;

    if (!entity)
        return UINT32_MAX;

    p = (uintptr_t)entity;
    first = (uintptr_t)&cl_entities[0];
    end = (uintptr_t)&cl_entities[MAX_EDICTS];

    if (p >= first && p < end) {
        uintptr_t offset = p - first;
        if ((offset % sizeof(entity_t)) == 0u)
            return (uint32_t)(offset / sizeof(entity_t));
    }

    return UINT32_MAX;
}

static XzPresentKind XzVrilBridge_Kind(const entity_t *entity)
{
    if (!entity || !entity->model)
        return XZ_PRESENT_UNKNOWN;

    switch (entity->model->type) {
    case mod_brush:
        return XZ_PRESENT_BRUSH;
    case mod_sprite:
        return XZ_PRESENT_SPRITE;
    case mod_alias:
        return XZ_PRESENT_ALIAS;
    default:
        return XZ_PRESENT_UNKNOWN;
    }
}

static unsigned int XzVrilBridge_CaptureActiveLights(void)
{
    unsigned int count = 0u;
    int i;

    for (i = 0; i < MAX_DLIGHTS; ++i) {
        const dlight_t *source = &cl_dlights[i];
        XzPresentLight light;

        if (source->die < (float)cl.time ||
            source->radius <= 0.0f)
            continue;

        memset(&light, 0, sizeof(light));
        light.origin[0] = source->origin[0];
        light.origin[1] = source->origin[1];
        light.origin[2] = source->origin[2];
        light.color[0] = source->color[0];
        light.color[1] = source->color[1];
        light.color[2] = source->color[2];
        light.radius = source->radius;
        light.minlight = source->minlight;
        light.type = source->type;
        light.dark = source->dark ? 1 : 0;

        if (XzPresentWorld_PushLight(&light))
            count++;
    }

    return count;
}

void XzVrilBridge_Init(void)
{
    XzPresentWorld_Init();
}

void XzVrilBridge_CapturePresentation(int source_frame)
{
    unsigned int i;

    XzPresentWorld_Begin(source_frame, r_origin);
    XzPresentWorld_SetCameraBasis(
        vpn,
        vright,
        vup,
        r_refdef.fov_x,
        r_refdef.fov_y);

    for (i = 0u; i < (unsigned int)cl_numvisedicts; ++i) {
        const entity_t *source = cl_visedicts[i];
        XzPresentEntity entity;

        if (!source || !source->model)
            continue;

        memset(&entity, 0, sizeof(entity));
        entity.source_id = XzVrilBridge_SourceId(source);
        entity.asset_hash =
            XzPresentWorld_HashAssetName(source->model->name);
        entity.effects = (uint32_t)source->effects;
        entity.frame = source->frame;
        entity.skin = source->skinnum;
        entity.render_mode = (int)source->rendermode;
        entity.render_amount = source->renderamt;
        entity.render_color[0] = source->rendercolor[0];
        entity.render_color[1] = source->rendercolor[1];
        entity.render_color[2] = source->rendercolor[2];
        entity.scale = source->scale;
        entity.kind = XzVrilBridge_Kind(source);

        entity.origin[0] = source->origin[0];
        entity.origin[1] = source->origin[1];
        entity.origin[2] = source->origin[2];

        entity.angles[0] = source->angles[0];
        entity.angles[1] = source->angles[1];
        entity.angles[2] = source->angles[2];

        XzPresentWorld_Push(&entity);
    }

    XzPresentWorld_SetStaticBrushCount(
        cl_numstaticbrushmodels > 0
            ? (unsigned int)cl_numstaticbrushmodels : 0u);
    XzVrilBridge_CaptureActiveLights();

    XzPresentWorld_Commit();
}

void XzVrilBridge_Shutdown(void)
{
}

int XzVrilBridge_SelfTest(void)
{
    return XzPresentWorld_SelfTest();
}
