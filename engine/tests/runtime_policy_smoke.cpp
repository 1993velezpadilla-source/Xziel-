#include "xziel/runtime_policy.hpp"

#include <cassert>

int main() {
    xziel::RuntimePolicyPlanner planner;

    const auto performance = planner.plan({
        .gameMode = xziel::UserGameMode::Performance,
        .memoryPressure = xziel::MemoryPressure::Normal,
        .displayRefreshHz = 120.0f,
        .batterySaver = false,
        .charging = false,
    });

    assert(performance.preferredFps == 120.0f);
    assert(performance.maximumQuality == xziel::RenderQuality::Ultra);
    assert(performance.requestHighRefreshRate);
    assert(performance.allowRayQueryExperimental);

    const auto critical = planner.plan({
        .gameMode = xziel::UserGameMode::Performance,
        .memoryPressure = xziel::MemoryPressure::Critical,
        .displayRefreshHz = 120.0f,
        .batterySaver = false,
        .charging = true,
    });

    assert(critical.preferredFps <= 60.0f);
    assert(critical.maximumQuality == xziel::RenderQuality::Low);
    assert(critical.textureBudgetScale < 0.6f);
    assert(!critical.requestHighRefreshRate);

    xziel::RenderWorkload ultra{};
    ultra.quality = xziel::RenderQuality::Ultra;
    ultra.renderScale = 1.0f;
    ultra.maxPlanarReflectionPasses = 2;
    ultra.ssrEnabled = true;
    ultra.ssrMaxSteps = 40;
    ultra.shadowMapResolution = 1536;
    ultra.volumetricFogSteps = 32;

    const auto limited =
        planner.applyCeiling(ultra, critical);

    assert(limited.quality == xziel::RenderQuality::Low);
    assert(limited.renderScale <= 0.70f);
    assert(limited.maxPlanarReflectionPasses == 0);
    assert(!limited.ssrEnabled);
    assert(limited.shadowMapResolution <= 512);

    return 0;
}
