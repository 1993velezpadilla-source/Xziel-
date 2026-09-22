#ifndef XZ_GEOMETRY_TAP_H
#define XZ_GEOMETRY_TAP_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_GEOMETRY_MAX_BATCHES 2048u
#define XZ_GEOMETRY_MAX_VERTICES 131072u
#define XZ_GEOMETRY_MAX_INDICES 262144u

typedef enum {
    XZ_GEOMETRY_ALIAS = 0,
    XZ_GEOMETRY_SURFACE,
    XZ_GEOMETRY_SPRITE
} XzGeometryKind;

typedef struct {
    float position[3];
    float uv[2];
} XzGeometryVertex;

typedef struct {
    unsigned int first_vertex;
    unsigned int vertex_count;
    unsigned int first_index;
    unsigned int index_count;
    XzGeometryKind kind;
    int texture_id;
    float modelview[16];
    float projection[16];
} XzGeometryBatch;

typedef struct {
    uint64_t generation;
    XzGeometryBatch batches[XZ_GEOMETRY_MAX_BATCHES];
    XzGeometryVertex vertices[XZ_GEOMETRY_MAX_VERTICES];
    uint32_t indices[XZ_GEOMETRY_MAX_INDICES];

    unsigned int batch_count;
    unsigned int vertex_count;
    unsigned int index_count;

    unsigned int alias_batches;
    unsigned int surface_batches;
    unsigned int sprite_batches;

    unsigned int dropped_batches;
    unsigned int dropped_vertices;
    unsigned int dropped_indices;
} XzGeometryFrame;

void XzGeometryTap_Init(void);
void XzGeometryTap_BeginFrame(uint64_t generation);
void XzGeometryTap_CommitFrame(void);

int XzGeometryTap_CaptureAlias(
    const void *vertices,
    unsigned int vertex_count,
    unsigned int vertex_stride,
    unsigned int xyz_offset,
    unsigned int uv_offset,
    const uint16_t *indices,
    unsigned int index_count,
    int texture_id,
    const float modelview[16],
    const float projection[16]);

int XzGeometryTap_CaptureSurfaceFan(
    const float *source,
    unsigned int count,
    unsigned int stride_floats,
    unsigned int position_offset,
    unsigned int texture_offset,
    int texture_id,
    const float modelview[16],
    const float projection[16]);

int XzGeometryTap_CaptureSpriteQuad(
    const float positions[12],
    const float uvs[8],
    int texture_id,
    const float modelview[16],
    const float projection[16]);

const XzGeometryFrame *XzGeometryTap_GetReadFrame(void);
int XzGeometryTap_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
