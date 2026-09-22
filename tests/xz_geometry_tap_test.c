#include "../engine/xz/xz_geometry_tap.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzGeometryTap_SelfTest());
    puts("xz_geometry_tap_test: PASS");
    return 0;
}
