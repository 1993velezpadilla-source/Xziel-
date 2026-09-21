#include "xz_pass_inputs.h"

#include <string.h>

int XzPassInputPlan_Build(
    XzPassInputPlan *plan,
    const XzCommandStream *commands,
    XzGpuResourcePool *resources)
{
    XzPassInput *current = NULL;
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
                plan->count >= XZ_PASS_INPUT_MAX)
                return 0;

            current = &plan->passes[plan->count];
            memset(current, 0, sizeof(*current));
            current->pass_index = command->a;
            break;

        case XZ_CMD_RESOURCE_READ:
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

            if (desc->type ==
                XZ_GPU_RESOURCE_EXTERNAL_SURFACE) {
                plan->external_read_count++;
                return 0;
            }

            if (desc->type != XZ_GPU_RESOURCE_TEXTURE &&
                desc->type != XZ_GPU_RESOURCE_DEPTH) {
                plan->invalid_resource_count++;
                return 0;
            }

            if (current->count >=
                XZ_PASS_INPUTS_PER_PASS) {
                plan->overflow_count++;
                return 0;
            }

            current->handles[current->count] = handle;
            current->types[current->count] = desc->type;
            current->count++;
            plan->total_inputs++;

            if (current->count >
                plan->max_inputs_per_pass)
                plan->max_inputs_per_pass =
                    current->count;
            break;
        }

        case XZ_CMD_RESOURCE_WRITE:
        case XZ_CMD_DRAW_PACKETS:
            if (!current)
                return 0;
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
           XzPassInputPlan_Validate(plan);
}

int XzPassInputPlan_Validate(
    const XzPassInputPlan *plan)
{
    unsigned int i;

    if (!plan || plan->count == 0u ||
        plan->count > XZ_PASS_INPUT_MAX ||
        plan->invalid_resource_count != 0u ||
        plan->overflow_count != 0u ||
        plan->external_read_count != 0u ||
        plan->max_inputs_per_pass >
            XZ_PASS_INPUTS_PER_PASS)
        return 0;

    for (i = 0u; i < plan->count; ++i) {
        const XzPassInput *input =
            &plan->passes[i];

        if (input->count >
            XZ_PASS_INPUTS_PER_PASS)
            return 0;
    }

    return 1;
}

const XzPassInput *XzPassInputPlan_Find(
    const XzPassInputPlan *plan,
    unsigned int pass_index)
{
    unsigned int i;

    if (!plan)
        return NULL;

    for (i = 0u; i < plan->count; ++i) {
        if (plan->passes[i].pass_index ==
            pass_index)
            return &plan->passes[i];
    }

    return NULL;
}

int XzPassInputPlan_SelfTest(void)
{
    XzGpuResourcePool pool;
    XzGpuResourceDesc desc;
    XzGpuHandle color;
    XzGpuHandle depth;
    XzCommandStream stream;
    XzPassInputPlan plan;

    XzGpuResourcePool_Init(&pool);
    memset(&desc, 0, sizeof(desc));
    memset(&stream, 0, sizeof(stream));

    desc.type = XZ_GPU_RESOURCE_TEXTURE;
    color = XzGpuResource_Create(&pool, &desc);

    desc.type = XZ_GPU_RESOURCE_DEPTH;
    depth = XzGpuResource_Create(&pool, &desc);

    if (color == XZ_GPU_INVALID_HANDLE ||
        depth == XZ_GPU_INVALID_HANDLE)
        return 0;

    stream.content_hash = 0x55443322u;
    stream.count = 8u;

    stream.commands[0].op = XZ_CMD_BEGIN_FRAME;
    stream.commands[1].op = XZ_CMD_BEGIN_PASS;
    stream.commands[1].a = 4u;

    stream.commands[2].op = XZ_CMD_RESOURCE_READ;
    stream.commands[2].a = 4u;
    stream.commands[2].c = color;

    stream.commands[3].op = XZ_CMD_RESOURCE_READ;
    stream.commands[3].a = 4u;
    stream.commands[3].c = depth;

    stream.commands[4].op = XZ_CMD_RESOURCE_WRITE;
    stream.commands[4].a = 4u;
    stream.commands[4].c = color;

    stream.commands[5].op = XZ_CMD_DRAW_PACKETS;
    stream.commands[6].op = XZ_CMD_END_PASS;
    stream.commands[6].a = 4u;
    stream.commands[7].op = XZ_CMD_END_FRAME;

    if (!XzPassInputPlan_Build(
            &plan, &stream, &pool))
        return 0;

    if (plan.count != 1u ||
        plan.total_inputs != 2u ||
        plan.max_inputs_per_pass != 2u)
        return 0;

    if (plan.passes[0].count != 2u ||
        plan.passes[0].types[0] !=
            XZ_GPU_RESOURCE_TEXTURE ||
        plan.passes[0].types[1] !=
            XZ_GPU_RESOURCE_DEPTH)
        return 0;

    return 1;
}
