#ifndef XZ_STREAM_RESIDENCY_H
#define XZ_STREAM_RESIDENCY_H

#include "xz_device_caps.h"
#include "xz_phase0.h"
#include "xz_render_plan.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_RESIDENCY_MAX_SLOTS 128u

typedef struct {
    uint32_t asset_hash;
    uint64_t last_seen_generation;
    unsigned char priority;
    unsigned char lod;
    unsigned char resident;
} XzResidencySlot;

typedef struct {
    XzResidencySlot slots[XZ_RESIDENCY_MAX_SLOTS];

    unsigned int capacity;
    unsigned int resident_count;
    unsigned int high_water_count;

    uint64_t updates;
    uint64_t hits;
    uint64_t loads;
    uint64_t evictions;
    uint64_t misses;
    uint64_t protected_keeps;

    unsigned int last_requested_unique;
    unsigned int last_admitted_unique;
    float last_aggression;
} XzStreamResidency;

void XzStreamResidency_Init(
    XzStreamResidency *state);

void XzStreamResidency_Update(
    XzStreamResidency *state,
    const XzRenderPlan *plan,
    XzDeviceTier tier,
    const XzGovernorRecommendation *recommendation);

int XzStreamResidency_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
