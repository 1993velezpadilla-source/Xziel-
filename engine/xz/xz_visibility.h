#ifndef XZ_VISIBILITY_H
#define XZ_VISIBILITY_H

#include "xz_present_world.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    XZ_VISIBILITY_FRONT = 0,
    XZ_VISIBILITY_EDGE,
    XZ_VISIBILITY_BEHIND,
    XZ_VISIBILITY_CULLED
} XzVisibilityClass;

typedef struct {
    XzVisibilityClass visibility_class;
    int admitted;
    float view_forward;
    float view_right;
    float view_up;
    float projected_radius;
} XzVisibilityResult;

void XzVisibility_Classify(
    const XzPresentFrame *frame,
    const XzPresentEntity *entity,
    XzVisibilityResult *result);

int XzVisibility_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
