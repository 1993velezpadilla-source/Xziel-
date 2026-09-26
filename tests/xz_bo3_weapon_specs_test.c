#include "xz_bo3_weapon_specs.h"

#include <assert.h>
#include <math.h>
#include <string.h>

int main(void)
{
    const XzBo3WeaponSpec *kn44;
    const XzBo3WeaponSpec *kuda;
    const XzBo3WeaponSpec *sheiva;
    const XzBo3WeaponSpec *rk5;
    const XzBo3WeaponSpec *pharo;
    const XzBo3WeaponSpec *argus;
    const XzBo3WeaponSpec *krm;
    const XzBo3WeaponSpec *locus;

    assert(XzBo3WeaponSpec_SelfTest());
    assert(XzBo3WeaponSpec_Count() == 8u);

    kn44 = XzBo3WeaponSpec_FindByLogicalItemId("ar_standard");
    kuda = XzBo3WeaponSpec_FindByLogicalItemId("smg_standard");
    sheiva = XzBo3WeaponSpec_FindByLogicalItemId("ar_marksman");
    rk5 = XzBo3WeaponSpec_FindByLogicalItemId("pistol_burst");
    pharo = XzBo3WeaponSpec_FindByLogicalItemId("smg_burst");
    argus = XzBo3WeaponSpec_FindByLogicalItemId("shotgun_precision");
    krm = XzBo3WeaponSpec_FindByLogicalItemId("shotgun_pump");
    locus = XzBo3WeaponSpec_FindByLogicalItemId("sniper_fastbolt");

    assert(kn44 && strcmp(kn44->display_name, "KN-44") == 0);
    assert(kn44->damage_max == 120.0f && kn44->damage_min == 70.0f);
    assert(kn44->magazine == 30u && kn44->reserve == 210u);
    assert(kn44->wall_cost == 1400u && kn44->wall_refill_cost == 700u);

    assert(kuda && kuda->overall_rpm == 722.0f);
    assert(kuda->damage_max == 110.0f && kuda->damage_min == 60.0f);

    assert(sheiva && sheiva->overall_rpm == 257.0f);
    assert(sheiva->head_multiplier == 3.0f);

    assert(rk5 && rk5->burst_size == 3u);
    assert(rk5->cyclic_rpm == 909.0f && rk5->overall_rpm == 775.0f);
    assert(rk5->magazine == 15u && rk5->reserve == 120u);

    assert(pharo && pharo->burst_size == 4u);
    assert(pharo->cyclic_rpm == 909.0f && pharo->overall_rpm == 659.0f);

    assert(argus && argus->projectiles_per_shot == 1u);
    assert(argus->damage_max == 800.0f && argus->damage_min == 500.0f);

    assert(krm && krm->projectiles_per_shot == 4u);
    assert(krm->damage_max == 225.0f && krm->damage_min == 15.0f);

    assert(locus && locus->wall_cost == 5000u);
    assert(locus->wall_refill_cost == 2500u);

    assert(XzBo3WeaponSpec_FindByLogicalItemId("frag_grenade") == 0);
    assert(XzBo3WeaponSpec_FindByLogicalItemId("not_a_weapon") == 0);

    assert(fabsf(XzBo3WeaponSpec_SecondsPerShot(kn44) - 0.096f) < 0.0001f);

    return 0;
}
