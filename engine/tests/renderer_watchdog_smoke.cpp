#include "xziel/renderer_watchdog.hpp"

#include <cassert>

int main() {
    xziel::RendererWatchdog watchdog;

    auto state = watchdog.report(
        {
            .fault = xziel::RendererFault::SwapchainFailed,
            .frameIndex = 100,
            .code = 1,
        },
        xziel::RendererBackend::Vulkan,
        true);

    assert(
        state.recommendedAction ==
        xziel::RendererRecoveryAction::RecreateSwapchain);
    assert(!state.mustStopSubmitting);

    state = watchdog.report(
        {
            .fault = xziel::RendererFault::DeviceLost,
            .frameIndex = 101,
            .code = 2,
        },
        xziel::RendererBackend::Vulkan,
        true);

    assert(state.mustStopSubmitting);
    assert(state.safeMode);
    assert(state.advancedFeaturesDisabled);
    assert(
        state.recommendedAction ==
        xziel::RendererRecoveryAction::RecreateDevice);

    // A repeated device loss should stop retrying the same aggressive path.
    state = watchdog.report(
        {
            .fault = xziel::RendererFault::DeviceLost,
            .frameIndex = 102,
            .code = 2,
        },
        xziel::RendererBackend::Vulkan,
        true);

    assert(
        state.recommendedAction ==
        xziel::RendererRecoveryAction::SwitchCompatibilityRenderer);

    watchdog.reset();

    state = watchdog.report(
        {
            .fault = xziel::RendererFault::OutOfMemory,
            .frameIndex = 10,
        },
        xziel::RendererBackend::Vulkan,
        true);

    assert(state.safeMode);
    assert(
        state.recommendedAction ==
        xziel::RendererRecoveryAction::DropAdvancedFeatures);

    return 0;
}
