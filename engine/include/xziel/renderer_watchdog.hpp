#pragma once

#include "xziel/renderer_capabilities.hpp"

#include <array>
#include <cstdint>

namespace xziel {

enum class RendererFault : std::uint8_t {
    None,
    InstanceInitFailed,
    DeviceInitFailed,
    SwapchainFailed,
    OutOfMemory,
    DeviceLost,
    PipelineCreationFailed,
    ShaderValidationFailed,
    PresentFailed,
};

enum class RendererRecoveryAction : std::uint8_t {
    None,
    RecreateSwapchain,
    RecreateDevice,
    DropAdvancedFeatures,
    SwitchCompatibilityRenderer,
    ExitCleanly,
};

struct RendererFaultEvent {
    RendererFault fault = RendererFault::None;
    std::uint64_t frameIndex = 0;
    std::uint32_t code = 0;
};

struct RendererWatchdogState {
    std::uint32_t faultCount = 0;
    std::uint32_t deviceLostCount = 0;
    std::uint32_t outOfMemoryCount = 0;
    std::uint32_t pipelineFailureCount = 0;

    bool safeMode = false;
    bool advancedFeaturesDisabled = false;
    bool mustStopSubmitting = false;

    RendererRecoveryAction recommendedAction =
        RendererRecoveryAction::None;
};

class RendererWatchdog final {
public:
    RendererWatchdog();

    void reset() noexcept;

    [[nodiscard]] RendererWatchdogState report(
        const RendererFaultEvent& event,
        RendererBackend activeBackend,
        bool compatibilityBackendAvailable) noexcept;

    [[nodiscard]] const RendererWatchdogState& state() const noexcept;

    [[nodiscard]] const std::array<RendererFaultEvent, 16>&
    recentFaults() const noexcept;

private:
    void pushFault(const RendererFaultEvent& event) noexcept;

    RendererWatchdogState state_{};
    std::array<RendererFaultEvent, 16> recent_{};
    std::uint32_t recentWrite_ = 0;
};

} // namespace xziel
