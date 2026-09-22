#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

constexpr std::size_t kFrameTelemetryCapacity = 240;

struct FrameTimingSample {
    float cpuMs = 0.0f;
    float gpuMs = 0.0f;
    float presentMs = 0.0f;
};

struct FrameTimingSummary {
    std::uint32_t sampleCount = 0;

    float averageFrameMs = 0.0f;
    float p95FrameMs = 0.0f;
    float p99FrameMs = 0.0f;
    float maxFrameMs = 0.0f;

    std::uint32_t hitchCount = 0;
    float hitchRatio = 0.0f;

    bool cpuBoundLikely = false;
    bool gpuBoundLikely = false;
};

class FrameTelemetry final {
public:
    explicit FrameTelemetry(float targetFps = 60.0f);

    void reset() noexcept;
    void push(const FrameTimingSample& sample) noexcept;

    [[nodiscard]] FrameTimingSummary summarize() const noexcept;
    [[nodiscard]] std::size_t sampleCount() const noexcept;

private:
    float targetFps_ = 60.0f;

    std::array<FrameTimingSample, kFrameTelemetryCapacity> samples_{};
    std::size_t writeIndex_ = 0;
    std::size_t count_ = 0;
};

} // namespace xziel
