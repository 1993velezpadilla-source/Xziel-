#include "../engine/xz/xz_pass_targets.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzPassTargetPlan_SelfTest());
    puts("xz_pass_targets_test: PASS");
    return 0;
}
