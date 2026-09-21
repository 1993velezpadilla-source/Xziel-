#include "xz_pass_targets.h"

#include <string.h>

static int XzAssignWrite(
    XzPassTargetPlan *plan,
    XzPassTarget *target,
    XzGpuHandle handle,
    const XzGpuResourceDesc *desc)
{
    if (!plan || !target || !desc)
        return 0;

    switch (desc->type) {
    case XZ_GPU_RESOURCE_TEXTURE:
        if (target->color != XZ_GPU_INVALID_HANDLE) {
            plan->multiple_color_count++;
            return 0;
        }
        target->color = handle;
        break;

    case XZ_GPU_RESOURCE_DEPTH:
        if (target->depth != XZ_GPU_INVALID_HANDLE) {
            plan->multiple_depth_count++;
            return 0;
        }
        target->depth = handle;
        break;

    case XZ_GPU_RESOURCE_EXTERNAL_SURFACE:
        if (target->external != XZ_GPU_INVALID_HANDLE) {
            plan->multiple_external_count++;
            return 0;
        }
        target->external = handle;
        break;

    case XZ_GPU_RESOURCE_BUFFER:
    case XZ_GPU_RESOURCE_UNKNOWN:
    default:
        plan->invalid_resource_count++;
        return 0;
    }

    target->write_count++;
    return 1;
}

int XzPassTargetPlan_Build(
    XzPassTargetPlan *plan,
    const XzCommandStream *commands,
    XzGpuResourcePool *resources)
{
    XzPassTarget *current = NULL;
    unsigned int i;
    int frame_open = 0;

    if (!plan || !commands || !resources)
        return 0;

    memset(plan, 0, sizeof(*plan));

    if (!XzCommandStream_Validate(commands))
        return 0;

    for (i = 0u; i < commands->count; ++i) {
        const XzCommand *command =
            &commands->commands[i];

        switch (command->op) {
        case XZ_CMD_BEGIN_FRAME:
            if (frame_open || current)
                return 0;
            frame_open = 1;
            break;

        case XZ_CMD_BEGIN_PASS:
            if (!frame_open || current ||
                plan->count >= XZ_PASS_TARGET_MAX)
                return 0;

            current = &plan->passes[plan->count];
            memset(current, 0, sizeof(*current));
            current->pass_index = command->a;
            break;

        case XZ_CMD_RESOURCE_READ:
        {
            const XzGpuResourceDesc *desc;

            if (!current)
                return 0;

            desc = XzGpuResource_Resolve(
                resources,
                (XzGpuHandle)command->c);
            if (!desc) {
                plan->invalid_resource_count++;
                return 0;
            }

            current->read_count++;
            break;
        }

        case XZ_CMD_RESOURCE_WRITE:
        {
            XzGpuHandle handle;
            const XzGpuResourceDesc *desc;

            if (!current)
                return 0;

            handle = (XzGpuHandle)command->c;
            desc = XzGpuResource_Resolve(
                resources, handle);

            if (!desc) {
                plan->invalid_resource_count++;
                return 0;
            }

            if (!XzAssignWrite(
                    plan,
                    current,
                    handle,
                    desc))
                return 0;
            break;
        }

        case XZ_CMD_DRAW_PACKETS:
            if (!current)
                return 0;
            current->draw_count++;
            break;

        case XZ_CMD_END_PASS:
            if (!current ||
                command->a != current->pass_index)
                return 0;
            plan->count++;
            current = NULL;
            break;

        case XZ_CMD_END_FRAME:
            if (!frame_open || current)
                return 0;
            frame_open = 0;
            break;

        case XZ_CMD_NOP:
        default:
            return 0;
        }
    }

    return !frame_open &&
           current == NULL &&
           XzPassTargetPlan_Validate(plan);
}

int XzPassTargetPlan_Validate(
    const XzPassTargetPlan *plan)
{
    unsigned int i;

    if (!plan || plan->count == 0u ||
        plan->count > XZ_PASS_TARGET_MAX ||
        plan->invalid_resource_count != 0u ||
        plan->multiple_color_count != 0u ||
        plan->multiple_depth_count != 0u ||
        plan->multiple_external_count != 0u)
        return 0;

    for (i = 0u; i < plan->count; ++i) {
        const XzPassTarget *target =
            &plan->passes[i];

        if (target->write_count == 0u)
            return 0;

        if (target->external != XZ_GPU_INVALID_HANDLE &&
            (target->color != XZ_GPU_INVALID_HANDLE ||
             target->depth != XZ_GPU_INVALID_HANDLE))
            return 0;
    }

    return 1;
}

int XzPassTargetPlan_SelfTest(void)
{
    XzGpuResourcePool pool;
    XzGpuResourceDesc desc;
    XzGpuHandle color;
    XzGpuHandle depth;
    XzGpuHandle external;
    XzCommandStream stream;
    XzPassTargetPlan plan;

    XzGpuResourcePool_Init(&pool);
    memset(&desc, 0, sizeof(desc));
    memset(&stream, 0, sizeof(stream));

    desc.type = XZ_GPU_RESOURCE_TEXTURE;
    desc.width = 320u;
    desc.height = 180u;
    desc.samples = 1u;
    color = XzGpuResource_Create(&pool, &desc);

    desc.type = XZ_GPU_RESOURCE_DEPTH;
    depth = XzGpuResource_Create(&pool, &desc);

    desc.type = XZ_GPU_RESOURCE_EXTERNAL_SURFACE;
    external = XzGpuResource_Create(&pool, &desc);

    if (color == XZ_GPU_INVALID_HANDLE ||
        depth == XZ_GPU_INVALID_HANDLE ||
        external == XZ_GPU_INVALID_HANDLE)
        return 0;

    stream.content_hash = 0x1234u;
    stream.count = 10u;

    stream.commands[0].op = XZ_CMD_BEGIN_FRAME;

    stream.commands[1].op = XZ_CMD_BEGIN_PASS;
    stream.commands[1].a = 0u;
    stream.commands[2].op = XZ_CMD_RESOURCE_WRITE;
    stream.commands[2].a = 0u;
    stream.commands[2].c = color;
    stream.commands[3].op = XZ_CMD_RESOURCE_WRITE;
    stream.commands[3].a = 0u;
    stream.commands[3].c = depth;
    stream.commands[4].op = XZ_CMD_DRAW_PACKETS;
    stream.commands[5].op = XZ_CMD_END_PASS;
    stream.commands[5].a = 0u;

    stream.commands[6].op = XZ_CMD_BEGIN_PASS;
    stream.commands[6].a = 1u;
    stream.commands[7].op = XZ_CMD_RESOURCE_WRITE;
    stream.commands[7].a = 1u;
    stream.commands[7].c = external;
    stream.commands[8].op = XZ_CMD_END_PASS;
    stream.commands[8].a = 1u;

    stream.commands[9].op = XZ_CMD_END_FRAME;

    if (!XzPassTargetPlan_Build(
            &plan, &stream, &pool))
        return 0;

    if (plan.count != 2u)
        return 0;

    if (plan.passes[0].color != color ||
        plan.passes[0].depth != depth ||
        plan.passes[0].draw_count != 1u)
        return 0;

    if (plan.passes[1].external != external)
        return 0;

    return 1;
}
