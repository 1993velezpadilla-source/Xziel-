#include "xziel/frame_telemetry.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace xziel {

namespace {

float sanitized(float value) noexcept {
    if (!std::isfinite(value) || value < 0.0f) {
        return 0.0f;
    }
    return std::min(value, 1000.0f);
}

float combined(const FrameTimingSample& sample) noexcept {
    return std::max({
        sanitized(sample.cpuMs),
        sanitized(sample.gpuMs),
        sanitized(sample.presentMs),
    });
}

} // namespace

FrameTelemetry::FrameTelemetry(float targetFps)
    : targetFps_(std::max(1.0f, targetFps)) {}

void FrameTelemetry::reset() noexcept {
    samples_ = {};
    writeIndex_ = 0;
    count_ = 0;
}

void FrameTelemetry::push(
    const FrameTimingSample& sample) noexcept {
    samples_[writeIndex_] = {
        .cpuMs = sanitized(sample.cpuMs),
        .gpuMs = sanitized(sample.gpuMs),
        .presentMs = sanitized(sample.presentMs),
    };

    writeIndex_ =
        (writeIndex_ + 1U) % samples_.size();
    count_ = std::min(count_ + 1U, samples_.size());
}

FrameTimingSummary FrameTelemetry::summarize() const noexcept {
    FrameTimingSummary out{};
    out.sampleCount = static_cast<std::uint32_t>(count_);

    if (count_ == 0) {
        return out;
    }

    std::array<float, kFrameTelemetryCapacity> frameTimes{};

    float sum = 0.0f;
    float cpuSum = 0.0f;
    float gpuSum = 0.0f;

    const float targetMs =
        1000.0f / targetFps_;
    const float hitchThreshold =
        targetMs * 1.50f;

    for (std::size_t i = 0; i < count_; ++i) {
        const auto& sample = samples_[i];
        const float frame = combined(sample);

        frameTimes[i] = frame;
        sum += frame;
        cpuSum += sample.cpuMs;
        gpuSum += sample.gpuMs;

        if (frame > hitchThreshold) {
            ++out.hitchCount;
        }

        out.maxFrameMs =
            std::max(out.maxFrameMs, frame);
    }

    std::sort(
        frameTimes.begin(),
        frameTimes.begin() +
            static_cast<std::ptrdiff_t>(count_));

    const auto percentile = [&](float p) noexcept {
        const float index =
            p * static_cast<float>(count_ - 1U);
        const std::size_t lo =
            static_cast<std::size_t>(index);
        const std::size_t hi =
            std::min(lo + 1U, count_ - 1U);
        const float fraction =
            index - static_cast<float>(lo);

        return frameTimes[lo] +
            (frameTimes[hi] - frameTimes[lo]) *
            fraction;
    };

    out.averageFrameMs =
        sum / static_cast<float>(count_);
    out.p95FrameMs = percentile(0.95f);
    out.p99FrameMs = percentile(0.99f);
    out.hitchRatio =
        static_cast<float>(out.hitchCount) /
        static_cast<float>(count_);

    const float averageCpu =
        cpuSum / static_cast<float>(count_);
    const float averageGpu =
        gpuSum / static_cast<float>(count_);

    out.cpuBoundLikely =
        averageCpu > averageGpu * 1.12f &&
        averageCpu > targetMs * 0.85f;

    out.gpuBoundLikely =
        averageGpu > averageCpu * 1.12f &&
        averageGpu > targetMs * 0.85f;

    return out;
}

std::size_t FrameTelemetry::sampleCount() const noexcept {
    return count_;
}

} // namespace xziel
