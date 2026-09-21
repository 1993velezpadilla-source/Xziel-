#ifndef XZ_BOTTLENECK_H
#define XZ_BOTTLENECK_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    XZ_BOTTLENECK_UNKNOWN = 0,
    XZ_BOTTLENECK_BALANCED,
    XZ_BOTTLENECK_UPDATE,
    XZ_BOTTLENECK_RENDER,
    XZ_BOTTLENECK_AUDIO
} XzBottleneckKind;

typedef struct {
    XzBottleneckKind kind;
    float update_share;
    float render_share;
    float audio_share;
    float dominant_ratio;
    float measured_total_ms;
} XzBottleneckAnalysis;

XzBottleneckAnalysis XzBottleneck_Analyze(
    unsigned long long accepted_frames,
    double update_p95_ms,
    double render_p95_ms,
    double audio_p95_ms);

const char *XzBottleneck_Name(XzBottleneckKind kind);

int XzBottleneck_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
