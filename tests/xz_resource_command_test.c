#include "../engine/xz/xz_gpu_resources.h"
#include "../engine/xz/xz_command_stream.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzGpuResourcePool_SelfTest());
    assert(XzCommandStream_SelfTest());

    puts("xz_resource_command_test: PASS");
    return 0;
}
