#include "../engine/xz/xz_device_caps.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    XzDeviceCaps caps;

    assert(XzDeviceCaps_SelfTest());

    XzDeviceCaps_Init(&caps);
    XzDeviceCaps_SetPlatform(
        &caps, 6, 6144, 60, 33, (3 << 16) | 1, 1);

    assert(caps.allow_gles3);
    assert(caps.allow_vulkan);
    assert(caps.allow_gpu_driven);
    assert(caps.allow_temporal_upscale);
    assert(!caps.allow_high_refresh);
    assert(!caps.allow_ray_query);

    puts("xz_device_caps_test: PASS");
    return 0;
}
