#include "xz_world_transform.h"

#include <assert.h>
#include <math.h>

int main(void)
{
    XzWorldTransform transform;
    XzWorldVec3 source = {-2.489199f, -10.343102f, 1.411515f};
    XzWorldVec3 runtime;
    XzWorldVec3 roundtrip;

    assert(XzWorldTransform_SelfTest());

    XzWorldTransform_Init(&transform);
    assert(XzWorldTransform_IsValid(&transform));

    runtime = XzWorldTransform_ToRuntime(&transform, source);

    assert(fabsf(runtime.x - source.x * XZ_WORLD_UNITS_PER_METER) < 0.002f);
    assert(fabsf(runtime.y - source.y * XZ_WORLD_UNITS_PER_METER) < 0.002f);
    assert(fabsf(runtime.z - source.z * XZ_WORLD_UNITS_PER_METER) < 0.002f);

    roundtrip = XzWorldTransform_ToSourceMeters(&transform, runtime);

    assert(fabsf(roundtrip.x - source.x) < 0.0001f);
    assert(fabsf(roundtrip.y - source.y) < 0.0001f);
    assert(fabsf(roundtrip.z - source.z) < 0.0001f);

    return 0;
}
