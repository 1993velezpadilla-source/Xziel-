#include "../engine/xz/xz_rhi.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzRhi_SelfTest());
    puts("xz_rhi_test: PASS");
    return 0;
}
