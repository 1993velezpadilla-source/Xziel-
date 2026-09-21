#include "xz_gles3_resource_plan.h"
#include "xz_render_graph.h"

#include <string.h>

static unsigned int XzClampDimension(
    unsigned int value,
    unsigned int limit)
{
    if (value == 0u)
        value = 1u;

    if (limit == 0u)
        return value;

    return value < limit ? value : limit;
}

static unsigned int XzBytesPerPixel(
    uint32_t format)
{
    switch ((XzRgFormat)format) {
    case XZ_RG_FORMAT_RGBA16F:
        return 8u;
    case XZ_RG_FORMAT_RG16F:
        return 4u;
    case XZ_RG_FORMAT_DEPTH16:
        return 2u;
    case XZ_RG_FORMAT_DEPTH24:
        return 4u;
    case XZ_RG_FORMAT_RGBA8:
        return 4u;
    case XZ_RG_FORMAT_UNKNOWN:
    default:
        return 4u;
    }
}

int XzGles3ResourcePlan_Build(
    const XzGpuResourceDesc *desc,
    unsigned int max_shadow_dimension,
    XzGles3ResourceSpec *spec)
{
    unsigned int bpp;

    if (!desc || !spec)
        return 0;

    memset(spec, 0, sizeof(*spec));

    switch (desc->type) {
    case XZ_GPU_RESOURCE_TEXTURE:
        spec->kind = XZ_G3_RESOURCE_TEXTURE_2D;
        break;

    case XZ_GPU_RESOURCE_DEPTH:
        spec->kind =
            XZ_G3_RESOURCE_DEPTH_TEXTURE;
        break;

    case XZ_GPU_RESOURCE_EXTERNAL_SURFACE:
        spec->kind =
            XZ_G3_RESOURCE_EXTERNAL_SURFACE;
        break;

    case XZ_GPU_RESOURCE_BUFFER:
    case XZ_GPU_RESOURCE_UNKNOWN:
    default:
        return 0;
    }

    bpp = XzBytesPerPixel(desc->format);

    spec->logical_format = desc->format;
    spec->flags = desc->flags;
    spec->logical_width =
        desc->width > 0u ? desc->width : 1u;
    spec->logical_height =
        desc->height > 0u ? desc->height : 1u;
    spec->samples =
        desc->samples > 0u ? desc->samples : 1u;
    spec->bytes_per_pixel = bpp;

    if (spec->kind ==
        XZ_G3_RESOURCE_EXTERNAL_SURFACE) {
        spec->physical_width = 1u;
        spec->physical_height = 1u;
        spec->physical_bytes = 0u;
    } else {
        spec->physical_width =
            XzClampDimension(
                spec->logical_width,
                max_shadow_dimension);
        spec->physical_height =
            XzClampDimension(
                spec->logical_height,
                max_shadow_dimension);

        spec->physical_bytes =
            (uint64_t)spec->physical_width *
            (uint64_t)spec->physical_height *
            (uint64_t)spec->samples *
            (uint64_t)bpp;
    }

    spec->logical_bytes =
        desc->size_bytes > 0u
            ? desc->size_bytes
            : (uint64_t)spec->logical_width *
              (uint64_t)spec->logical_height *
              (uint64_t)spec->samples *
              (uint64_t)bpp;

    return 1;
}

int XzGles3ResourcePlan_SelfTest(void)
{
    XzGpuResourceDesc desc;
    XzGles3ResourceSpec spec;

    memset(&desc, 0, sizeof(desc));
    desc.type = XZ_GPU_RESOURCE_TEXTURE;
    desc.format = XZ_RG_FORMAT_RGBA16F;
    desc.width = 2400u;
    desc.height = 1080u;
    desc.samples = 1u;
    desc.size_bytes =
        2400ull * 1080ull * 8ull;

    if (!XzGles3ResourcePlan_Build(
            &desc, 128u, &spec))
        return 0;

    if (spec.kind != XZ_G3_RESOURCE_TEXTURE_2D ||
        spec.physical_width != 128u ||
        spec.physical_height != 128u ||
        spec.bytes_per_pixel != 8u ||
        spec.logical_bytes !=
            2400ull * 1080ull * 8ull ||
        spec.physical_bytes !=
            128ull * 128ull * 8ull)
        return 0;

    desc.type = XZ_GPU_RESOURCE_DEPTH;
    desc.format = XZ_RG_FORMAT_DEPTH24;

    if (!XzGles3ResourcePlan_Build(
            &desc, 64u, &spec))
        return 0;

    if (spec.kind !=
            XZ_G3_RESOURCE_DEPTH_TEXTURE ||
        spec.physical_width != 64u ||
        spec.physical_height != 64u ||
        spec.bytes_per_pixel != 4u)
        return 0;

    desc.type = XZ_GPU_RESOURCE_EXTERNAL_SURFACE;
    desc.format = XZ_RG_FORMAT_RGBA8;

    if (!XzGles3ResourcePlan_Build(
            &desc, 64u, &spec))
        return 0;

    if (spec.kind !=
            XZ_G3_RESOURCE_EXTERNAL_SURFACE ||
        spec.physical_bytes != 0u)
        return 0;

    desc.type = XZ_GPU_RESOURCE_BUFFER;
    if (XzGles3ResourcePlan_Build(
            &desc, 64u, &spec))
        return 0;

    return 1;
}
