#include "../engine/xz/xz_cutover.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzCutover_SelfTest());
    puts("xz_cutover_test: PASS");
    return 0;
}
