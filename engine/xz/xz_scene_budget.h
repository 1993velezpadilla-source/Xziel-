#ifndef XZ_SCENE_BUDGET_H
#define XZ_SCENE_BUDGET_H

#include "xz_device_caps.h"
#include "xz_phase0.h"
#include "xz_present_world.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    unsigned int near_entities;
    unsigned int mid_entities;
    unsigned int far_entities;

    unsigned int critical_entities;
    unsigned int important_entities;
    unsigned int background_entities;

    unsigned int full_animation_budget;
    unsigned int shadowed_entity_budget;
    unsigned int premium_vfx_budget;
    unsigned int dynamic_light_budget;

    unsigned int requested_lights;
    unsigned int admitted_lights;

    float entity_load;
    float light_load;
} XzSceneBudget;

void XzSceneBudget_Build(
    XzSceneBudget *budget,
    const XzPresentFrame *frame,
    XzDeviceTier tier,
    const XzGovernorRecommendation *recommendation);

int XzSceneBudget_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
