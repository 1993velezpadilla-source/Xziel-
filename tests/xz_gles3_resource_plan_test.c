#include "../engine/xz/xz_gles3_resource_plan.h"
#include "../engine/xz/xz_render_graph.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    XzGpuResourceDesc desc;
    XzGles3ResourceSpec spec;

    assert(XzGles3ResourcePlan_SelfTest());

    memset(&desc, 0, sizeof(desc));
    desc.type = XZ_GPU_RESOURCE_TEXTURE;
    desc.format = XZ_RG_FORMAT_RGBA8;
    desc.width = 32u;
    desc.height = 16u;
    desc.samples = 1u;

    assert(XzGles3ResourcePlan_Build(
        &desc, 128u, &spec));

    assert(spec.physical_width == 32u);
    assert(spec.physical_height == 16u);
    assert(spec.physical_bytes ==
           32ull * 16ull * 4ull);

    puts("xz_gles3_resource_plan_test: PASS");
    return 0;
}
