#include "xz_phase0.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    unsigned int index;
    float score;
    uint32_t id;
} XzFeatureRank;

static double XzClampDouble(double value, double lo, double hi)
{
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

static float XzClampFloat(float value, float lo, float hi)
{
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

static int XzCompareDouble(const void *a, const void *b)
{
    const double da = *(const double *)a;
    const double db = *(const double *)b;
    return (da > db) - (da < db);
}

static int XzCompareFeatureRank(const void *a, const void *b)
{
    const XzFeatureRank *ra = (const XzFeatureRank *)a;
    const XzFeatureRank *rb = (const XzFeatureRank *)b;
    if (ra->score < rb->score) return 1;
    if (ra->score > rb->score) return -1;
    if (ra->id > rb->id) return 1;
    if (ra->id < rb->id) return -1;
    return 0;
}

static void XzFrameMetrics_Recompute(XzFrameMetrics *metrics)
{
    double sorted[XZ_FRAME_WINDOW];
    double total = 0.0;
    unsigned int i;
    unsigned int n = metrics->count;
    unsigned int p50;
    unsigned int p95;
    unsigned int p99;

    if (!n)
        return;

    for (i = 0; i < n; ++i) {
        sorted[i] = metrics->samples_ms[i];
        total += sorted[i];
    }

    qsort(sorted, n, sizeof(sorted[0]), XzCompareDouble);

    p50 = (unsigned int)((n - 1u) * 0.50 + 0.5);
    p95 = (unsigned int)((n - 1u) * 0.95 + 0.5);
    p99 = (unsigned int)((n - 1u) * 0.99 + 0.5);

    metrics->average_ms = total / (double)n;
    metrics->p50_ms = sorted[p50];
    metrics->p95_ms = sorted[p95];
    metrics->p99_ms = sorted[p99];
    metrics->max_ms = sorted[n - 1u];
}

void XzFrameMetrics_Init(XzFrameMetrics *metrics)
{
    if (!metrics) return;
    memset(metrics, 0, sizeof(*metrics));
}

void XzFrameMetrics_Begin(XzFrameMetrics *metrics, double now_seconds)
{
    if (!metrics) return;
    metrics->begin_seconds = now_seconds;
}

void XzFrameMetrics_End(XzFrameMetrics *metrics, double now_seconds)
{
    double elapsed_ms;

    if (!metrics)
        return;

    elapsed_ms = (now_seconds - metrics->begin_seconds) * 1000.0;
    elapsed_ms = XzClampDouble(elapsed_ms, 0.0, 10000.0);

    metrics->last_ms = elapsed_ms;
    metrics->samples_ms[metrics->write_index] = elapsed_ms;
    metrics->write_index = (metrics->write_index + 1u) % XZ_FRAME_WINDOW;
    if (metrics->count < XZ_FRAME_WINDOW)
        metrics->count++;
    metrics->total_frames++;

    if (elapsed_ms > 25.0) metrics->spikes_over_25ms++;
    if (elapsed_ms > 33.333) metrics->spikes_over_33ms++;
    if (elapsed_ms > 50.0) metrics->spikes_over_50ms++;

    if (metrics->total_frames <= 8u ||
        (metrics->total_frames % 15u) == 0u)
        XzFrameMetrics_Recompute(metrics);
}

void XzMemoryBudget_Init(
    XzMemoryBudget *budget,
    uint64_t soft_limit_bytes,
    uint64_t hard_limit_bytes)
{
    if (!budget) return;
    memset(budget, 0, sizeof(*budget));
    budget->soft_limit_bytes = soft_limit_bytes;
    budget->hard_limit_bytes =
        hard_limit_bytes > soft_limit_bytes ? hard_limit_bytes : soft_limit_bytes;
}

void XzMemoryBudget_Sample(XzMemoryBudget *budget, uint64_t current_bytes)
{
    if (!budget) return;
    budget->current_bytes = current_bytes;
    if (current_bytes > budget->high_water_bytes)
        budget->high_water_bytes = current_bytes;
}

static void XzGovernor_DefaultRecommendation(
    XzGovernorRecommendation *recommendation)
{
    recommendation->render_scale = 1.0f;
    recommendation->animation_rate_scale = 1.0f;
    recommendation->shadow_budget_scale = 1.0f;
    recommendation->vfx_budget_scale = 1.0f;
    recommendation->light_budget_scale = 1.0f;
    recommendation->streaming_aggression = 1.0f;
}

void XzPerformanceGovernor_Init(
    XzPerformanceGovernor *governor,
    double target_frame_ms,
    int passive)
{
    if (!governor) return;
    memset(governor, 0, sizeof(*governor));
    governor->target_frame_ms =
        target_frame_ms > 1.0 ? target_frame_ms : 16.6667;
    governor->state = XZ_GOVERNOR_STABLE;
    governor->passive = passive ? 1 : 0;
    XzGovernor_DefaultRecommendation(&governor->recommendation);
}

void XzPerformanceGovernor_Update(
    XzPerformanceGovernor *governor,
    const XzFrameMetrics *metrics,
    const XzMemoryBudget *memory,
    int thermal_status)
{
    double memory_ratio = 0.0;
    XzGovernorRecommendation rec;

    if (!governor || !metrics || !memory)
        return;

    XzGovernor_DefaultRecommendation(&rec);

    if (memory->hard_limit_bytes > 0)
        memory_ratio =
            (double)memory->current_bytes / (double)memory->hard_limit_bytes;

    if (thermal_status >= 3) {
        governor->state = XZ_GOVERNOR_THERMAL_PRESSURE;
        rec.render_scale = 0.80f;
        rec.animation_rate_scale = 0.78f;
        rec.shadow_budget_scale = 0.60f;
        rec.vfx_budget_scale = 0.65f;
        rec.light_budget_scale = 0.65f;
        rec.streaming_aggression = 0.80f;
    } else if (memory_ratio >= 0.92) {
        governor->state = XZ_GOVERNOR_MEMORY_PRESSURE;
        rec.render_scale = 0.90f;
        rec.animation_rate_scale = 0.90f;
        rec.shadow_budget_scale = 0.80f;
        rec.vfx_budget_scale = 0.72f;
        rec.light_budget_scale = 0.80f;
        rec.streaming_aggression = 0.55f;
    } else if (metrics->total_frames >= XZ_FRAME_WINDOW &&
               metrics->p95_ms > governor->target_frame_ms * 1.35) {
        governor->state = XZ_GOVERNOR_FRAME_PRESSURE;
        rec.render_scale = 0.85f;
        rec.animation_rate_scale = 0.85f;
        rec.shadow_budget_scale = 0.70f;
        rec.vfx_budget_scale = 0.75f;
        rec.light_budget_scale = 0.75f;
        rec.streaming_aggression = 0.90f;
    } else if (metrics->total_frames >= XZ_FRAME_WINDOW &&
               metrics->p95_ms < governor->target_frame_ms * 0.80 &&
               memory_ratio < 0.70) {
        governor->state = XZ_GOVERNOR_HEADROOM;
        rec.render_scale = 1.0f;
        rec.animation_rate_scale = 1.0f;
        rec.shadow_budget_scale = 1.0f;
        rec.vfx_budget_scale = 1.0f;
        rec.light_budget_scale = 1.0f;
        rec.streaming_aggression = 1.10f;
    } else {
        governor->state = XZ_GOVERNOR_STABLE;
    }

    rec.render_scale = XzClampFloat(rec.render_scale, 0.50f, 1.0f);
    rec.animation_rate_scale =
        XzClampFloat(rec.animation_rate_scale, 0.25f, 1.0f);
    rec.shadow_budget_scale =
        XzClampFloat(rec.shadow_budget_scale, 0.0f, 1.0f);
    rec.vfx_budget_scale =
        XzClampFloat(rec.vfx_budget_scale, 0.0f, 1.0f);
    rec.light_budget_scale =
        XzClampFloat(rec.light_budget_scale, 0.0f, 1.0f);
    rec.streaming_aggression =
        XzClampFloat(rec.streaming_aggression, 0.25f, 1.25f);

    governor->recommendation = rec;
}

static float XzFeatureScore(
    const XzFeatureCandidate *candidate,
    float cpu_budget_ms,
    float gpu_budget_ms,
    float memory_budget_mb)
{
    float value;
    float cost = 0.0f;

    value = candidate->visual_value + candidate->gameplay_value * 4.0f;
    if (cpu_budget_ms > 0.0f)
        cost += candidate->cpu_ms / cpu_budget_ms;
    if (gpu_budget_ms > 0.0f)
        cost += candidate->gpu_ms / gpu_budget_ms;
    if (memory_budget_mb > 0.0f)
        cost += candidate->memory_mb / memory_budget_mb;

    if (cost < 0.001f)
        cost = 0.001f;

    return value / cost;
}

XzFeaturePlan XzFeaturePlanner_Select(
    const XzFeatureCandidate *candidates,
    unsigned int candidate_count,
    float cpu_budget_ms,
    float gpu_budget_ms,
    float memory_budget_mb)
{
    XzFeaturePlan plan;
    XzFeatureRank ranks[XZ_FEATURE_MAX];
    unsigned int count;
    unsigned int i;
    unsigned int pass;
    int changed;

    memset(&plan, 0, sizeof(plan));

    if (!candidates || !candidate_count)
        return plan;

    count = candidate_count > XZ_FEATURE_MAX
        ? XZ_FEATURE_MAX : candidate_count;

    for (i = 0; i < count; ++i) {
        ranks[i].index = i;
        ranks[i].id = candidates[i].id;
        ranks[i].score = XzFeatureScore(
            &candidates[i],
            cpu_budget_ms,
            gpu_budget_ms,
            memory_budget_mb);
    }

    qsort(ranks, count, sizeof(ranks[0]), XzCompareFeatureRank);

    for (pass = 0; pass < count; ++pass) {
        changed = 0;

        for (i = 0; i < count; ++i) {
            const XzFeatureCandidate *candidate =
                &candidates[ranks[i].index];
            uint32_t bit;
            float next_cpu;
            float next_gpu;
            float next_memory;

            if (candidate->id >= 32u)
                continue;

            bit = 1u << candidate->id;
            if (plan.selected_mask & bit)
                continue;
            if ((candidate->requires_mask & plan.selected_mask) !=
                candidate->requires_mask)
                continue;
            if (candidate->conflicts_mask & plan.selected_mask)
                continue;

            next_cpu = plan.used_cpu_ms + candidate->cpu_ms;
            next_gpu = plan.used_gpu_ms + candidate->gpu_ms;
            next_memory = plan.used_memory_mb + candidate->memory_mb;

            if (next_cpu > cpu_budget_ms ||
                next_gpu > gpu_budget_ms ||
                next_memory > memory_budget_mb)
                continue;

            plan.selected_mask |= bit;
            plan.used_cpu_ms = next_cpu;
            plan.used_gpu_ms = next_gpu;
            plan.used_memory_mb = next_memory;
            plan.total_value +=
                candidate->visual_value + candidate->gameplay_value * 4.0f;
            changed = 1;
        }

        if (!changed)
            break;
    }

    return plan;
}

const char *XzGovernorState_Name(XzGovernorState state)
{
    switch (state) {
    case XZ_GOVERNOR_HEADROOM: return "HEADROOM";
    case XZ_GOVERNOR_STABLE: return "STABLE";
    case XZ_GOVERNOR_FRAME_PRESSURE: return "FRAME_PRESSURE";
    case XZ_GOVERNOR_MEMORY_PRESSURE: return "MEMORY_PRESSURE";
    case XZ_GOVERNOR_THERMAL_PRESSURE: return "THERMAL_PRESSURE";
    default: return "UNKNOWN";
    }
}

int XzPhase0_SelfTest(void)
{
    XzFrameMetrics metrics;
    XzMemoryBudget memory;
    XzPerformanceGovernor governor;
    XzFeatureCandidate candidates[3];
    XzFeaturePlan plan;
    unsigned int i;

    XzFrameMetrics_Init(&metrics);
    for (i = 0; i < 40u; ++i) {
        double start = (double)i;
        XzFrameMetrics_Begin(&metrics, start);
        XzFrameMetrics_End(&metrics, start + 0.016);
    }

    if (metrics.count != 40u)
        return 0;
    if (fabs(metrics.p95_ms - 16.0) > 0.01)
        return 0;

    XzMemoryBudget_Init(
        &memory,
        256u * 1024u * 1024u,
        384u * 1024u * 1024u);
    XzMemoryBudget_Sample(&memory, 128u * 1024u * 1024u);

    XzPerformanceGovernor_Init(&governor, 16.6667, 1);
    XzPerformanceGovernor_Update(&governor, &metrics, &memory, -1);
    if (governor.state != XZ_GOVERNOR_STABLE &&
        governor.state != XZ_GOVERNOR_HEADROOM)
        return 0;

    memset(candidates, 0, sizeof(candidates));
    candidates[0].id = 0;
    candidates[0].visual_value = 5.0f;
    candidates[0].gameplay_value = 5.0f;
    candidates[0].cpu_ms = 0.4f;
    candidates[0].gpu_ms = 0.3f;
    candidates[0].memory_mb = 4.0f;

    candidates[1].id = 1;
    candidates[1].visual_value = 3.0f;
    candidates[1].cpu_ms = 0.2f;
    candidates[1].gpu_ms = 0.2f;
    candidates[1].memory_mb = 2.0f;
    candidates[1].requires_mask = 1u << 0;

    candidates[2].id = 2;
    candidates[2].visual_value = 1.0f;
    candidates[2].cpu_ms = 5.0f;
    candidates[2].gpu_ms = 5.0f;
    candidates[2].memory_mb = 100.0f;

    plan = XzFeaturePlanner_Select(
        candidates, 3u, 1.0f, 1.0f, 16.0f);

    if ((plan.selected_mask & (1u << 0)) == 0)
        return 0;
    if ((plan.selected_mask & (1u << 2)) != 0)
        return 0;

    return 1;
}
