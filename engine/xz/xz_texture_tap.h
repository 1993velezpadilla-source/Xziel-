#ifndef XZ_TEXTURE_TAP_H
#define XZ_TEXTURE_TAP_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_TEXTURE_MAX_ENTRIES 1024u
#define XZ_TEXTURE_MAX_RESIDENT_BYTES (96u * 1024u * 1024u)

typedef struct {
    unsigned int legacy_id;
    unsigned int width;
    unsigned int height;
    uint64_t revision;
    const unsigned char *rgba;
    size_t bytes;
} XzTextureSnapshot;

typedef struct {
    uint64_t captures;
    uint64_t updates;
    uint64_t resolve_hits;
    uint64_t resolve_misses;
    uint64_t dropped;
    unsigned int resident_count;
    size_t resident_bytes;
    size_t high_water_bytes;
} XzTextureTapStats;

void XzTextureTap_Init(void);
void XzTextureTap_Shutdown(void);

int XzTextureTap_CaptureRgba(
    unsigned int legacy_id,
    const void *rgba,
    unsigned int width,
    unsigned int height);

int XzTextureTap_Resolve(
    unsigned int legacy_id,
    XzTextureSnapshot *snapshot);

void XzTextureTap_GetStats(
    XzTextureTapStats *stats);

int XzTextureTap_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
