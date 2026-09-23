#pragma once

#include "xziel/performance.hpp"

#include <cstdint>

namespace xziel {

enum class UserGameMode : std::uint8_t {
    Standard,
    Performance,
    Battery,
};

enum class MemoryPressure : std::uint8_t {
    Normal,
    Elevated,
    Critical,
};

struct RuntimePolicyInput {
    UserGameMode gameMode = UserGameMode::Standard;
    MemoryPressure memoryPressure = MemoryPressure::Normal;

    float displayRefreshHz = 60.0f;
    bool batterySaver = false;
    bool charging = false;

    // Cached Android ADPF/headroom telemetry. Negative/NaN means unavailable.
    // thermalHeadroom is PowerManager's thermal-envelope usage where 1.0 is
    // the severe-throttling threshold. CPU/GPU headroom are Android 16
    // percentages of currently available compute capacity.
    float thermalHeadroom = -1.0f;
    float cpuHeadroomPercent = -1.0f;
    float gpuHeadroomPercent = -1.0f;
};

struct RuntimePolicy {
    float preferredFps = 60.0f;
    RenderQuality maximumQuality = RenderQuality::High;

    float textureBudgetScale = 1.0f;
    float meshBudgetScale = 1.0f;
    float audioBudgetScale = 1.0f;

    bool requestHighRefreshRate = false;
    bool allowRayQueryExperimental = false;
};

class RuntimePolicyPlanner final {
public:
    [[nodiscard]] RuntimePolicy plan(
        const RuntimePolicyInput& input) const noexcept;

    [[nodiscard]] RenderWorkload applyCeiling(
        const RenderWorkload& workload,
        const RuntimePolicy& policy) const noexcept;

private:
    [[nodiscard]] static int qualityRank(RenderQuality quality) noexcept;
};

} // namespace xziel
