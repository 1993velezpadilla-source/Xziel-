#include "xz_texture_tap.h"

#include <stdio.h>

int main(void)
{
    if (!XzTextureTap_SelfTest()) {
        fprintf(stderr, "xz_texture_tap_test: FAIL\n");
        return 1;
    }

    puts("xz_texture_tap_test: PASS");
    return 0;
}
