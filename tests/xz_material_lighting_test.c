#include "../engine/xz/xz_material_lighting.h"

#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(XzMaterialLighting_SelfTest());
    puts("xz_material_lighting_test: PASS");
    return 0;
}
