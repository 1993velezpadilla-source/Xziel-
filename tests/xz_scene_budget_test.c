#include "../engine/xz/xz_scene_budget.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    XzPresentFrame frame;
    XzPresentEntity entity;
    XzSceneBudget budget;
    XzGovernorRecommendation rec;

    assert(XzSceneBudget_SelfTest());

    memset(&frame, 0, sizeof(frame));
    memset(&entity, 0, sizeof(entity));
    memset(&rec, 0, sizeof(rec));

    entity.kind = XZ_PRESENT_ALIAS;
    entity.distance_sq = 100.0f;
    entity.priority_class = 3u;
    frame.entities[0] = entity;
    frame.entity_count = 1u;
    frame.alias_count = 1u;
    frame.active_light_count = 2u;

    rec.animation_rate_scale = 1.0f;
    rec.shadow_budget_scale = 1.0f;
    rec.vfx_budget_scale = 1.0f;
    rec.light_budget_scale = 1.0f;

    XzSceneBudget_Build(
        &budget, &frame, XZ_DEVICE_LOW, &rec);

    assert(budget.near_entities == 1u);
    assert(budget.critical_entities == 1u);
    assert(budget.admitted_lights == 2u);
    assert(budget.full_animation_budget == 12u);

    puts("xz_scene_budget_test: PASS");
    return 0;
}
