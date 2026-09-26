#include "xz_map_runtime.h"

#include <assert.h>
#include <string.h>

int main(void)
{
    XzMapRuntimeState state;

    assert(XzMapRuntime_SelfTest());

    XzMapRuntime_Init(&state);
    XzMapRuntime_SetWorldModel(&state, "maps/ndu.bsp");

    assert(XzMapRuntime_Kind(&state) == XZ_MAP_RUNTIME_NONE);
    assert(strcmp(XzMapRuntime_MapId(&state), "ndu") == 0);
    assert(XzMapRuntime_Nacht(&state) == 0);

    XzMapRuntime_SetWorldModel(
        &state,
        "maps/xziel_nacht_bo3.bsp");

    assert(XzMapRuntime_Kind(&state) == XZ_MAP_RUNTIME_NACHT_BO3);
    assert(XzMapRuntime_Nacht(&state) != 0);
    assert(XzMapRuntime_Nacht(&state)->points == 500u);
    assert(XzNacht_ActiveSpawnCount(XzMapRuntime_Nacht(&state)) == 10u);

    return 0;
}
