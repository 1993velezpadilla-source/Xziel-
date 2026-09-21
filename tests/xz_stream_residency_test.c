#include "../engine/xz/xz_stream_residency.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzStreamResidency_SelfTest());
    puts("xz_stream_residency_test: PASS");
    return 0;
}
