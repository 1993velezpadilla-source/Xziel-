#include "../engine/xz/xz_phase0.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static void test_frame_metrics(void)
{
    XzFrameMetrics metrics;
    unsigned int i;

    XzFrameMetrics_Init(&metrics);

    for (i = 0; i < 120u; ++i) {
        const double ms = i < 114u ? 10.0 : 30.0;
        XzFrameMetrics_Begin(&metrics, (double)i);
        XzFrameMetrics_End(&metrics, (double)i + ms / 1000.0);
    }

    assert(metrics.total_frames == 120u);
    assert(metrics.count == 120u);
    assert(metrics.p50_ms > 9.9 && metrics.p50_ms < 10.1);
    assert(metrics.p95_ms >= 10.0);
    assert(metrics.max_ms > 29.9);
    assert(metrics.spikes_over_25ms == 6u);
}

static void test_memory_and_governor(void)
{
    XzFrameMetrics metrics;
    XzMemoryBudget memory;
    XzPerformanceGovernor governor;
    unsigned int i;

    XzFrameMetrics_Init(&metrics);
    for (i = 0; i < 120u; ++i) {
        XzFrameMetrics_Begin(&metrics, (double)i);
        XzFrameMetrics_End(&metrics, (double)i + 0.030);
    }

    XzMemoryBudget_Init(&memory, 100u, 200u);
    XzMemoryBudget_Sample(&memory, 50u);

    XzPerformanceGovernor_Init(&governor, 16.6667, 1);
    XzPerformanceGovernor_Update(&governor, &metrics, &memory, -1);

    assert(governor.passive == 1);
    assert(governor.state == XZ_GOVERNOR_FRAME_PRESSURE);
    assert(governor.recommendation.render_scale < 1.0f);

    XzMemoryBudget_Sample(&memory, 190u);
    XzPerformanceGovernor_Update(&governor, &metrics, &memory, -1);
    assert(governor.state == XZ_GOVERNOR_MEMORY_PRESSURE);
}

static void test_feature_planner(void)
{
    XzFeatureCandidate features[4];
    XzFeaturePlan plan;

    memset(features, 0, sizeof(features));

    features[0].id = 0;
    features[0].visual_value = 4.0f;
    features[0].gameplay_value = 5.0f;
    features[0].cpu_ms = 0.20f;
    features[0].gpu_ms = 0.20f;
    features[0].memory_mb = 2.0f;

    features[1].id = 1;
    features[1].visual_value = 3.0f;
    features[1].cpu_ms = 0.15f;
    features[1].gpu_ms = 0.15f;
    features[1].memory_mb = 1.0f;
    features[1].requires_mask = 1u << 0;

    features[2].id = 2;
    features[2].visual_value = 2.0f;
    features[2].cpu_ms = 0.10f;
    features[2].gpu_ms = 0.10f;
    features[2].memory_mb = 1.0f;
    features[2].conflicts_mask = 1u << 1;

    features[3].id = 3;
    features[3].visual_value = 1.0f;
    features[3].cpu_ms = 20.0f;
    features[3].gpu_ms = 20.0f;
    features[3].memory_mb = 1000.0f;

    plan = XzFeaturePlanner_Select(
        features, 4u, 1.0f, 1.0f, 16.0f);

    assert(plan.selected_mask & (1u << 0));
    assert(!(plan.selected_mask & (1u << 3)));
    assert(plan.used_cpu_ms <= 1.0f);
    assert(plan.used_gpu_ms <= 1.0f);
    assert(plan.used_memory_mb <= 16.0f);
}

int main(void)
{
    test_frame_metrics();
    test_memory_and_governor();
    test_feature_planner();
    assert(XzPhase0_SelfTest());

    puts("xz_phase0_test: PASS");
    return 0;
}
