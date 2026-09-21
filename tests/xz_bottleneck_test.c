#include "../engine/xz/xz_bottleneck.h"

#include <assert.h>
#include <stdio.h>

static void test_warmup(void)
{
    XzBottleneckAnalysis a =
        XzBottleneck_Analyze(60ull, 2.0, 50.0, 1.0);

    assert(a.kind == XZ_BOTTLENECK_UNKNOWN);
}

static void test_render_bound(void)
{
    XzBottleneckAnalysis a =
        XzBottleneck_Analyze(240ull, 4.0, 130.0, 0.05);

    assert(a.kind == XZ_BOTTLENECK_RENDER);
    assert(a.render_share > 0.90f);
    assert(a.dominant_ratio > 10.0f);
}

static void test_update_bound(void)
{
    XzBottleneckAnalysis a =
        XzBottleneck_Analyze(240ull, 18.0, 8.0, 0.5);

    assert(a.kind == XZ_BOTTLENECK_UPDATE);
    assert(a.update_share > 0.60f);
}

static void test_audio_bound(void)
{
    XzBottleneckAnalysis a =
        XzBottleneck_Analyze(240ull, 2.0, 3.0, 15.0);

    assert(a.kind == XZ_BOTTLENECK_AUDIO);
    assert(a.audio_share > 0.70f);
}

static void test_balanced(void)
{
    XzBottleneckAnalysis a =
        XzBottleneck_Analyze(240ull, 7.0, 8.0, 6.0);

    assert(a.kind == XZ_BOTTLENECK_BALANCED);
}

int main(void)
{
    test_warmup();
    test_render_bound();
    test_update_bound();
    test_audio_bound();
    test_balanced();
    assert(XzBottleneck_SelfTest());

    puts("xz_bottleneck_test: PASS");
    return 0;
}
