#include "xz_command_stream.h"

#include <string.h>

static uint32_t XzCommandHashU32(
    uint32_t hash,
    uint32_t value)
{
    hash ^= value;
    hash *= 16777619u;
    return hash;
}

static uint32_t XzCommandHashU64(
    uint32_t hash,
    uint64_t value)
{
    hash = XzCommandHashU32(
        hash,
        (uint32_t)(value & 0xffffffffu));
    hash = XzCommandHashU32(
        hash,
        (uint32_t)(value >> 32));
    return hash;
}

static int XzCommandPush(
    XzCommandStream *stream,
    XzCommandOp op,
    uint32_t a,
    uint32_t b,
    uint32_t c,
    uint32_t d,
    uint64_t value64)
{
    XzCommand *command;

    if (!stream)
        return 0;

    if (stream->count >= XZ_COMMAND_MAX) {
        stream->overflow_count++;
        return 0;
    }

    command = &stream->commands[stream->count++];
    command->op = op;
    command->a = a;
    command->b = b;
    command->c = c;
    command->d = d;
    command->value64 = value64;

    stream->content_hash =
        XzCommandHashU32(
            stream->content_hash,
            (uint32_t)op);
    stream->content_hash =
        XzCommandHashU32(
            stream->content_hash, a);
    stream->content_hash =
        XzCommandHashU32(
            stream->content_hash, b);
    stream->content_hash =
        XzCommandHashU32(
            stream->content_hash, c);
    stream->content_hash =
        XzCommandHashU32(
            stream->content_hash, d);
    stream->content_hash =
        XzCommandHashU64(
            stream->content_hash,
            value64);

    return 1;
}

void XzCommandStream_Reset(
    XzCommandStream *stream)
{
    if (!stream)
        return;

    memset(stream, 0, sizeof(*stream));
    stream->content_hash = 2166136261u;
}

static int XzEncodeResourceMask(
    XzCommandStream *stream,
    XzCommandOp op,
    uint32_t mask,
    unsigned int pass_index,
    XzGpuResourcePool *resources,
    const XzGpuHandle handles[XZ_RG_MAX_RESOURCES])
{
    unsigned int resource_index;

    for (resource_index = 0u;
         resource_index < XZ_RG_MAX_RESOURCES;
         ++resource_index) {
        uint32_t bit = 1u << resource_index;
        XzGpuHandle handle;
        const XzGpuResourceDesc *desc;

        if ((mask & bit) == 0u)
            continue;

        handle = handles[resource_index];
        desc = XzGpuResource_Resolve(
            resources, handle);

        if (!desc)
            return 0;

        if (!XzCommandPush(
                stream,
                op,
                pass_index,
                resource_index,
                handle,
                desc->flags,
                desc->size_bytes))
            return 0;
    }

    return 1;
}

int XzCommandStream_EncodeFrame(
    XzCommandStream *stream,
    const XzRenderGraph *graph,
    const XzRenderGraphCompiled *compiled,
    XzGpuResourcePool *resources,
    const XzGpuHandle resource_handles[XZ_RG_MAX_RESOURCES],
    const XzRenderPlan *plan)
{
    unsigned int position;

    if (!stream || !graph || !compiled ||
        !resources || !resource_handles || !plan)
        return 0;

    XzCommandStream_Reset(stream);

    if (!compiled->valid ||
        compiled->error != XZ_RG_OK ||
        !XzRenderPlan_Validate(plan))
        return 0;

    if (!XzCommandPush(
            stream,
            XZ_CMD_BEGIN_FRAME,
            (uint32_t)plan->generation,
            (uint32_t)plan->source_frame,
            plan->packet_count,
            plan->admitted_lights,
            (uint64_t)plan->content_hash))
        return 0;

    for (position = 0u;
         position < compiled->pass_count;
         ++position) {
        const unsigned int pass_index =
            compiled->execution_order[position];
        const XzRgPassDesc *pass =
            &graph->passes[pass_index];

        if (!XzCommandPush(
                stream,
                XZ_CMD_BEGIN_PASS,
                pass_index,
                compiled->fusion_group[position],
                pass->flags,
                position,
                0u))
            return 0;

        if (!XzEncodeResourceMask(
                stream,
                XZ_CMD_RESOURCE_READ,
                pass->read_mask,
                pass_index,
                resources,
                resource_handles))
            return 0;

        if (!XzEncodeResourceMask(
                stream,
                XZ_CMD_RESOURCE_WRITE,
                pass->write_mask,
                pass_index,
                resources,
                resource_handles))
            return 0;

        /*
         * The bootstrap graph's first execution pass owns scene geometry.
         * Later graph versions can make draw ownership explicit per pass.
         */
        if (position == 0u &&
            plan->packet_count > 0u) {
            if (!XzCommandPush(
                    stream,
                    XZ_CMD_DRAW_PACKETS,
                    plan->packet_count,
                    plan->full_animation_count,
                    plan->shadow_count,
                    plan->premium_vfx_count,
                    (uint64_t)plan->content_hash))
                return 0;
        }

        if (!XzCommandPush(
                stream,
                XZ_CMD_END_PASS,
                pass_index,
                compiled->fusion_group[position],
                0u,
                0u,
                0u))
            return 0;
    }

    if (!XzCommandPush(
            stream,
            XZ_CMD_END_FRAME,
            (uint32_t)plan->generation,
            stream->count,
            0u,
            0u,
            (uint64_t)plan->content_hash))
        return 0;

    return stream->overflow_count == 0u;
}

int XzCommandStream_Validate(
    const XzCommandStream *stream)
{
    unsigned int i;
    int frame_open = 0;
    int pass_open = 0;
    unsigned int begin_frames = 0u;
    unsigned int end_frames = 0u;

    if (!stream || stream->count < 2u ||
        stream->count > XZ_COMMAND_MAX ||
        stream->overflow_count != 0u ||
        stream->content_hash == 0u)
        return 0;

    for (i = 0u; i < stream->count; ++i) {
        const XzCommand *command =
            &stream->commands[i];

        switch (command->op) {
        case XZ_CMD_BEGIN_FRAME:
            if (frame_open || pass_open)
                return 0;
            frame_open = 1;
            begin_frames++;
            break;

        case XZ_CMD_BEGIN_PASS:
            if (!frame_open || pass_open)
                return 0;
            pass_open = 1;
            break;

        case XZ_CMD_RESOURCE_READ:
        case XZ_CMD_RESOURCE_WRITE:
        case XZ_CMD_DRAW_PACKETS:
            if (!frame_open || !pass_open)
                return 0;
            break;

        case XZ_CMD_END_PASS:
            if (!frame_open || !pass_open)
                return 0;
            pass_open = 0;
            break;

        case XZ_CMD_END_FRAME:
            if (!frame_open || pass_open)
                return 0;
            frame_open = 0;
            end_frames++;
            break;

        case XZ_CMD_NOP:
        default:
            return 0;
        }
    }

    return !frame_open &&
           !pass_open &&
           begin_frames == 1u &&
           end_frames == 1u;
}

const char *XzCommandOp_Name(
    XzCommandOp op)
{
    switch (op) {
    case XZ_CMD_NOP: return "NOP";
    case XZ_CMD_BEGIN_FRAME: return "BEGIN_FRAME";
    case XZ_CMD_BEGIN_PASS: return "BEGIN_PASS";
    case XZ_CMD_RESOURCE_READ: return "RESOURCE_READ";
    case XZ_CMD_RESOURCE_WRITE: return "RESOURCE_WRITE";
    case XZ_CMD_DRAW_PACKETS: return "DRAW_PACKETS";
    case XZ_CMD_END_PASS: return "END_PASS";
    case XZ_CMD_END_FRAME: return "END_FRAME";
    default: return "UNKNOWN";
    }
}

int XzCommandStream_SelfTest(void)
{
    XzRenderGraph graph;
    XzRenderGraphCompiled compiled;
    XzRgResourceDesc rg_desc;
    XzRgPassDesc pass;
    XzGpuResourcePool pool;
    XzGpuResourceDesc gpu_desc;
    XzGpuHandle handles[XZ_RG_MAX_RESOURCES];
    XzRenderPlan plan;
    XzCommandStream stream;
    int color;
    int swapchain;

    memset(handles, 0, sizeof(handles));
    memset(&plan, 0, sizeof(plan));

    XzRenderGraph_Init(&graph);

    memset(&rg_desc, 0, sizeof(rg_desc));
    rg_desc.width = 320u;
    rg_desc.height = 180u;
    rg_desc.format = XZ_RG_FORMAT_RGBA8;
    rg_desc.flags = XZ_RG_RESOURCE_TRANSIENT;
    color = XzRenderGraph_AddResource(
        &graph, &rg_desc);

    rg_desc.flags =
        XZ_RG_RESOURCE_IMPORTED |
        XZ_RG_RESOURCE_PRESERVE;
    swapchain = XzRenderGraph_AddResource(
        &graph, &rg_desc);

    if (color < 0 || swapchain < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.write_mask = 1u << (unsigned int)color;
    if (XzRenderGraph_AddPass(&graph, &pass) < 0)
        return 0;

    memset(&pass, 0, sizeof(pass));
    pass.read_mask = 1u << (unsigned int)color;
    pass.write_mask = 1u << (unsigned int)swapchain;
    if (XzRenderGraph_AddPass(&graph, &pass) < 0)
        return 0;

    if (!XzRenderGraph_Compile(
            &graph, &compiled))
        return 0;

    XzGpuResourcePool_Init(&pool);
    memset(&gpu_desc, 0, sizeof(gpu_desc));
    gpu_desc.type = XZ_GPU_RESOURCE_TEXTURE;
    gpu_desc.width = 320u;
    gpu_desc.height = 180u;
    gpu_desc.samples = 1u;
    gpu_desc.size_bytes = 320u * 180u * 4u;

    handles[color] =
        XzGpuResource_Create(
            &pool, &gpu_desc);

    gpu_desc.type =
        XZ_GPU_RESOURCE_EXTERNAL_SURFACE;
    gpu_desc.flags = XZ_GPU_RESOURCE_IMPORTED;
    handles[swapchain] =
        XzGpuResource_Create(
            &pool, &gpu_desc);

    if (handles[color] == XZ_GPU_INVALID_HANDLE ||
        handles[swapchain] == XZ_GPU_INVALID_HANDLE)
        return 0;

    plan.generation = 7u;
    plan.source_frame = 9;
    plan.packet_count = 1u;
    plan.near_count = 1u;
    plan.packets[0].kind =
        (unsigned char)XZ_PRESENT_ALIAS;
    plan.packets[0].lod =
        (unsigned char)XZ_RENDER_LOD_NEAR;
    plan.content_hash = 0x12345678u;

    if (!XzCommandStream_EncodeFrame(
            &stream,
            &graph,
            &compiled,
            &pool,
            handles,
            &plan))
        return 0;

    if (!XzCommandStream_Validate(&stream))
        return 0;

    if (stream.count != 10u)
        return 0;

    if (stream.commands[0].op !=
        XZ_CMD_BEGIN_FRAME)
        return 0;

    if (stream.commands[
            stream.count - 1u].op !=
        XZ_CMD_END_FRAME)
        return 0;

    return 1;
}
