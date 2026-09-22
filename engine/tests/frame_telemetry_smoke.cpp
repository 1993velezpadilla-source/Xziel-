#include "xziel/frame_telemetry.hpp"

#include <cassert>

int main() {
    xziel::FrameTelemetry telemetry(60.0f);

    for (int i = 0; i < 220; ++i) {
        telemetry.push({
            .cpuMs = 6.0f,
            .gpuMs = 10.0f,
            .presentMs = 11.0f,
        });
    }

    for (int i = 0; i < 20; ++i) {
        telemetry.push({
            .cpuMs = 8.0f,
            .gpuMs = 31.0f,
            .presentMs = 33.0f,
        });
    }

    const auto summary = telemetry.summarize();

    assert(summary.sampleCount == 240);
    assert(summary.averageFrameMs > 0.0f);
    assert(summary.p95FrameMs >= summary.averageFrameMs);
    assert(summary.p99FrameMs >= summary.p95FrameMs);
    assert(summary.maxFrameMs >= summary.p99FrameMs);
    assert(summary.hitchCount == 20);
    assert(summary.gpuBoundLikely);

    return 0;
}
