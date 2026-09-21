#include "../engine/xz/xz_visibility.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzVisibility_SelfTest());
    puts("xz_visibility_test: PASS");
    return 0;
}
