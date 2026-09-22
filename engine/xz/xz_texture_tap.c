#include "xz_texture_tap.h"

#include <stdlib.h>
#include <string.h>

typedef struct {
    unsigned int legacy_id;
    unsigned int width;
    unsigned int height;
    uint64_t revision;
    unsigned char *rgba;
    size_t bytes;
    int used;
} XzTextureEntry;

typedef struct {
    XzTextureEntry entries[XZ_TEXTURE_MAX_ENTRIES];
    uint64_t next_revision;
    uint64_t captures;
    uint64_t updates;
    uint64_t resolve_hits;
    uint64_t resolve_misses;
    uint64_t dropped;
    unsigned int resident_count;
    size_t resident_bytes;
    size_t high_water_bytes;
    int initialized;
} XzTextureTapState;

static XzTextureTapState xz_textures;

static XzTextureEntry *XzFindEntry(
    unsigned int legacy_id)
{
    unsigned int i;

    for (i = 0u; i < XZ_TEXTURE_MAX_ENTRIES; ++i) {
        if (xz_textures.entries[i].used &&
            xz_textures.entries[i].legacy_id == legacy_id)
            return &xz_textures.entries[i];
    }

    return NULL;
}

static XzTextureEntry *XzFindFreeEntry(void)
{
    unsigned int i;

    for (i = 0u; i < XZ_TEXTURE_MAX_ENTRIES; ++i) {
        if (!xz_textures.entries[i].used)
            return &xz_textures.entries[i];
    }

    return NULL;
}

void XzTextureTap_Init(void)
{
    if (xz_textures.initialized)
        XzTextureTap_Shutdown();

    memset(&xz_textures, 0, sizeof(xz_textures));
    xz_textures.initialized = 1;
}

void XzTextureTap_Shutdown(void)
{
    unsigned int i;

    for (i = 0u; i < XZ_TEXTURE_MAX_ENTRIES; ++i) {
        free(xz_textures.entries[i].rgba);
        xz_textures.entries[i].rgba = NULL;
    }

    memset(&xz_textures, 0, sizeof(xz_textures));
}

int XzTextureTap_CaptureRgba(
    unsigned int legacy_id,
    const void *rgba,
    unsigned int width,
    unsigned int height)
{
    XzTextureEntry *entry;
    size_t bytes;
    size_t next_resident;
    unsigned char *copy;
    int existed;

    if (!xz_textures.initialized)
        XzTextureTap_Init();

    if (legacy_id == 0u || !rgba ||
        width == 0u || height == 0u)
        return 0;

    if ((size_t)width >
        SIZE_MAX / (size_t)height / 4u) {
        xz_textures.dropped++;
        return 0;
    }

    bytes =
        (size_t)width *
        (size_t)height *
        4u;

    entry = XzFindEntry(legacy_id);
    existed = entry != NULL;

    if (!entry)
        entry = XzFindFreeEntry();

    if (!entry) {
        xz_textures.dropped++;
        return 0;
    }

    next_resident =
        xz_textures.resident_bytes -
        (entry->used ? entry->bytes : 0u) +
        bytes;

    if (next_resident >
        (size_t)XZ_TEXTURE_MAX_RESIDENT_BYTES) {
        xz_textures.dropped++;
        return 0;
    }

    copy = (unsigned char *)realloc(entry->rgba, bytes);
    if (!copy) {
        xz_textures.dropped++;
        return 0;
    }

    memcpy(copy, rgba, bytes);

    if (!entry->used)
        xz_textures.resident_count++;

    entry->legacy_id = legacy_id;
    entry->width = width;
    entry->height = height;
    entry->rgba = copy;
    entry->bytes = bytes;
    entry->used = 1;

    xz_textures.next_revision++;
    if (xz_textures.next_revision == 0u)
        xz_textures.next_revision++;
    entry->revision = xz_textures.next_revision;

    xz_textures.resident_bytes = next_resident;
    if (xz_textures.resident_bytes >
        xz_textures.high_water_bytes)
        xz_textures.high_water_bytes =
            xz_textures.resident_bytes;

    xz_textures.captures++;
    if (existed)
        xz_textures.updates++;

    return 1;
}

int XzTextureTap_Resolve(
    unsigned int legacy_id,
    XzTextureSnapshot *snapshot)
{
    XzTextureEntry *entry;

    if (snapshot)
        memset(snapshot, 0, sizeof(*snapshot));

    if (!xz_textures.initialized ||
        legacy_id == 0u) {
        xz_textures.resolve_misses++;
        return 0;
    }

    entry = XzFindEntry(legacy_id);
    if (!entry || !entry->rgba || entry->bytes == 0u) {
        xz_textures.resolve_misses++;
        return 0;
    }

    if (snapshot) {
        snapshot->legacy_id = entry->legacy_id;
        snapshot->width = entry->width;
        snapshot->height = entry->height;
        snapshot->revision = entry->revision;
        snapshot->rgba = entry->rgba;
        snapshot->bytes = entry->bytes;
    }

    xz_textures.resolve_hits++;
    return 1;
}

void XzTextureTap_GetStats(
    XzTextureTapStats *stats)
{
    if (!stats)
        return;

    memset(stats, 0, sizeof(*stats));
    stats->captures = xz_textures.captures;
    stats->updates = xz_textures.updates;
    stats->resolve_hits = xz_textures.resolve_hits;
    stats->resolve_misses = xz_textures.resolve_misses;
    stats->dropped = xz_textures.dropped;
    stats->resident_count = xz_textures.resident_count;
    stats->resident_bytes = xz_textures.resident_bytes;
    stats->high_water_bytes = xz_textures.high_water_bytes;
}

int XzTextureTap_SelfTest(void)
{
    static const unsigned char pixels_a[16] = {
        255u, 0u, 0u, 255u,
        0u, 255u, 0u, 255u,
        0u, 0u, 255u, 255u,
        255u, 255u, 255u, 255u
    };
    static const unsigned char pixels_b[4] = {
        7u, 11u, 13u, 17u
    };
    XzTextureSnapshot first;
    XzTextureSnapshot second;
    XzTextureTapStats stats;

    XzTextureTap_Init();

    if (!XzTextureTap_CaptureRgba(
            41u, pixels_a, 2u, 2u))
        return 0;

    if (!XzTextureTap_Resolve(41u, &first))
        return 0;

    if (first.width != 2u ||
        first.height != 2u ||
        first.bytes != sizeof(pixels_a) ||
        !first.rgba ||
        memcmp(first.rgba, pixels_a, sizeof(pixels_a)) != 0)
        return 0;

    if (!XzTextureTap_CaptureRgba(
            41u, pixels_b, 1u, 1u))
        return 0;

    if (!XzTextureTap_Resolve(41u, &second))
        return 0;

    if (second.revision <= first.revision ||
        second.width != 1u ||
        second.height != 1u ||
        second.bytes != sizeof(pixels_b) ||
        memcmp(second.rgba, pixels_b, sizeof(pixels_b)) != 0)
        return 0;

    if (XzTextureTap_Resolve(99u, NULL))
        return 0;

    XzTextureTap_GetStats(&stats);
    if (stats.captures != 2u ||
        stats.updates != 1u ||
        stats.resolve_hits != 2u ||
        stats.resolve_misses != 1u ||
        stats.dropped != 0u ||
        stats.resident_count != 1u ||
        stats.resident_bytes != sizeof(pixels_b) ||
        stats.high_water_bytes < sizeof(pixels_a))
        return 0;

    XzTextureTap_Shutdown();
    return 1;
}
