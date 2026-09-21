#include "../engine/xz/xz_render_plan.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    XzPresentFrame frame;
    XzSceneBudget budget;
    XzRenderPlan plan;

    assert(XzRenderPlan_SelfTest());

    memset(&frame, 0, sizeof(frame));
    memset(&budget, 0, sizeof(budget));

    frame.generation = 11u;
    frame.source_frame = 200;
    frame.active_light_count = 4u;

    frame.entity_count = 2u;
    frame.alias_count = 2u;

    frame.entities[0].source_id = 10u;
    frame.entities[0].asset_hash = 1000u;
    frame.entities[0].kind = XZ_PRESENT_ALIAS;
    frame.entities[0].priority_class = 3u;
    frame.entities[0].distance_sq = 100.0f;

    frame.entities[1].source_id = 11u;
    frame.entities[1].asset_hash = 1001u;
    frame.entities[1].kind = XZ_PRESENT_ALIAS;
    frame.entities[1].priority_class = 0u;
    frame.entities[1].distance_sq = 1000000.0f;

    budget.full_animation_budget = 1u;
    budget.shadowed_entity_budget = 1u;
    budget.premium_vfx_budget = 1u;
    budget.admitted_lights = 2u;

    XzRenderPlan_Build(
        &plan,
        &frame,
        &budget,
        XZ_DEVICE_LOW);

    assert(XzRenderPlan_Validate(&plan));
    assert(plan.packet_count == 2u);
    assert(plan.near_count == 1u);
    assert(plan.far_count == 1u);
    assert(plan.full_animation_count == 1u);
    assert(plan.shadow_count == 1u);
    assert(plan.admitted_lights == 2u);

    puts("xz_render_plan_test: PASS");
    return 0;
}
