#include "xziel/renderer_watchdog.hpp"

#include <algorithm>

namespace xziel {

RendererWatchdog::RendererWatchdog() {
    reset();
}

void RendererWatchdog::reset() noexcept {
    state_ = {};
    recent_ = {};
    recentWrite_ = 0;
}

RendererWatchdogState RendererWatchdog::report(
    const RendererFaultEvent& event,
    RendererBackend activeBackend,
    bool compatibilityBackendAvailable) noexcept {
    if (event.fault == RendererFault::None) {
        return state_;
    }

    pushFault(event);
    ++state_.faultCount;

    state_.recommendedAction =
        RendererRecoveryAction::None;

    switch (event.fault) {
        case RendererFault::SwapchainFailed:
        case RendererFault::PresentFailed:
            state_.recommendedAction =
                RendererRecoveryAction::RecreateSwapchain;
            break;

        case RendererFault::PipelineCreationFailed:
        case RendererFault::ShaderValidationFailed:
            ++state_.pipelineFailureCount;
            state_.advancedFeaturesDisabled = true;
            state_.safeMode = true;
            state_.recommendedAction =
                RendererRecoveryAction::DropAdvancedFeatures;
            break;

        case RendererFault::OutOfMemory:
            ++state_.outOfMemoryCount;
            state_.advancedFeaturesDisabled = true;
            state_.safeMode = true;

            if (state_.outOfMemoryCount == 1) {
                state_.recommendedAction =
                    RendererRecoveryAction::DropAdvancedFeatures;
            } else if (
                activeBackend == RendererBackend::Vulkan &&
                compatibilityBackendAvailable) {
                state_.recommendedAction =
                    RendererRecoveryAction::SwitchCompatibilityRenderer;
            } else {
                state_.recommendedAction =
                    RendererRecoveryAction::ExitCleanly;
            }
            break;

        case RendererFault::DeviceLost:
            ++state_.deviceLostCount;

            // Vulkan makes a lost logical device sticky. No more work should be
            // submitted to that VkDevice. Platform code must tear it down
            // before any attempt to create a replacement device.
            state_.mustStopSubmitting = true;
            state_.safeMode = true;
            state_.advancedFeaturesDisabled = true;

            if (state_.deviceLostCount == 1) {
                state_.recommendedAction =
                    RendererRecoveryAction::RecreateDevice;
            } else if (
                activeBackend == RendererBackend::Vulkan &&
                compatibilityBackendAvailable) {
                state_.recommendedAction =
                    RendererRecoveryAction::SwitchCompatibilityRenderer;
            } else {
                state_.recommendedAction =
                    RendererRecoveryAction::ExitCleanly;
            }
            break;

        case RendererFault::InstanceInitFailed:
        case RendererFault::DeviceInitFailed:
            state_.safeMode = true;
            state_.advancedFeaturesDisabled = true;

            if (activeBackend == RendererBackend::Vulkan &&
                compatibilityBackendAvailable) {
                state_.recommendedAction =
                    RendererRecoveryAction::SwitchCompatibilityRenderer;
            } else {
                state_.recommendedAction =
                    RendererRecoveryAction::ExitCleanly;
            }
            break;

        case RendererFault::None:
            break;
    }

    // Repeated renderer faults in one session bias toward a safer backend.
    if (state_.faultCount >= 4 &&
        activeBackend == RendererBackend::Vulkan &&
        compatibilityBackendAvailable &&
        event.fault != RendererFault::SwapchainFailed &&
        event.fault != RendererFault::PresentFailed) {
        state_.safeMode = true;
        state_.advancedFeaturesDisabled = true;
        state_.recommendedAction =
            RendererRecoveryAction::SwitchCompatibilityRenderer;
    }

    return state_;
}

const RendererWatchdogState& RendererWatchdog::state() const noexcept {
    return state_;
}

const std::array<RendererFaultEvent, 16>&
RendererWatchdog::recentFaults() const noexcept {
    return recent_;
}

void RendererWatchdog::pushFault(
    const RendererFaultEvent& event) noexcept {
    recent_[recentWrite_] = event;
    recentWrite_ =
        (recentWrite_ + 1U) %
        static_cast<std::uint32_t>(recent_.size());
}

} // namespace xziel
