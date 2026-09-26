#ifndef XZ_BO3_WEAPON_SPECS_H
#define XZ_BO3_WEAPON_SPECS_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XZ_BO3_WEAPON_SPEC_COUNT 8u

typedef enum XzBo3FireMode {
    XZ_BO3_FIRE_AUTOMATIC = 0,
    XZ_BO3_FIRE_SEMIAUTOMATIC,
    XZ_BO3_FIRE_BURST,
    XZ_BO3_FIRE_AUTO_BURST,
    XZ_BO3_FIRE_PUMP_ACTION,
    XZ_BO3_FIRE_LEVER_ACTION,
    XZ_BO3_FIRE_BOLT_ACTION
} XzBo3FireMode;

typedef enum XzBo3DamageModel {
    XZ_BO3_DAMAGE_HITSCAN_RANGE = 0,
    XZ_BO3_DAMAGE_HITSCAN_FLAT,
    XZ_BO3_DAMAGE_SINGLE_SLUG_RANGE,
    XZ_BO3_DAMAGE_PELLET_RANGE
} XzBo3DamageModel;

typedef struct XzBo3WeaponSpec {
    const char *spec_id;
    const char *logical_item_id;
    const char *display_name;

    unsigned int wall_cost;
    unsigned int wall_refill_cost;

    XzBo3FireMode fire_mode;
    unsigned int burst_size;
    float cyclic_rpm;
    float overall_rpm;

    XzBo3DamageModel damage_model;
    float damage_max;
    float damage_min;
    unsigned int projectiles_per_shot;
    float head_multiplier;

    unsigned int magazine;
    unsigned int reserve;

    float reload_loaded_seconds;
    float reload_empty_seconds;
} XzBo3WeaponSpec;

size_t XzBo3WeaponSpec_Count(void);

const XzBo3WeaponSpec *XzBo3WeaponSpec_Get(
    size_t index);

const XzBo3WeaponSpec *XzBo3WeaponSpec_FindByLogicalItemId(
    const char *logical_item_id);

float XzBo3WeaponSpec_SecondsPerShot(
    const XzBo3WeaponSpec *spec);

float XzBo3WeaponSpec_SecondsPerBurstShot(
    const XzBo3WeaponSpec *spec);

float XzBo3WeaponSpec_BurstCycleSeconds(
    const XzBo3WeaponSpec *spec);

float XzBo3WeaponSpec_BurstTailSeconds(
    const XzBo3WeaponSpec *spec);

int XzBo3WeaponSpec_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
