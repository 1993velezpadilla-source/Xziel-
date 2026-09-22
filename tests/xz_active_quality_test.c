#include "../engine/xz/xz_active_quality.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzActiveQuality_SelfTest());
    puts("xz_active_quality_test: PASS");
    return 0;
}
