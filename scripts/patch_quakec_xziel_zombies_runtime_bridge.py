#!/usr/bin/env python3
"""Add a stable XZIEL semantic bridge for BO3-style perk/power-up systems.

Higher-level XZIEL systems (Wunderfizz, GobbleGum, scripted rewards) should call
these helpers rather than depend directly on NZ:P's internal numeric IDs.

This bridge reuses upstream primitives where they exist and adds bounded XZIEL
logic primitives where safe. Widow's Wine and Death Machine remain unsupported.
Fire Sale receives a logic-only timer/cost primitive here; its pickup model,
jingle and multi-location presentation remain separately gated.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_zombies_runtime_bridge.py <quakec-root>")

root = Path(sys.argv[1])
power_path = root / "source/server/entities/powerups.qc"
perk_path = root / "source/server/entities/perk_a_cola.qc"

power = power_path.read_text(encoding="utf-8")
perk = perk_path.read_text(encoding="utf-8")

power_marker = "// XZIEL_ZOMBIES_POWERUP_BRIDGE_BEGIN"
if power_marker not in power:
    power += r'''

// XZIEL_ZOMBIES_POWERUP_BRIDGE_BEGIN
// Stable semantic IDs owned by XZIEL, not by upstream NZ:P.
#define XZIEL_PU_NUKE          1
#define XZIEL_PU_INSTAKILL     2
#define XZIEL_PU_DOUBLEPOINTS  3
#define XZIEL_PU_CARPENTER     4
#define XZIEL_PU_MAXAMMO       5
#define XZIEL_PU_RANDOMPERK     6
#define XZIEL_PU_BONUSPOINTS   7
#define XZIEL_PU_FIRESALE      8
#define XZIEL_PU_DEATHMACHINE  9

float(float semantic_id) XZIEL_CorePowerupSupported =
{
    switch (semantic_id) {
        case XZIEL_PU_NUKE:
        case XZIEL_PU_INSTAKILL:
        case XZIEL_PU_DOUBLEPOINTS:
        case XZIEL_PU_CARPENTER:
        case XZIEL_PU_MAXAMMO:
        case XZIEL_PU_RANDOMPERK:
        case XZIEL_PU_BONUSPOINTS:
        case XZIEL_PU_FIRESALE:
            return true;
        default:
            return false;
    }
};

float(float semantic_id) XZIEL_CorePowerupNativeId =
{
    switch (semantic_id) {
        case XZIEL_PU_NUKE: return PU_NUKE;
        case XZIEL_PU_INSTAKILL: return PU_INSTAKILL;
        case XZIEL_PU_DOUBLEPOINTS: return PU_DOUBLEPTS;
        case XZIEL_PU_CARPENTER: return PU_CARPENTER;
        case XZIEL_PU_MAXAMMO: return PU_MAXAMMO;
        case XZIEL_PU_RANDOMPERK: return PU_FREEPERK;
        case XZIEL_PU_BONUSPOINTS: return PU_BONUSPOINTS;
        default: return -1;
    }
};

float(vector where, float semantic_id) XZIEL_SpawnCorePowerup =
{
    float native_id = XZIEL_CorePowerupNativeId(semantic_id);
    if (native_id < 0)
        return false;

    Spawn_Powerup(where, native_id);
    return true;
};

// XZIEL Fire Sale logic primitive. BO3 behavior is a 30 second sale with
// Mystery Box rolls costing 10 points. Presentation/all-spawn behavior is
// intentionally not claimed by this logic-only helper.
float xziel_fire_sale_finished;
float xziel_fire_sale_restore_cost;

void() XZIEL_FireSaleWatcher =
{
    if (time < xziel_fire_sale_finished) {
        mystery_box_cost = 10;
        self.nextthink = time + 0.10;
        return;
    }

    if (xziel_fire_sale_restore_cost > 0)
        mystery_box_cost = xziel_fire_sale_restore_cost;
    else
        mystery_box_cost = 950;

    xziel_fire_sale_finished = 0;
    xziel_fire_sale_restore_cost = 0;
    remove(self);
};

float() XZIEL_StartFireSaleLogic =
{
    if (xziel_fire_sale_finished <= time) {
        xziel_fire_sale_restore_cost = mystery_box_cost;
        if (xziel_fire_sale_restore_cost <= 0)
            xziel_fire_sale_restore_cost = 950;
    }

    xziel_fire_sale_finished = time + 30;
    mystery_box_cost = 10;

    entity watcher = find(world, classname, "xziel_fire_sale_watcher");
    if (watcher == world) {
        watcher = spawn();
        watcher.classname = "xziel_fire_sale_watcher";
        watcher.think = XZIEL_FireSaleWatcher;
        watcher.nextthink = time + 0.10;
    }

    return true;
};

float() XZIEL_FireSaleLogicActive =
{
    return xziel_fire_sale_finished > time;
};

float() XZIEL_PackAPunchGrantPrimitiveSupported =
{
    return true;
};

float(vector where) XZIEL_SpawnPackAPunchGrant =
{
    Spawn_Powerup(where, PU_UPGRADEWEAPON);
    return true;
};
// XZIEL_ZOMBIES_POWERUP_BRIDGE_END
'''

perk_marker = "// XZIEL_ZOMBIES_PERK_BRIDGE_BEGIN"
if perk_marker not in perk:
    perk += r'''

// XZIEL_ZOMBIES_PERK_BRIDGE_BEGIN
#define XZIEL_PERK_MULEKICK    1
#define XZIEL_PERK_JUGGERNOG   2
#define XZIEL_PERK_QUICKREVIVE 3
#define XZIEL_PERK_SPEEDCOLA   4
#define XZIEL_PERK_DOUBLETAP2  5
#define XZIEL_PERK_STAMINUP    6
#define XZIEL_PERK_DEADSHOT    7
#define XZIEL_PERK_WIDOWSWINE  8

float(float semantic_id) XZIEL_PerkSupported =
{
    switch (semantic_id) {
        case XZIEL_PERK_MULEKICK:
        case XZIEL_PERK_JUGGERNOG:
        case XZIEL_PERK_QUICKREVIVE:
        case XZIEL_PERK_SPEEDCOLA:
        case XZIEL_PERK_DOUBLETAP2:
        case XZIEL_PERK_STAMINUP:
        case XZIEL_PERK_DEADSHOT:
            return true;
        default:
            return false;
    }
};

float(float semantic_id) XZIEL_PerkNativeBit =
{
    switch (semantic_id) {
        case XZIEL_PERK_MULEKICK: return P_MULE;
        case XZIEL_PERK_JUGGERNOG: return P_JUG;
        case XZIEL_PERK_QUICKREVIVE: return P_REVIVE;
        case XZIEL_PERK_SPEEDCOLA: return P_SPEED;
        case XZIEL_PERK_DOUBLETAP2: return P_DOUBLE;
        case XZIEL_PERK_STAMINUP: return P_STAMIN;
        case XZIEL_PERK_DEADSHOT: return P_DEAD;
        default: return 0;
    }
};

float(entity player, float semantic_id) XZIEL_PlayerHasPerk =
{
    float perk_bit = XZIEL_PerkNativeBit(semantic_id);
    if (!perk_bit)
        return false;
    return (player.perks & perk_bit) != 0;
};

// Logic-only grant used by scripted reward systems. Presentation-aware systems
// should still route through the drink/machine sequence before calling this.
float(entity player, float semantic_id) XZIEL_GrantPerkLogic =
{
    float perk_bit = XZIEL_PerkNativeBit(semantic_id);
    if (!perk_bit || player == world || player.classname != "player")
        return false;
    if (player.perks & perk_bit)
        return false;

    entity old_self = self;
    self = player;
    GivePerk(perk_bit);
    self = old_self;
    return true;
};
float(entity player) XZIEL_WunderfizzEligiblePerkCount =
{
    if (player == world || player.classname != "player")
        return 0;
    if (Player_GetNumPerks(player) >= game_modifiers.gameplay.perksacola.perk_purchase_limit)
        return 0;

    float count = 0;
    // BO3 Nacht Wunderfizz pool excludes standalone Mule Kick.
    for (float semantic_id = XZIEL_PERK_JUGGERNOG; semantic_id <= XZIEL_PERK_WIDOWSWINE; semantic_id++) {
        if (XZIEL_PerkSupported(semantic_id) && !XZIEL_PlayerHasPerk(player, semantic_id))
            count++;
    }
    return count;
};

float(entity player) XZIEL_WunderfizzPickSupportedPerk =
{
    float eligible = XZIEL_WunderfizzEligiblePerkCount(player);
    if (eligible <= 0)
        return 0;

    float target = floor(random() * eligible);
    if (target >= eligible)
        target = eligible - 1;

    float seen = 0;
    for (float semantic_id = XZIEL_PERK_JUGGERNOG; semantic_id <= XZIEL_PERK_WIDOWSWINE; semantic_id++) {
        if (!XZIEL_PerkSupported(semantic_id) || XZIEL_PlayerHasPerk(player, semantic_id))
            continue;
        if (seen == target)
            return semantic_id;
        seen++;
    }
    return 0;
};

float(entity player) XZIEL_WunderfizzGrantLogic =
{
    float semantic_id = XZIEL_WunderfizzPickSupportedPerk(player);
    if (!semantic_id)
        return false;
    return XZIEL_GrantPerkLogic(player, semantic_id);
};

// XZIEL_ZOMBIES_PERK_BRIDGE_END
'''

for text, begin, end in (
    (power, power_marker, "// XZIEL_ZOMBIES_POWERUP_BRIDGE_END"),
    (perk, perk_marker, "// XZIEL_ZOMBIES_PERK_BRIDGE_END"),
):
    if text.count(begin) != 1 or text.count(end) != 1:
        raise SystemExit(f"runtime bridge marker mismatch: {begin}")

required_power = [
    "XZIEL_CorePowerupSupported",
    "XZIEL_CorePowerupNativeId",
    "XZIEL_SpawnCorePowerup",
    "XZIEL_SpawnPackAPunchGrant",
    "XZIEL_StartFireSaleLogic",
    "XZIEL_FireSaleLogicActive",
]
for token in required_power:
    if power.count(token) < 1:
        raise SystemExit(f"missing power-up bridge token: {token}")

required_perk = [
    "XZIEL_PerkSupported",
    "XZIEL_PerkNativeBit",
    "XZIEL_PlayerHasPerk",
    "XZIEL_GrantPerkLogic",
    "XZIEL_WunderfizzEligiblePerkCount",
    "XZIEL_WunderfizzPickSupportedPerk",
    "XZIEL_WunderfizzGrantLogic",
]
for token in required_perk:
    if perk.count(token) < 1:
        raise SystemExit(f"missing perk bridge token: {token}")

power_path.write_text(power, encoding="utf-8")
perk_path.write_text(perk, encoding="utf-8")
print("Applied XZIEL Zombies semantic runtime bridge (7 perks, 7 upstream power-ups, Fire Sale logic, PaP grant primitive).")
