#ifndef XZ_CUTOVER_H
#define XZ_CUTOVER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    XZ_CUTOVER_MODE_LEGACY = 0,
    XZ_CUTOVER_MODE_MIRROR,
    XZ_CUTOVER_MODE_MODERN
} XzCutoverMode;

enum {
    XZ_CUTOVER_CAP_BACKEND_HEALTH  = 1u << 0,
    XZ_CUTOVER_CAP_COMMAND_HEALTH  = 1u << 1,
    XZ_CUTOVER_CAP_GRAPH_HEALTH    = 1u << 2,
    XZ_CUTOVER_CAP_RESIDENCY       = 1u << 3,
    XZ_CUTOVER_CAP_ACTIVE_QUALITY  = 1u << 4,
    XZ_CUTOVER_CAP_REAL_GEOMETRY   = 1u << 5,
    XZ_CUTOVER_CAP_REAL_TEXTURES   = 1u << 6,
    XZ_CUTOVER_CAP_VISIBLE_PRESENT = 1u << 7
};

#define XZ_CUTOVER_OPERATIONAL_MASK     (XZ_CUTOVER_CAP_BACKEND_HEALTH |      XZ_CUTOVER_CAP_COMMAND_HEALTH |      XZ_CUTOVER_CAP_GRAPH_HEALTH |      XZ_CUTOVER_CAP_RESIDENCY |      XZ_CUTOVER_CAP_ACTIVE_QUALITY)

#define XZ_CUTOVER_PARITY_MASK     (XZ_CUTOVER_OPERATIONAL_MASK |      XZ_CUTOVER_CAP_REAL_GEOMETRY |      XZ_CUTOVER_CAP_REAL_TEXTURES |      XZ_CUTOVER_CAP_VISIBLE_PRESENT)

typedef struct {
    int backend_healthy;
    int commands_healthy;
    int graph_healthy;
    int residency_healthy;
    int active_quality_healthy;

    int real_geometry_ready;
    int real_textures_ready;
    int visible_present_ready;

    uint64_t healthy_frames;
} XzCutoverEvidence;

typedef struct {
    XzCutoverMode requested_mode;
    XzCutoverMode active_mode;

    uint32_t capability_mask;
    uint32_t blocker_mask;

    int candidate_ready;
    int cutover_allowed;

    uint64_t evaluations;
    uint64_t mode_changes;
    uint64_t blocked_modern_evaluations;
    uint64_t last_healthy_frames;
} XzCutoverState;

void XzCutover_Init(
    XzCutoverState *state);

void XzCutover_RequestMode(
    XzCutoverState *state,
    XzCutoverMode mode);

void XzCutover_Evaluate(
    XzCutoverState *state,
    const XzCutoverEvidence *evidence);

const char *XzCutoverMode_Name(
    XzCutoverMode mode);

int XzCutover_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
