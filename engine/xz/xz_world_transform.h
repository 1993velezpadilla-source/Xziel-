#ifndef XZ_WORLD_TRANSFORM_H
#define XZ_WORLD_TRANSFORM_H

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_WORLD_UNITS_PER_METER 39.3700787402f

typedef struct XzWorldVec3 {
    float x;
    float y;
    float z;
} XzWorldVec3;

typedef struct XzWorldTransform {
    XzWorldVec3 source_origin_m;
    XzWorldVec3 runtime_origin_units;
    float basis[9];
    float units_per_meter;
} XzWorldTransform;

void XzWorldTransform_Init(XzWorldTransform *transform);

void XzWorldTransform_SetOrigins(
    XzWorldTransform *transform,
    XzWorldVec3 source_origin_m,
    XzWorldVec3 runtime_origin_units);

int XzWorldTransform_SetBasis(
    XzWorldTransform *transform,
    const float basis[9]);

int XzWorldTransform_IsValid(
    const XzWorldTransform *transform);

XzWorldVec3 XzWorldTransform_ToRuntime(
    const XzWorldTransform *transform,
    XzWorldVec3 source_m);

XzWorldVec3 XzWorldTransform_ToSourceMeters(
    const XzWorldTransform *transform,
    XzWorldVec3 runtime_units);

float XzWorldTransform_MetersToUnits(
    const XzWorldTransform *transform,
    float meters);

float XzWorldTransform_UnitsToMeters(
    const XzWorldTransform *transform,
    float units);

int XzWorldTransform_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
