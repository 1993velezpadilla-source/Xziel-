#include "xz_render_graph.h"

#include <string.h>

typedef struct {
    int valid;
    XzRgFormat format;
    unsigned int width;
    unsigned int height;
    unsigned int samples;
    int last_use;
} XzAliasSlotState;

static int XzResourceCompatible(
    const XzRgResourceDesc *a,
    const XzAliasSlotState *slot)
{
    return slot->valid &&
           a->format == slot->format &&
           a->width == slot->width &&
           a->height == slot->height &&
           a->samples == slot->samples;
}

static unsigned int XzPopCount32(uint32_t value)
{
    unsigned int count = 0u;
    while (value) {
        value &= value - 1u;
        count++;
    }
    return count;
}

void XzRenderGraph_Init(XzRenderGraph *graph)
{
    if (!graph)
        return;
    memset(graph, 0, sizeof(*graph));
}

int XzRenderGraph_AddResource(
    XzRenderGraph *graph,
    const XzRgResourceDesc *desc)
{
    unsigned int index;

    if (!graph || !desc)
        return -1;

    if (graph->resource_count >= XZ_RG_MAX_RESOURCES)
        return -1;

    index = graph->resource_count++;
    graph->resources[index] = *desc;
    if (graph->resources[index].samples == 0u)
        graph->resources[index].samples = 1u;

    return (int)index;
}

int XzRenderGraph_AddPass(
    XzRenderGraph *graph,
    const XzRgPassDesc *desc)
{
    unsigned int index;

    if (!graph || !desc)
        return -1;

    if (graph->pass_count >= XZ_RG_MAX_PASSES)
        return -1;

    index = graph->pass_count++;
    graph->passes[index] = *desc;

    return (int)index;
}

static void XzAddEdge(
    unsigned char edges[XZ_RG_MAX_PASSES][XZ_RG_MAX_PASSES],
    unsigned int from,
    unsigned int to)
{
    if (from == to)
        return;
    edges[from][to] = 1u;
}

static int XzBuildDependencies(
    const XzRenderGraph *graph,
    unsigned char edges[XZ_RG_MAX_PASSES][XZ_RG_MAX_PASSES],
    XzRgError *error)
{
    int last_writer[XZ_RG_MAX_RESOURCES];
    int last_access[XZ_RG_MAX_RESOURCES];
    uint32_t valid_mask;
    unsigned int p;
    unsigned int r;

    memset(edges, 0, XZ_RG_MAX_PASSES * XZ_RG_MAX_PASSES);
    for (r = 0u; r < XZ_RG_MAX_RESOURCES; ++r) {
        last_writer[r] = -1;
        last_access[r] = -1;
    }

    valid_mask = graph->resource_count == 32u
        ? 0xffffffffu
        : ((1u << graph->resource_count) - 1u);

    for (p = 0u; p < graph->pass_count; ++p) {
        const XzRgPassDesc *pass = &graph->passes[p];
        uint32_t used = pass->read_mask | pass->write_mask;

        if ((used & ~valid_mask) != 0u) {
            *error = XZ_RG_ERROR_INVALID_MASK;
            return 0;
        }

        for (r = 0u; r < graph->resource_count; ++r) {
            const uint32_t bit = 1u << r;
            const int reads = (pass->read_mask & bit) != 0u;
            const int writes = (pass->write_mask & bit) != 0u;

            if (reads) {
                if (last_writer[r] < 0 &&
                    (graph->resources[r].flags &
                     XZ_RG_RESOURCE_IMPORTED) == 0u) {
                    *error = XZ_RG_ERROR_READ_BEFORE_WRITE;
                    return 0;
                }

                if (last_writer[r] >= 0)
                    XzAddEdge(
                        edges,
                        (unsigned int)last_writer[r],
                        p);

                last_access[r] = (int)p;
            }

            if (writes) {
                if (last_access[r] >= 0)
                    XzAddEdge(
                        edges,
                        (unsigned int)last_access[r],
                        p);

                last_writer[r] = (int)p;
                last_access[r] = (int)p;
            }
        }
    }

    return 1;
}

static int XzTopoSort(
    const XzRenderGraph *graph,
    unsigned char edges[XZ_RG_MAX_PASSES][XZ_RG_MAX_PASSES],
    unsigned int order[XZ_RG_MAX_PASSES])
{
    unsigned int indegree[XZ_RG_MAX_PASSES];
    unsigned char emitted[XZ_RG_MAX_PASSES];
    unsigned int out = 0u;
    unsigned int i;
    unsigned int j;

    memset(indegree, 0, sizeof(indegree));
    memset(emitted, 0, sizeof(emitted));

    for (i = 0u; i < graph->pass_count; ++i)
        for (j = 0u; j < graph->pass_count; ++j)
            if (edges[i][j])
                indegree[j]++;

    while (out < graph->pass_count) {
        int found = -1;

        for (i = 0u; i < graph->pass_count; ++i) {
            if (!emitted[i] && indegree[i] == 0u) {
                found = (int)i;
                break;
            }
        }

        if (found < 0)
            return 0;

        order[out++] = (unsigned int)found;
        emitted[found] = 1u;

        for (j = 0u; j < graph->pass_count; ++j) {
            if (edges[found][j] && indegree[j] > 0u)
                indegree[j]--;
        }
    }

    return 1;
}

static void XzComputeLifetimes(
    const XzRenderGraph *graph,
    XzRenderGraphCompiled *compiled)
{
    unsigned int position;
    unsigned int r;

    for (r = 0u; r < XZ_RG_MAX_RESOURCES; ++r) {
        compiled->first_use[r] = -1;
        compiled->last_use[r] = -1;
        compiled->alias_slot[r] = -1;
    }

    for (position = 0u; position < graph->pass_count; ++position) {
        const unsigned int pass_index =
            compiled->execution_order[position];
        const XzRgPassDesc *pass =
            &graph->passes[pass_index];
        const uint32_t used =
            pass->read_mask | pass->write_mask;

        for (r = 0u; r < graph->resource_count; ++r) {
            const uint32_t bit = 1u << r;
            if ((used & bit) == 0u)
                continue;

            if (compiled->first_use[r] < 0)
                compiled->first_use[r] = (int)position;
            compiled->last_use[r] = (int)position;
        }
    }
}

static void XzAssignTransientAliases(
    const XzRenderGraph *graph,
    XzRenderGraphCompiled *compiled)
{
    XzAliasSlotState slots[XZ_RG_MAX_RESOURCES];
    unsigned int r;

    memset(slots, 0, sizeof(slots));

    for (r = 0u; r < graph->resource_count; ++r) {
        const XzRgResourceDesc *resource =
            &graph->resources[r];
        unsigned int slot;
        int assigned = -1;

        if (resource->flags & XZ_RG_RESOURCE_TILE_LOCAL)
            compiled->tile_local_resource_count++;
        if (resource->flags & XZ_RG_RESOURCE_MEMORYLESS)
            compiled->memoryless_resource_count++;

        if ((resource->flags & XZ_RG_RESOURCE_TRANSIENT) == 0u ||
            (resource->flags & XZ_RG_RESOURCE_IMPORTED) != 0u ||
            (resource->flags & XZ_RG_RESOURCE_PRESERVE) != 0u ||
            compiled->first_use[r] < 0)
            continue;

        for (slot = 0u;
             slot < compiled->alias_slot_count;
             ++slot) {
            if (XzResourceCompatible(resource, &slots[slot]) &&
                slots[slot].last_use < compiled->first_use[r]) {
                assigned = (int)slot;
                break;
            }
        }

        if (assigned < 0) {
            assigned = (int)compiled->alias_slot_count++;
            slots[assigned].valid = 1;
            slots[assigned].format = resource->format;
            slots[assigned].width = resource->width;
            slots[assigned].height = resource->height;
            slots[assigned].samples = resource->samples;
        }

        slots[assigned].last_use = compiled->last_use[r];
        compiled->alias_slot[r] = assigned;
    }

    for (r = 0u; r < graph->pass_count; ++r) {
        uint32_t live_slots = 0u;
        unsigned int resource_index;

        for (resource_index = 0u;
             resource_index < graph->resource_count;
             ++resource_index) {
            const int slot =
                compiled->alias_slot[resource_index];

            if (slot < 0)
                continue;
            if (compiled->first_use[resource_index] <= (int)r &&
                compiled->last_use[resource_index] >= (int)r)
                live_slots |= 1u << (unsigned int)slot;
        }

        {
            const unsigned int live = XzPopCount32(live_slots);
            if (live > compiled->peak_live_transient_slots)
                compiled->peak_live_transient_slots = live;
        }
    }
}

static int XzCanFuse(
    const XzRgPassDesc *previous,
    const XzRgPassDesc *current)
{
    if (previous->flags &
        (XZ_RG_PASS_NEEDS_NEIGHBORHOOD |
         XZ_RG_PASS_NEEDS_HISTORY))
        return 0;
    if ((current->flags &
         XZ_RG_PASS_CAN_FUSE_PREVIOUS) == 0u)
        return 0;
    if ((current->flags &
         XZ_RG_PASS_CURRENT_PIXEL_ONLY) == 0u)
        return 0;
    if ((current->flags &
         XZ_RG_PASS_FRAMEBUFFER_FETCH) == 0u)
        return 0;
    if (current->flags &
        (XZ_RG_PASS_NEEDS_NEIGHBORHOOD |
         XZ_RG_PASS_NEEDS_HISTORY))
        return 0;
    if ((current->read_mask &
         previous->write_mask) == 0u)
        return 0;

    return 1;
}

static void XzBuildFusionGroups(
    const XzRenderGraph *graph,
    XzRenderGraphCompiled *compiled)
{
    unsigned int position;
    unsigned int group = 0u;

    if (graph->pass_count == 0u)
        return;

    compiled->fusion_group[0] = 0u;
    compiled->fusion_group_count = 1u;

    for (position = 1u;
         position < graph->pass_count;
         ++position) {
        const unsigned int prev_index =
            compiled->execution_order[position - 1u];
        const unsigned int current_index =
            compiled->execution_order[position];
        const XzRgPassDesc *prev =
            &graph->passes[prev_index];
        const XzRgPassDesc *current =
            &graph->passes[current_index];

        if (XzCanFuse(prev, current)) {
            compiled->fused_pass_count++;
        } else {
            group++;
            compiled->fusion_group_count++;
        }

        compiled->fusion_group[position] = group;
    }
}

int XzRenderGraph_Compile(
    const XzRenderGraph *graph,
    XzRenderGraphCompiled *compiled)
{
    unsigned char edges[XZ_RG_MAX_PASSES][XZ_RG_MAX_PASSES];
    XzRgError error = XZ_RG_OK;

    if (!graph || !compiled)
        return 0;

    memset(compiled, 0, sizeof(*compiled));
    compiled->resource_count = graph->resource_count;
    compiled->pass_count = graph->pass_count;

    if (graph->resource_count > XZ_RG_MAX_RESOURCES) {
        compiled->error = XZ_RG_ERROR_TOO_MANY_RESOURCES;
        return 0;
    }
    if (graph->pass_count > XZ_RG_MAX_PASSES) {
        compiled->error = XZ_RG_ERROR_TOO_MANY_PASSES;
        return 0;
    }

    if (!XzBuildDependencies(graph, edges, &error)) {
        compiled->error = error;
        return 0;
    }

    if (!XzTopoSort(
            graph,
            edges,
            compiled->execution_order)) {
        compiled->error = XZ_RG_ERROR_CYCLE;
        return 0;
    }

    XzComputeLifetimes(graph, compiled);
    XzAssignTransientAliases(graph, compiled);
    XzBuildFusionGroups(graph, compiled);

    compiled->error = XZ_RG_OK;
    compiled->valid = 1;
    return 1;
}

const char *XzRgError_Name(XzRgError error)
{
    switch (error) {
    case XZ_RG_OK: return "OK";
    case XZ_RG_ERROR_TOO_MANY_RESOURCES:
        return "TOO_MANY_RESOURCES";
    case XZ_RG_ERROR_TOO_MANY_PASSES:
        return "TOO_MANY_PASSES";
    case XZ_RG_ERROR_INVALID_MASK:
        return "INVALID_MASK";
    case XZ_RG_ERROR_READ_BEFORE_WRITE:
        return "READ_BEFORE_WRITE";
    case XZ_RG_ERROR_CYCLE:
        return "CYCLE";
    default:
        return "UNKNOWN";
    }
}

int XzRenderGraph_SelfTest(void)
{
    XzRenderGraph graph;
    XzRenderGraphCompiled compiled;
    XzRgResourceDesc resource;
    XzRgPassDesc pass;
    int scene_color;
    int depth;
    int lit;
    int bloom_temp;
    int swapchain;

    XzRenderGraph_Init(&graph);

    memset(&resource, 0, sizeof(resource));
    resource.width = 1920u;
    resource.height = 1080u;
    resource.samples = 1u;
    resource.format = XZ_RG_FORMAT_RGBA16F;
    resource.flags =
        XZ_RG_RESOURCE_TRANSIENT |
        XZ_RG_RESOURCE_TILE_LOCAL;
    scene_color = XzRenderGraph_AddResource(
        &graph, &resource);

    resource.format = XZ_RG_FORMAT_DEPTH24;
    resource.flags =
        XZ_RG_RESOURCE_TRANSIENT |
        XZ_RG_RESOURCE_TILE_LOCAL |
        XZ_RG_RESOURCE_MEMORYLESS;
    depth = XzRenderGraph_AddResource(
        &graph, &resource);

    resource.format = XZ_RG_FORMAT_RGBA16F;
    resource.flags =
        XZ_RG_RESOURCE_TRANSIENT |
        XZ_RG_RESOURCE_TILE_LOCAL;
    lit = XzRenderGraph_AddResource(
        &graph, &resource);
    bloom_temp = XzRenderGraph_AddResource(
        &graph, &resource);

    resource.format = XZ_RG_FORMAT_RGBA8;
    resource.flags =
        XZ_RG_RESOURCE_IMPORTED |
        XZ_RG_RESOURCE_PRESERVE;
    swapchain = XzRenderGraph_AddResource(
        &graph, &resource);

    if (scene_color < 0 || depth < 0 || lit < 0 ||
        bloom_temp < 0 || swapchain < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.write_mask =
        (1u << (unsigned int)scene_color) |
        (1u << (unsigned int)depth);
    if (XzRenderGraph_AddPass(&graph, &pass) < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.read_mask =
        (1u << (unsigned int)scene_color) |
        (1u << (unsigned int)depth);
    pass.write_mask = 1u << (unsigned int)lit;
    pass.flags =
        XZ_RG_PASS_CURRENT_PIXEL_ONLY |
        XZ_RG_PASS_FRAMEBUFFER_FETCH |
        XZ_RG_PASS_CAN_FUSE_PREVIOUS;
    if (XzRenderGraph_AddPass(&graph, &pass) < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.read_mask = 1u << (unsigned int)lit;
    pass.write_mask = 1u << (unsigned int)bloom_temp;
    pass.flags = XZ_RG_PASS_NEEDS_NEIGHBORHOOD;
    if (XzRenderGraph_AddPass(&graph, &pass) < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.read_mask =
        (1u << (unsigned int)lit) |
        (1u << (unsigned int)bloom_temp);
    pass.write_mask = 1u << (unsigned int)swapchain;
    pass.flags =
        XZ_RG_PASS_CURRENT_PIXEL_ONLY |
        XZ_RG_PASS_FRAMEBUFFER_FETCH |
        XZ_RG_PASS_CAN_FUSE_PREVIOUS;
    if (XzRenderGraph_AddPass(&graph, &pass) < 0)
        return 0;

    if (!XzRenderGraph_Compile(&graph, &compiled))
        return 0;
    if (!compiled.valid ||
        compiled.error != XZ_RG_OK)
        return 0;

    if (compiled.pass_count != 4u ||
        compiled.resource_count != 5u)
        return 0;

    if (compiled.alias_slot[scene_color] < 0 ||
        compiled.alias_slot[bloom_temp] < 0)
        return 0;

    if (compiled.alias_slot[scene_color] !=
        compiled.alias_slot[bloom_temp])
        return 0;

    if (compiled.memoryless_resource_count != 1u)
        return 0;
    if (compiled.tile_local_resource_count != 4u)
        return 0;
    if (compiled.fusion_group_count != 3u)
        return 0;
    if (compiled.fused_pass_count != 1u)
        return 0;
    if (compiled.peak_live_transient_slots != 3u)
        return 0;

    return 1;
}
