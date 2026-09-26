#include "xz_bo3_weapon_specs.h"

#include <math.h>
#include <string.h>

static const XzBo3WeaponSpec kWeaponSpecs[XZ_BO3_WEAPON_SPEC_COUNT] = {
    {
        .spec_id = "bo3_kn44_v1",
        .logical_item_id = "ar_standard",
        .display_name = "KN-44",
        .wall_cost = 1400u,
        .wall_refill_cost = 700u,
        .fire_mode = XZ_BO3_FIRE_AUTOMATIC,
        .burst_size = 1u,
        .cyclic_rpm = 625.0f,
        .overall_rpm = 625.0f,
        .damage_model = XZ_BO3_DAMAGE_HITSCAN_RANGE,
        .damage_max = 120.0f,
        .damage_min = 70.0f,
        .projectiles_per_shot = 1u,
        .head_multiplier = 4.0f,
        .falloff_start_units = 700.0f,
        .falloff_end_units = 2001.0f,
        .damage_falloff_verified = 1,
        .native_enablement_allowed = 0,
        .magazine = 30u,
        .reserve = 210u,
        .reload_loaded_seconds = 2.03f,
        .reload_empty_seconds = 2.80f
    },
    {
        .spec_id = "bo3_argus_v1",
        .logical_item_id = "shotgun_precision",
        .display_name = "Argus",
        .wall_cost = 1100u,
        .wall_refill_cost = 550u,
        .fire_mode = XZ_BO3_FIRE_LEVER_ACTION,
        .burst_size = 1u,
        .cyclic_rpm = 63.0f,
        .overall_rpm = 63.0f,
        .damage_model = XZ_BO3_DAMAGE_SINGLE_SLUG_RANGE,
        .damage_max = 800.0f,
        .damage_min = 500.0f,
        .projectiles_per_shot = 1u,
        .head_multiplier = 3.0f,
        .falloff_start_units = 300.0f,
        .falloff_end_units = 700.0f,
        .damage_falloff_verified = 0,
        .native_enablement_allowed = 0,
        .magazine = 10u,
        .reserve = 60u,
        .reload_loaded_seconds = 0.0f,
        .reload_empty_seconds = 0.0f
    },
    {
        .spec_id = "bo3_krm262_v1",
        .logical_item_id = "shotgun_pump",
        .display_name = "KRM-262",
        .wall_cost = 750u,
        .wall_refill_cost = 375u,
        .fire_mode = XZ_BO3_FIRE_PUMP_ACTION,
        .burst_size = 1u,
        .cyclic_rpm = 60.0f,
        .overall_rpm = 60.0f,
        .damage_model = XZ_BO3_DAMAGE_PELLET_RANGE,
        .damage_max = 225.0f,
        .damage_min = 15.0f,
        .projectiles_per_shot = 4u,
        .head_multiplier = 2.0f,
        .falloff_start_units = 200.0f,
        .falloff_end_units = 600.0f,
        .damage_falloff_verified = 0,
        .native_enablement_allowed = 0,
        .magazine = 8u,
        .reserve = 48u,
        .reload_loaded_seconds = 0.0f,
        .reload_empty_seconds = 0.0f
    },
    {
        .spec_id = "bo3_kuda_v1",
        .logical_item_id = "smg_standard",
        .display_name = "Kuda",
        .wall_cost = 1250u,
        .wall_refill_cost = 625u,
        .fire_mode = XZ_BO3_FIRE_AUTOMATIC,
        .burst_size = 1u,
        .cyclic_rpm = 722.0f,
        .overall_rpm = 722.0f,
        .damage_model = XZ_BO3_DAMAGE_HITSCAN_RANGE,
        .damage_max = 110.0f,
        .damage_min = 60.0f,
        .projectiles_per_shot = 1u,
        .head_multiplier = 4.0f,
        .falloff_start_units = 400.0f,
        .falloff_end_units = 2001.0f,
        .damage_falloff_verified = 1,
        .native_enablement_allowed = 0,
        .magazine = 30u,
        .reserve = 210u,
        .reload_loaded_seconds = 1.80f,
        .reload_empty_seconds = 2.30f
    },
    {
        .spec_id = "bo3_locus_v1",
        .logical_item_id = "sniper_fastbolt",
        .display_name = "Locus",
        .wall_cost = 5000u,
        .wall_refill_cost = 2500u,
        .fire_mode = XZ_BO3_FIRE_BOLT_ACTION,
        .burst_size = 1u,
        .cyclic_rpm = 57.0f,
        .overall_rpm = 57.0f,
        .damage_model = XZ_BO3_DAMAGE_HITSCAN_FLAT,
        .damage_max = 500.0f,
        .damage_min = 500.0f,
        .projectiles_per_shot = 1u,
        .head_multiplier = 10.0f,
        .falloff_start_units = 4000.0f,
        .falloff_end_units = 5000.0f,
        .damage_falloff_verified = 1,
        .native_enablement_allowed = 0,
        .magazine = 10u,
        .reserve = 60u,
        .reload_loaded_seconds = 0.0f,
        .reload_empty_seconds = 0.0f
    },
    {
        .spec_id = "bo3_pharo_v1",
        .logical_item_id = "smg_burst",
        .display_name = "Pharo",
        .wall_cost = 700u,
        .wall_refill_cost = 350u,
        .fire_mode = XZ_BO3_FIRE_AUTO_BURST,
        .burst_size = 4u,
        .cyclic_rpm = 909.0f,
        .overall_rpm = 659.0f,
        .damage_model = XZ_BO3_DAMAGE_HITSCAN_RANGE,
        .damage_max = 80.0f,
        .damage_min = 60.0f,
        .projectiles_per_shot = 1u,
        .head_multiplier = 4.0f,
        .falloff_start_units = 400.0f,
        .falloff_end_units = 1501.0f,
        .damage_falloff_verified = 1,
        .native_enablement_allowed = 0,
        .magazine = 40u,
        .reserve = 160u,
        .reload_loaded_seconds = 2.10f,
        .reload_empty_seconds = 2.40f
    },
    {
        .spec_id = "bo3_sheiva_v1",
        .logical_item_id = "ar_marksman",
        .display_name = "Sheiva",
        .wall_cost = 500u,
        .wall_refill_cost = 250u,
        .fire_mode = XZ_BO3_FIRE_SEMIAUTOMATIC,
        .burst_size = 1u,
        .cyclic_rpm = 257.0f,
        .overall_rpm = 257.0f,
        .damage_model = XZ_BO3_DAMAGE_HITSCAN_RANGE,
        .damage_max = 100.0f,
        .damage_min = 80.0f,
        .projectiles_per_shot = 1u,
        .head_multiplier = 3.0f,
        .falloff_start_units = 750.0f,
        .falloff_end_units = 2001.0f,
        .damage_falloff_verified = 1,
        .native_enablement_allowed = 0,
        .magazine = 10u,
        .reserve = 100u,
        .reload_loaded_seconds = 0.0f,
        .reload_empty_seconds = 0.0f
    },
    {
        .spec_id = "bo3_rk5_v1",
        .logical_item_id = "pistol_burst",
        .display_name = "RK5",
        .wall_cost = 500u,
        .wall_refill_cost = 250u,
        .fire_mode = XZ_BO3_FIRE_BURST,
        .burst_size = 3u,
        .cyclic_rpm = 909.0f,
        .overall_rpm = 775.0f,
        .damage_model = XZ_BO3_DAMAGE_HITSCAN_RANGE,
        .damage_max = 100.0f,
        .damage_min = 25.0f,
        .projectiles_per_shot = 1u,
        .head_multiplier = 2.0f,
        .falloff_start_units = 200.0f,
        .falloff_end_units = 751.0f,
        .damage_falloff_verified = 1,
        .native_enablement_allowed = 0,
        .magazine = 15u,
        .reserve = 120u,
        .reload_loaded_seconds = 1.50f,
        .reload_empty_seconds = 1.85f
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

float XzBo3WeaponSpec_DamageAtDistanceUnits(
    const XzBo3WeaponSpec *spec,
    float distance_units)
{
    float t;

    if (!spec ||
        !spec->damage_falloff_verified ||
        !isfinite(distance_units) ||
        distance_units < 0.0f)
        return 0.0f;

    if (spec->damage_max == spec->damage_min)
        return spec->damage_max;

    if (!isfinite(spec->falloff_start_units) ||
        !isfinite(spec->falloff_end_units) ||
        spec->falloff_start_units < 0.0f ||
        spec->falloff_end_units <= spec->falloff_start_units)
        return 0.0f;

    if (distance_units <= spec->falloff_start_units)
        return spec->damage_max;
    if (distance_units >= spec->falloff_end_units)
        return spec->damage_min;

    t = (distance_units - spec->falloff_start_units) /
        (spec->falloff_end_units - spec->falloff_start_units);

    return spec->damage_max +
        ((spec->damage_min - spec->damage_max) * t);
}

int XzBo3WeaponSpec_IsNativeReady(
    const XzBo3WeaponSpec *spec)
{
    if (!spec)
        return 0;

    return spec->damage_falloff_verified != 0 &&
        spec->native_enablement_allowed != 0;
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

        if (spec->damage_falloff_verified &&
            (spec->falloff_start_units < 0.0f ||
             spec->falloff_end_units <= spec->falloff_start_units))
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

    if (fabsf(
            XzBo3WeaponSpec_DamageAtDistanceUnits(rk5, 200.0f) -
            100.0f) > 0.0001f)
        return 0;

    if (fabsf(
            XzBo3WeaponSpec_DamageAtDistanceUnits(rk5, 751.0f) -
            25.0f) > 0.0001f)
        return 0;

    if (XzBo3WeaponSpec_DamageAtDistanceUnits(argus, 300.0f) != 0.0f ||
        XzBo3WeaponSpec_DamageAtDistanceUnits(krm, 200.0f) != 0.0f)
        return 0;

    return 1;
}
