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
    assert(rk5->head_multiplier == 2.0f);

    assert(pharo && pharo->burst_size == 4u);
    assert(pharo->cyclic_rpm == 909.0f && pharo->overall_rpm == 659.0f);
    assert(pharo->head_multiplier == 4.0f);

    assert(argus && argus->projectiles_per_shot == 1u);
    assert(argus->damage_max == 800.0f && argus->damage_min == 500.0f);
    assert(argus->head_multiplier == 3.0f);

    assert(krm && krm->projectiles_per_shot == 4u);
    assert(krm->damage_max == 225.0f && krm->damage_min == 15.0f);
    assert(krm->head_multiplier == 2.0f);

    assert(locus && locus->wall_cost == 5000u);
    assert(locus->wall_refill_cost == 2500u);
    assert(locus->head_multiplier == 10.0f);

    assert(locus->damage_falloff_verified == 1);
    assert(locus->native_enablement_allowed == 0);
    assert(!XzBo3WeaponSpec_IsNativeReady(locus));

    assert(kn44->damage_falloff_verified == 1);
    assert(kn44->falloff_start_units == 700.0f);
    assert(kn44->falloff_end_units == 2001.0f);
    assert(kuda->falloff_start_units == 400.0f);
    assert(kuda->falloff_end_units == 2001.0f);
    assert(rk5->falloff_start_units == 200.0f);
    assert(rk5->falloff_end_units == 751.0f);
    assert(pharo->falloff_start_units == 400.0f);
    assert(pharo->falloff_end_units == 1501.0f);
    assert(sheiva->falloff_start_units == 750.0f);
    assert(sheiva->falloff_end_units == 2001.0f);
    assert(locus->falloff_start_units == 4000.0f);
    assert(locus->falloff_end_units == 5000.0f);

    assert(argus->damage_falloff_verified == 0);
    assert(krm->damage_falloff_verified == 0);
    assert(XzBo3WeaponSpec_DamageAtDistanceUnits(argus, 300.0f) == 0.0f);
    assert(XzBo3WeaponSpec_DamageAtDistanceUnits(krm, 200.0f) == 0.0f);

    assert(fabsf(XzBo3WeaponSpec_DamageAtDistanceUnits(kn44, 0.0f) - 120.0f) < 0.0001f);
    assert(fabsf(XzBo3WeaponSpec_DamageAtDistanceUnits(kn44, 700.0f) - 120.0f) < 0.0001f);
    assert(fabsf(XzBo3WeaponSpec_DamageAtDistanceUnits(kn44, 1350.5f) - 95.0f) < 0.0001f);
    assert(fabsf(XzBo3WeaponSpec_DamageAtDistanceUnits(kn44, 2001.0f) - 70.0f) < 0.0001f);
    assert(fabsf(XzBo3WeaponSpec_DamageAtDistanceUnits(rk5, 475.5f) - 62.5f) < 0.0001f);
    assert(fabsf(XzBo3WeaponSpec_DamageAtDistanceUnits(locus, 99999.0f) - 500.0f) < 0.0001f);

    for (size_t i = 0u; i < XzBo3WeaponSpec_Count(); ++i) {
        const XzBo3WeaponSpec *spec = XzBo3WeaponSpec_Get(i);
        assert(spec != 0);
        assert(!XzBo3WeaponSpec_IsNativeReady(spec));
    }

    assert(XzBo3WeaponSpec_FindByLogicalItemId("frag_grenade") == 0);
    assert(XzBo3WeaponSpec_FindByLogicalItemId("not_a_weapon") == 0);

    assert(fabsf(XzBo3WeaponSpec_SecondsPerShot(kn44) - 0.096f) < 0.0001f);

    assert(fabsf(
        XzBo3WeaponSpec_BurstCycleSeconds(rk5) -
        (3.0f * 60.0f / 775.0f)) < 0.0001f);
    assert(fabsf(
        XzBo3WeaponSpec_BurstTailSeconds(rk5) -
        0.100245f) < 0.0002f);

    assert(fabsf(
        XzBo3WeaponSpec_BurstCycleSeconds(pharo) -
        (4.0f * 60.0f / 659.0f)) < 0.0001f);
    assert(fabsf(
        XzBo3WeaponSpec_BurstTailSeconds(pharo) -
        0.166169f) < 0.0002f);

    assert(XzBo3WeaponSpec_BurstTailSeconds(kn44) == 0.0f);

    return 0;
}
