#include "../engine/xz/xz_pass_inputs.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzPassInputPlan_SelfTest());
    puts("xz_pass_inputs_test: PASS");
    return 0;
}
