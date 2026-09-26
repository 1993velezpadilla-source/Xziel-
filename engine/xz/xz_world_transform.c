#include "xz_world_transform.h"

#include <math.h>
#include <string.h>

static float XzWorldTransform_Dot3(
    const float *a,
    const float *b)
{
    return a[0] * b[0] +
           a[1] * b[1] +
           a[2] * b[2];
}

static int XzWorldTransform_BasisValid(
    const float basis[9])
{
    float cross[3];
    float determinant;
    int row;

    if (!basis)
        return 0;

    for (row = 0; row < 3; ++row) {
        const float *r = basis + row * 3;
        float length2 = XzWorldTransform_Dot3(r, r);
        if (!isfinite(length2) ||
            fabsf(length2 - 1.0f) > 0.0025f)
            return 0;
    }

    if (fabsf(XzWorldTransform_Dot3(basis, basis + 3)) > 0.0025f ||
        fabsf(XzWorldTransform_Dot3(basis, basis + 6)) > 0.0025f ||
        fabsf(XzWorldTransform_Dot3(basis + 3, basis + 6)) > 0.0025f)
        return 0;

    cross[0] = basis[4] * basis[8] - basis[5] * basis[7];
    cross[1] = basis[5] * basis[6] - basis[3] * basis[8];
    cross[2] = basis[3] * basis[7] - basis[4] * basis[6];
    determinant = XzWorldTransform_Dot3(basis, cross);

    /*
     * Accept both right- and left-handed orthonormal bases. Some imported
     * sources legitimately flip one axis (for example Unreal Y -> XZIEL -Y).
     */
    return isfinite(determinant) &&
        fabsf(fabsf(determinant) - 1.0f) <= 0.0025f;
}

void XzWorldTransform_Init(XzWorldTransform *transform)
{
    static const float identity[9] = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f
    };

    if (!transform)
        return;

    memset(transform, 0, sizeof(*transform));
    memcpy(transform->basis, identity, sizeof(identity));
    transform->units_per_meter = XZ_WORLD_UNITS_PER_METER;
}

void XzWorldTransform_SetOrigins(
    XzWorldTransform *transform,
    XzWorldVec3 source_origin_m,
    XzWorldVec3 runtime_origin_units)
{
    if (!transform)
        return;

    transform->source_origin_m = source_origin_m;
    transform->runtime_origin_units = runtime_origin_units;
}

int XzWorldTransform_SetBasis(
    XzWorldTransform *transform,
    const float basis[9])
{
    if (!transform || !XzWorldTransform_BasisValid(basis))
        return 0;

    memcpy(transform->basis, basis, sizeof(transform->basis));
    return 1;
}

int XzWorldTransform_IsValid(
    const XzWorldTransform *transform)
{
    if (!transform ||
        !isfinite(transform->units_per_meter) ||
        transform->units_per_meter <= 0.0f)
        return 0;

    if (!isfinite(transform->source_origin_m.x) ||
        !isfinite(transform->source_origin_m.y) ||
        !isfinite(transform->source_origin_m.z) ||
        !isfinite(transform->runtime_origin_units.x) ||
        !isfinite(transform->runtime_origin_units.y) ||
        !isfinite(transform->runtime_origin_units.z))
        return 0;

    return XzWorldTransform_BasisValid(transform->basis);
}

XzWorldVec3 XzWorldTransform_ToRuntime(
    const XzWorldTransform *transform,
    XzWorldVec3 source_m)
{
    XzWorldVec3 result = {0.0f, 0.0f, 0.0f};
    float delta[3];

    if (!XzWorldTransform_IsValid(transform))
        return result;

    delta[0] = source_m.x - transform->source_origin_m.x;
    delta[1] = source_m.y - transform->source_origin_m.y;
    delta[2] = source_m.z - transform->source_origin_m.z;

    result.x = transform->runtime_origin_units.x +
        XzWorldTransform_Dot3(transform->basis, delta) *
            transform->units_per_meter;
    result.y = transform->runtime_origin_units.y +
        XzWorldTransform_Dot3(transform->basis + 3, delta) *
            transform->units_per_meter;
    result.z = transform->runtime_origin_units.z +
        XzWorldTransform_Dot3(transform->basis + 6, delta) *
            transform->units_per_meter;

    return result;
}

XzWorldVec3 XzWorldTransform_ToSourceMeters(
    const XzWorldTransform *transform,
    XzWorldVec3 runtime_units)
{
    XzWorldVec3 result = {0.0f, 0.0f, 0.0f};
    float delta[3];

    if (!XzWorldTransform_IsValid(transform))
        return result;

    delta[0] = (runtime_units.x - transform->runtime_origin_units.x) /
        transform->units_per_meter;
    delta[1] = (runtime_units.y - transform->runtime_origin_units.y) /
        transform->units_per_meter;
    delta[2] = (runtime_units.z - transform->runtime_origin_units.z) /
        transform->units_per_meter;

    /*
     * For an orthonormal basis, inverse(B) == transpose(B).
     */
    result.x = transform->source_origin_m.x +
        transform->basis[0] * delta[0] +
        transform->basis[3] * delta[1] +
        transform->basis[6] * delta[2];
    result.y = transform->source_origin_m.y +
        transform->basis[1] * delta[0] +
        transform->basis[4] * delta[1] +
        transform->basis[7] * delta[2];
    result.z = transform->source_origin_m.z +
        transform->basis[2] * delta[0] +
        transform->basis[5] * delta[1] +
        transform->basis[8] * delta[2];

    return result;
}

float XzWorldTransform_MetersToUnits(
    const XzWorldTransform *transform,
    float meters)
{
    if (!XzWorldTransform_IsValid(transform) ||
        !isfinite(meters))
        return 0.0f;

    return meters * transform->units_per_meter;
}

float XzWorldTransform_UnitsToMeters(
    const XzWorldTransform *transform,
    float units)
{
    if (!XzWorldTransform_IsValid(transform) ||
        !isfinite(units))
        return 0.0f;

    return units / transform->units_per_meter;
}

int XzWorldTransform_SelfTest(void)
{
    XzWorldTransform transform;
    XzWorldVec3 source = {2.0f, -3.0f, 4.0f};
    XzWorldVec3 runtime;
    XzWorldVec3 roundtrip;
    static const float unreal_y_flip[9] = {
        1.0f, 0.0f, 0.0f,
        0.0f, -1.0f, 0.0f,
        0.0f, 0.0f, 1.0f
    };

    XzWorldTransform_Init(&transform);

    if (!XzWorldTransform_IsValid(&transform))
        return 0;

    runtime = XzWorldTransform_ToRuntime(&transform, source);
    if (fabsf(runtime.x - 2.0f * XZ_WORLD_UNITS_PER_METER) > 0.001f ||
        fabsf(runtime.y + 3.0f * XZ_WORLD_UNITS_PER_METER) > 0.001f ||
        fabsf(runtime.z - 4.0f * XZ_WORLD_UNITS_PER_METER) > 0.001f)
        return 0;

    roundtrip = XzWorldTransform_ToSourceMeters(&transform, runtime);
    if (fabsf(roundtrip.x - source.x) > 0.0001f ||
        fabsf(roundtrip.y - source.y) > 0.0001f ||
        fabsf(roundtrip.z - source.z) > 0.0001f)
        return 0;

    if (!XzWorldTransform_SetBasis(&transform, unreal_y_flip))
        return 0;

    runtime = XzWorldTransform_ToRuntime(&transform, source);
    if (runtime.y <= 0.0f)
        return 0;

    roundtrip = XzWorldTransform_ToSourceMeters(&transform, runtime);
    if (fabsf(roundtrip.x - source.x) > 0.0001f ||
        fabsf(roundtrip.y - source.y) > 0.0001f ||
        fabsf(roundtrip.z - source.z) > 0.0001f)
        return 0;

    return 1;
}
