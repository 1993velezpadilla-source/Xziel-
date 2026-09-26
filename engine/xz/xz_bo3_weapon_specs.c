#include "xz_bo3_weapon_specs.h"

#include <math.h>
#include <string.h>

static const XzBo3WeaponSpec kWeaponSpecs[XZ_BO3_WEAPON_SPEC_COUNT] = {
    {
        "bo3_kn44_v1", "ar_standard", "KN-44",
        1400u, 700u,
        XZ_BO3_FIRE_AUTOMATIC, 1u, 625.0f, 625.0f,
        XZ_BO3_DAMAGE_HITSCAN_RANGE, 120.0f, 70.0f, 1u, 4.0f,
        30u, 210u,
        2.03f, 2.80f
    },
    {
        "bo3_argus_v1", "shotgun_precision", "Argus",
        1100u, 550u,
        XZ_BO3_FIRE_LEVER_ACTION, 1u, 63.0f, 63.0f,
        XZ_BO3_DAMAGE_SINGLE_SLUG_RANGE, 800.0f, 500.0f, 1u, 0.0f,
        10u, 60u,
        0.0f, 0.0f
    },
    {
        "bo3_krm262_v1", "shotgun_pump", "KRM-262",
        750u, 375u,
        XZ_BO3_FIRE_PUMP_ACTION, 1u, 60.0f, 60.0f,
        XZ_BO3_DAMAGE_PELLET_RANGE, 225.0f, 15.0f, 4u, 0.0f,
        8u, 48u,
        0.0f, 0.0f
    },
    {
        "bo3_kuda_v1", "smg_standard", "Kuda",
        1250u, 625u,
        XZ_BO3_FIRE_AUTOMATIC, 1u, 722.0f, 722.0f,
        XZ_BO3_DAMAGE_HITSCAN_RANGE, 110.0f, 60.0f, 1u, 4.0f,
        30u, 210u,
        1.80f, 2.30f
    },
    {
        "bo3_locus_v1", "sniper_fastbolt", "Locus",
        5000u, 2500u,
        XZ_BO3_FIRE_BOLT_ACTION, 1u, 57.0f, 57.0f,
        XZ_BO3_DAMAGE_HITSCAN_FLAT, 500.0f, 500.0f, 1u, 0.0f,
        10u, 60u,
        0.0f, 0.0f
    },
    {
        "bo3_pharo_v1", "smg_burst", "Pharo",
        700u, 350u,
        XZ_BO3_FIRE_AUTO_BURST, 4u, 909.0f, 659.0f,
        XZ_BO3_DAMAGE_HITSCAN_RANGE, 80.0f, 60.0f, 1u, 0.0f,
        40u, 160u,
        2.10f, 2.40f
    },
    {
        "bo3_sheiva_v1", "ar_marksman", "Sheiva",
        500u, 250u,
        XZ_BO3_FIRE_SEMIAUTOMATIC, 1u, 257.0f, 257.0f,
        XZ_BO3_DAMAGE_HITSCAN_RANGE, 100.0f, 80.0f, 1u, 3.0f,
        10u, 100u,
        0.0f, 0.0f
    },
    {
        "bo3_rk5_v1", "pistol_burst", "RK5",
        500u, 250u,
        XZ_BO3_FIRE_BURST, 3u, 909.0f, 775.0f,
        XZ_BO3_DAMAGE_HITSCAN_RANGE, 100.0f, 25.0f, 1u, 0.0f,
        15u, 120u,
        1.50f, 1.85f
    }
};

size_t XzBo3WeaponSpec_Count(void)
{
    return XZ_BO3_WEAPON_SPEC_COUNT;
}

const XzBo3WeaponSpec *XzBo3WeaponSpec_Get(
    size_t index)
{
    if (index >= XZ_BO3_WEAPON_SPEC_COUNT)
        return NULL;

    return &kWeaponSpecs[index];
}

const XzBo3WeaponSpec *XzBo3WeaponSpec_FindByLogicalItemId(
    const char *logical_item_id)
{
    size_t index;

    if (!logical_item_id || !logical_item_id[0])
        return NULL;

    for (index = 0u; index < XZ_BO3_WEAPON_SPEC_COUNT; ++index) {
        if (strcmp(
                kWeaponSpecs[index].logical_item_id,
                logical_item_id) == 0)
            return &kWeaponSpecs[index];
    }

    return NULL;
}

float XzBo3WeaponSpec_SecondsPerShot(
    const XzBo3WeaponSpec *spec)
{
    if (!spec ||
        !isfinite(spec->overall_rpm) ||
        spec->overall_rpm <= 0.0f)
        return 0.0f;

    return 60.0f / spec->overall_rpm;
}

float XzBo3WeaponSpec_SecondsPerBurstShot(
    const XzBo3WeaponSpec *spec)
{
    if (!spec ||
        !isfinite(spec->cyclic_rpm) ||
        spec->cyclic_rpm <= 0.0f)
        return 0.0f;

    return 60.0f / spec->cyclic_rpm;
}

float XzBo3WeaponSpec_BurstCycleSeconds(
    const XzBo3WeaponSpec *spec)
{
    if (!spec ||
        spec->burst_size <= 1u ||
        !isfinite(spec->overall_rpm) ||
        spec->overall_rpm <= 0.0f)
        return 0.0f;

    /*
     * overall_rpm is rounds/minute including the pause between bursts.
     * A complete burst cycle therefore occupies N round-periods.
     */
    return ((float)spec->burst_size * 60.0f) /
        spec->overall_rpm;
}

float XzBo3WeaponSpec_BurstTailSeconds(
    const XzBo3WeaponSpec *spec)
{
    float cycle;
    float internal;
    float tail;

    if (!spec || spec->burst_size <= 1u)
        return 0.0f;

    cycle = XzBo3WeaponSpec_BurstCycleSeconds(spec);
    internal =
        ((float)(spec->burst_size - 1u)) *
        XzBo3WeaponSpec_SecondsPerBurstShot(spec);

    if (cycle <= 0.0f || internal < 0.0f)
        return 0.0f;

    tail = cycle - internal;
    return tail > 0.0f ? tail : 0.0f;
}

int XzBo3WeaponSpec_SelfTest(void)
{
    const XzBo3WeaponSpec *rk5;
    const XzBo3WeaponSpec *pharo;
    const XzBo3WeaponSpec *argus;
    const XzBo3WeaponSpec *krm;
    const XzBo3WeaponSpec *locus;
    size_t index;

    if (XzBo3WeaponSpec_Count() != 8u)
        return 0;

    for (index = 0u; index < XzBo3WeaponSpec_Count(); ++index) {
        const XzBo3WeaponSpec *spec =
            XzBo3WeaponSpec_Get(index);

        if (!spec ||
            !spec->spec_id ||
            !spec->logical_item_id ||
            !spec->display_name ||
            spec->wall_cost == 0u ||
            spec->wall_refill_cost == 0u ||
            spec->magazine == 0u ||
            spec->cyclic_rpm <= 0.0f ||
            spec->overall_rpm <= 0.0f ||
            spec->damage_max <= 0.0f ||
            spec->damage_min <= 0.0f ||
            spec->projectiles_per_shot == 0u)
            return 0;
    }

    rk5 = XzBo3WeaponSpec_FindByLogicalItemId(
        "pistol_burst");
    pharo = XzBo3WeaponSpec_FindByLogicalItemId(
        "smg_burst");
    argus = XzBo3WeaponSpec_FindByLogicalItemId(
        "shotgun_precision");
    krm = XzBo3WeaponSpec_FindByLogicalItemId(
        "shotgun_pump");
    locus = XzBo3WeaponSpec_FindByLogicalItemId(
        "sniper_fastbolt");

    if (!rk5 ||
        rk5->fire_mode != XZ_BO3_FIRE_BURST ||
        rk5->burst_size != 3u)
        return 0;

    if (!pharo ||
        pharo->fire_mode != XZ_BO3_FIRE_AUTO_BURST ||
        pharo->burst_size != 4u)
        return 0;

    if (!argus ||
        argus->damage_model !=
            XZ_BO3_DAMAGE_SINGLE_SLUG_RANGE ||
        argus->projectiles_per_shot != 1u)
        return 0;

    if (!krm ||
        krm->damage_model != XZ_BO3_DAMAGE_PELLET_RANGE ||
        krm->projectiles_per_shot != 4u)
        return 0;

    if (!locus ||
        locus->wall_refill_cost != 2500u ||
        locus->damage_max != 500.0f ||
        locus->damage_min != 500.0f)
        return 0;

    if (fabsf(
            XzBo3WeaponSpec_SecondsPerBurstShot(rk5) -
            (60.0f / 909.0f)) > 0.00001f)
        return 0;

    if (fabsf(
            XzBo3WeaponSpec_SecondsPerShot(pharo) -
            (60.0f / 659.0f)) > 0.00001f)
        return 0;

    if (fabsf(
            XzBo3WeaponSpec_BurstTailSeconds(rk5) -
            0.100245f) > 0.0002f)
        return 0;

    if (fabsf(
            XzBo3WeaponSpec_BurstTailSeconds(pharo) -
            0.166169f) > 0.0002f)
        return 0;

    return 1;
}
