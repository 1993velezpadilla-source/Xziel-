#ifndef XZ_PHASE0_H
#define XZ_PHASE0_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_FRAME_WINDOW 120u
#define XZ_FEATURE_MAX 32u

typedef struct {
    double samples_ms[XZ_FRAME_WINDOW];
    unsigned int write_index;
    unsigned int count;
    uint64_t total_frames;
    double begin_seconds;
    double last_ms;
    double average_ms;
    double p50_ms;
    double p95_ms;
    double p99_ms;
    double max_ms;
    uint64_t spikes_over_25ms;
    uint64_t spikes_over_33ms;
    uint64_t spikes_over_50ms;
} XzFrameMetrics;

typedef struct {
    uint64_t soft_limit_bytes;
    uint64_t hard_limit_bytes;
    uint64_t current_bytes;
    uint64_t high_water_bytes;
} XzMemoryBudget;

typedef enum {
    XZ_GOVERNOR_HEADROOM = 0,
    XZ_GOVERNOR_STABLE,
    XZ_GOVERNOR_FRAME_PRESSURE,
    XZ_GOVERNOR_MEMORY_PRESSURE,
    XZ_GOVERNOR_THERMAL_PRESSURE
} XzGovernorState;

typedef struct {
    float render_scale;
    float animation_rate_scale;
    float shadow_budget_scale;
    float vfx_budget_scale;
    float light_budget_scale;
    float streaming_aggression;
} XzGovernorRecommendation;

typedef struct {
    double target_frame_ms;
    XzGovernorState state;
    int passive;
    XzGovernorRecommendation recommendation;
} XzPerformanceGovernor;

typedef struct {
    uint32_t id;
    float visual_value;
    float gameplay_value;
    float cpu_ms;
    float gpu_ms;
    float memory_mb;
    uint32_t requires_mask;
    uint32_t conflicts_mask;
} XzFeatureCandidate;

typedef struct {
    uint32_t selected_mask;
    float used_cpu_ms;
    float used_gpu_ms;
    float used_memory_mb;
    float total_value;
} XzFeaturePlan;

void XzFrameMetrics_Init(XzFrameMetrics *metrics);
void XzFrameMetrics_Begin(XzFrameMetrics *metrics, double now_seconds);
void XzFrameMetrics_End(XzFrameMetrics *metrics, double now_seconds);

void XzMemoryBudget_Init(
    XzMemoryBudget *budget,
    uint64_t soft_limit_bytes,
    uint64_t hard_limit_bytes);
void XzMemoryBudget_Sample(XzMemoryBudget *budget, uint64_t current_bytes);

void XzPerformanceGovernor_Init(
    XzPerformanceGovernor *governor,
    double target_frame_ms,
    int passive);
void XzPerformanceGovernor_Update(
    XzPerformanceGovernor *governor,
    const XzFrameMetrics *metrics,
    const XzMemoryBudget *memory,
    int thermal_status);

XzFeaturePlan XzFeaturePlanner_Select(
    const XzFeatureCandidate *candidates,
    unsigned int candidate_count,
    float cpu_budget_ms,
    float gpu_budget_ms,
    float memory_budget_mb);

const char *XzGovernorState_Name(XzGovernorState state);
int XzPhase0_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
