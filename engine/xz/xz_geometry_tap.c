#include "xz_geometry_tap.h"

#include <string.h>

typedef struct {
    XzGeometryFrame frames[2];
    unsigned int write_index;
    unsigned int read_index;
} XzGeometryTapState;

static XzGeometryTapState xz_geometry;
static int xz_geometry_capture_enabled = 1;

static void XzCopyMatrix(float dst[16], const float src[16])
{
    if (src)
        memcpy(dst, src, 16u * sizeof(float));
    else {
        unsigned int i;
        memset(dst, 0, 16u * sizeof(float));
        for (i = 0u; i < 4u; ++i)
            dst[i * 5u] = 1.0f;
    }
}

static void XzCopyRenderState(
    XzGeometryRenderState *dst,
    const XzGeometryRenderState *src)
{
    if (!dst)
        return;

    if (src) {
        *dst = *src;
        return;
    }

    memset(dst, 0, sizeof(*dst));
    dst->color[0] = 1.0f;
    dst->color[1] = 1.0f;
    dst->color[2] = 1.0f;
    dst->color[3] = 1.0f;
    dst->blend_src = 0x0302u;       /* GL_SRC_ALPHA */
    dst->blend_dst = 0x0303u;       /* GL_ONE_MINUS_SRC_ALPHA */
    dst->depth_write = 1u;
    dst->depth_func = 0x0203u;      /* GL_LEQUAL */
    dst->alpha_func = 0x0204u;      /* GL_GREATER */
    dst->alpha_ref = 0.666f;
    dst->texture_env_mode = 0x2100u;/* GL_MODULATE */
}

static XzGeometryFrame *XzWriteFrame(void)
{
    return &xz_geometry.frames[xz_geometry.write_index];
}

static int XzReserve(
    XzGeometryFrame *frame,
    unsigned int vertices,
    unsigned int indices)
{
    if (!frame)
        return 0;

    if (frame->batch_count >= XZ_GEOMETRY_MAX_BATCHES) {
        frame->dropped_batches++;
        return 0;
    }

    if (frame->vertex_count + vertices >
        XZ_GEOMETRY_MAX_VERTICES) {
        frame->dropped_vertices += vertices;
        return 0;
    }

    if (frame->index_count + indices >
        XZ_GEOMETRY_MAX_INDICES) {
        frame->dropped_indices += indices;
        return 0;
    }

    return 1;
}

static XzGeometryBatch *XzBeginBatch(
    XzGeometryFrame *frame,
    XzGeometryKind kind,
    unsigned int vertices,
    unsigned int indices,
    int texture_id,
    const XzGeometryRenderState *state,
    const float modelview[16],
    const float projection[16])
{
    XzGeometryBatch *batch;

    if (!xz_geometry_capture_enabled)
        return NULL;

    if (!XzReserve(frame, vertices, indices))
        return NULL;

    batch = &frame->batches[frame->batch_count++];
    memset(batch, 0, sizeof(*batch));

    batch->first_vertex = frame->vertex_count;
    batch->vertex_count = vertices;
    batch->first_index = frame->index_count;
    batch->index_count = indices;
    batch->kind = kind;
    batch->texture_id = texture_id;
    XzCopyRenderState(&batch->state, state);
    XzCopyMatrix(batch->modelview, modelview);
    XzCopyMatrix(batch->projection, projection);

    if (kind == XZ_GEOMETRY_ALIAS)
        frame->alias_batches++;
    else if (kind == XZ_GEOMETRY_SURFACE)
        frame->surface_batches++;
    else if (kind == XZ_GEOMETRY_SPRITE)
        frame->sprite_batches++;

    return batch;
}

void XzGeometryTap_Init(void)
{
    memset(&xz_geometry, 0, sizeof(xz_geometry));
    xz_geometry.write_index = 0u;
    xz_geometry.read_index = 1u;
}

void XzGeometryTap_BeginFrame(uint64_t generation)
{
    XzGeometryFrame *frame = XzWriteFrame();

    if (!frame)
        return;

    frame->generation = generation;
    frame->batch_count = 0u;
    frame->vertex_count = 0u;
    frame->index_count = 0u;
    frame->alias_batches = 0u;
    frame->surface_batches = 0u;
    frame->sprite_batches = 0u;
    frame->dropped_batches = 0u;
    frame->dropped_vertices = 0u;
    frame->dropped_indices = 0u;
}

void XzGeometryTap_CommitFrame(void)
{
    unsigned int published = xz_geometry.write_index;
    xz_geometry.read_index = published;
    xz_geometry.write_index = published ^ 1u;
}

void XzGeometryTap_SetCaptureEnabled(int enabled)
{
    xz_geometry_capture_enabled = enabled ? 1 : 0;
}

const XzGeometryFrame *XzGeometryTap_GetReadFrame(void)
{
    return &xz_geometry.frames[xz_geometry.read_index];
}

const XzGeometryFrame *XzGeometryTap_GetWriteFrame(void)
{
    return &xz_geometry.frames[xz_geometry.write_index];
}

int XzGeometryTap_CaptureAlias(
    const void *vertices,
    unsigned int vertex_count,
    unsigned int vertex_stride,
    unsigned int xyz_offset,
    unsigned int uv_offset,
    const uint16_t *indices,
    unsigned int index_count,
    int texture_id,
    const XzGeometryRenderState *state,
    const float modelview[16],
    const float projection[16])
{
    XzGeometryFrame *frame = XzWriteFrame();
    XzGeometryBatch *batch;
    unsigned int i;

    if (!vertices || !indices ||
        vertex_stride == 0u ||
        vertex_count == 0u ||
        index_count == 0u)
        return 0;

    batch = XzBeginBatch(
        frame,
        XZ_GEOMETRY_ALIAS,
        vertex_count,
        index_count,
        texture_id,
        state,
        modelview,
        projection);
    if (!batch)
        return 0;

    for (i = 0u; i < vertex_count; ++i) {
        const unsigned char *base =
            (const unsigned char *)vertices +
            (size_t)i * vertex_stride;
        const float *uv =
            (const float *)(const void *)(base + uv_offset);
        const int16_t *xyz =
            (const int16_t *)(const void *)(base + xyz_offset);
        XzGeometryVertex *out =
            &frame->vertices[frame->vertex_count + i];

        out->position[0] = (float)xyz[0] / 128.0f;
        out->position[1] = (float)xyz[1] / 128.0f;
        out->position[2] = (float)xyz[2] / 128.0f;
        out->uv[0] = uv[0];
        out->uv[1] = uv[1];
    }

    for (i = 0u; i < index_count; ++i)
        frame->indices[frame->index_count + i] =
            (uint32_t)indices[i] + batch->first_vertex;

    frame->vertex_count += vertex_count;
    frame->index_count += index_count;
    return 1;
}

int XzGeometryTap_CaptureIndexedFloat(
    const void *vertices,
    unsigned int vertex_count,
    unsigned int vertex_stride,
    unsigned int xyz_offset,
    unsigned int uv_offset,
    const uint16_t *indices,
    unsigned int index_count,
    int texture_id,
    const XzGeometryRenderState *state,
    const float modelview[16],
    const float projection[16])
{
    XzGeometryFrame *frame = XzWriteFrame();
    XzGeometryBatch *batch;
    unsigned int i;

    if (!vertices || !indices ||
        vertex_stride == 0u ||
        vertex_count == 0u ||
        index_count == 0u)
        return 0;

    batch = XzBeginBatch(
        frame,
        XZ_GEOMETRY_SURFACE,
        vertex_count,
        index_count,
        texture_id,
        state,
        modelview,
        projection);
    if (!batch)
        return 0;

    for (i = 0u; i < vertex_count; ++i) {
        const unsigned char *base =
            (const unsigned char *)vertices +
            (size_t)i * vertex_stride;
        const float *xyz =
            (const float *)(const void *)(base + xyz_offset);
        const float *uv =
            (const float *)(const void *)(base + uv_offset);
        XzGeometryVertex *out =
            &frame->vertices[frame->vertex_count + i];

        out->position[0] = xyz[0];
        out->position[1] = xyz[1];
        out->position[2] = xyz[2];
        out->uv[0] = uv[0];
        out->uv[1] = uv[1];
    }

    for (i = 0u; i < index_count; ++i)
        frame->indices[frame->index_count + i] =
            (uint32_t)indices[i] + batch->first_vertex;

    frame->vertex_count += vertex_count;
    frame->index_count += index_count;
    return 1;
}

int XzGeometryTap_CaptureSurfaceFan(
    const float *source,
    unsigned int count,
    unsigned int stride_floats,
    unsigned int position_offset,
    unsigned int texture_offset,
    int texture_id,
    const XzGeometryRenderState *state,
    const float modelview[16],
    const float projection[16])
{
    XzGeometryFrame *frame = XzWriteFrame();
    XzGeometryBatch *batch;
    unsigned int index_count;
    unsigned int i;
    unsigned int out_index;

    if (!source || count < 3u ||
        stride_floats < 3u ||
        position_offset + 2u >= stride_floats ||
        texture_offset + 1u >= stride_floats)
        return 0;

    index_count = (count - 2u) * 3u;
    batch = XzBeginBatch(
        frame,
        XZ_GEOMETRY_SURFACE,
        count,
        index_count,
        texture_id,
        state,
        modelview,
        projection);
    if (!batch)
        return 0;

    for (i = 0u; i < count; ++i) {
        const float *in =
            source + i * stride_floats;
        XzGeometryVertex *out =
            &frame->vertices[frame->vertex_count + i];

        out->position[0] = in[position_offset + 0u];
        out->position[1] = in[position_offset + 1u];
        out->position[2] = in[position_offset + 2u];
        out->uv[0] = in[texture_offset];
        out->uv[1] = in[texture_offset + 1u];
    }

    out_index = frame->index_count;
    for (i = 0u; i + 2u < count; ++i) {
        frame->indices[out_index++] =
            (uint32_t)batch->first_vertex;
        frame->indices[out_index++] =
            (uint32_t)(batch->first_vertex + i + 1u);
        frame->indices[out_index++] =
            (uint32_t)(batch->first_vertex + i + 2u);
    }

    frame->vertex_count += count;
    frame->index_count += index_count;
    return 1;
}

int XzGeometryTap_CaptureSpriteQuad(
    const float positions[12],
    const float uvs[8],
    int texture_id,
    const XzGeometryRenderState *state,
    const float modelview[16],
    const float projection[16])
{
    static const uint32_t local_indices[6] = {
        0u, 1u, 2u, 0u, 2u, 3u
    };
    XzGeometryFrame *frame = XzWriteFrame();
    XzGeometryBatch *batch;
    unsigned int i;

    if (!positions || !uvs)
        return 0;

    batch = XzBeginBatch(
        frame,
        XZ_GEOMETRY_SPRITE,
        4u,
        6u,
        texture_id,
        state,
        modelview,
        projection);
    if (!batch)
        return 0;

    for (i = 0u; i < 4u; ++i) {
        XzGeometryVertex *out =
            &frame->vertices[frame->vertex_count + i];
        out->position[0] = positions[i * 3u + 0u];
        out->position[1] = positions[i * 3u + 1u];
        out->position[2] = positions[i * 3u + 2u];
        out->uv[0] = uvs[i * 2u + 0u];
        out->uv[1] = uvs[i * 2u + 1u];
    }

    for (i = 0u; i < 6u; ++i)
        frame->indices[frame->index_count + i] =
            (uint32_t)(batch->first_vertex + local_indices[i]);

    frame->vertex_count += 4u;
    frame->index_count += 6u;
    return 1;
}

int XzGeometryTap_SelfTest(void)
{
    static const struct {
        float uv[2];
        int16_t xyz[3];
        int16_t pad;
    } alias_vertices[3] = {
        {{0.0f, 0.0f}, {128, 0, 0}, 0},
        {{1.0f, 0.0f}, {0, 128, 0}, 0},
        {{0.0f, 1.0f}, {0, 0, 128}, 0}
    };
    static const uint16_t alias_indices[3] = {0u, 1u, 2u};
    static const float fan[20] = {
        0,0,0,0,0,
        1,0,0,1,0,
        1,1,0,1,1,
        0,1,0,0,1
    };
    const XzGeometryFrame *frame;

    XzGeometryTap_Init();
    XzGeometryTap_BeginFrame(7u);

    if (!XzGeometryTap_CaptureAlias(
            alias_vertices,
            3u,
            sizeof(alias_vertices[0]),
            2u * sizeof(float),
            0u,
            alias_indices,
            3u,
            4,
            NULL,
            NULL,
            NULL))
        return 0;

    if (!XzGeometryTap_CaptureSurfaceFan(
            fan, 4u, 5u, 0u, 3u, 8, NULL, NULL, NULL))
        return 0;

    XzGeometryTap_CommitFrame();
    frame = XzGeometryTap_GetReadFrame();

    if (frame->generation != 7u ||
        frame->batch_count != 2u ||
        frame->vertex_count != 7u ||
        frame->index_count != 9u ||
        frame->alias_batches != 1u ||
        frame->surface_batches != 1u ||
        frame->dropped_batches != 0u ||
        frame->dropped_vertices != 0u ||
        frame->dropped_indices != 0u)
        return 0;

    if (frame->vertices[0].position[0] != 1.0f)
        return 0;

    if (frame->batches[0].state.color[0] != 1.0f ||
        frame->batches[0].state.depth_write != 1u ||
        frame->batches[0].state.depth_func != 0x0203u ||
        frame->batches[0].state.texture_env_mode != 0x2100u)
        return 0;

    return 1;
}
